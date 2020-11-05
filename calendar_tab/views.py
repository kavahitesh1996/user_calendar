from datetime import datetime
import logging

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, JsonResponse
from django.template.context_processors import csrf
# from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from opaque_keys.edx.keys import CourseKey
from courseware.access import has_access
from courseware.courses import get_course_with_access
from django.template import Context, Template

import pytz
from dateutil import parser

from .models import UserCalendar, UserCalendarEvent
from .utils import gcal_service
from . import VENDOR_CSS_URL, VENDOR_JS_URL, VENDOR_PLUGIN_JS_URL, JS_URL

# from edxmako.shortcuts import render_to_response, render_to_string
from django.shortcuts import redirect, render_to_response


from django.views.generic.edit  import CreateView


log = logging.getLogger(__name__)


def from_google_datetime(g_datetime):
    """
    Formats google calendar API datetime string to dhxscheduler
    datetime string.
    Example: "2017-04-25T16:00:00-04:00" >> "04/25/2017 16:00"
    """
    dt = parser.parse(g_datetime)
    local_dt = dt.astimezone(pytz.timezone(settings.TIME_ZONE))
    return local_dt.strftime("%m/%d/%Y %H:%M")


def to_google_datetime(dhx_datetime):
    """
    Formats google dhxscheduler datetime string to calendar API
    datetime string.
    Example: "04/25/2017 16:00" >> "2017-04-25T16:00:00-04:00"
    """
    dt_unaware = datetime.strptime(dhx_datetime, "%m/%d/%Y %H:%M")
    dt_aware = timezone.make_aware(dt_unaware, timezone.get_current_timezone())
    return dt_aware.isoformat()


def get_calendar_id(user):
    """
    Returns google calendar ID by given User.
    """
    user_calendar_data = UserCalendar.objects.filter(
        username=user.username).values('username', 'calendar_id').first()
    calendar_id = user_calendar_data.get(
        'calendar_id') if user_calendar_data else ''
    return calendar_id


def _create_base_calendar_view_context(request):
    """
    Returns the default template context for rendering calendar view.
    """
    user = request.user
    return {
        'csrf': csrf(request)['csrf_token'],
        'user': user,
        'is_staff': is_staff(user),
        'calendar_id': get_calendar_id(user),
    }


def has_permission(user, api_event):
    """
    Has given User the permission to edit given Event?
    """
    try:
        db_event = UserCalendarEvent.objects.get(event_id=api_event['id'])
        return user.username == db_event.edx_user or is_staff(
            user, db_event.user_calendar.username)
    except (ObjectDoesNotExist, KeyError) as e:
        log.warn(e)
        return False


def is_staff(user):
    """
    Is this User Access
    """
    return user.is_staff


def events_view(request):
    """
    Return all google calendar events for given course.
    """
    calendar_id = get_calendar_id(request.user)
    try:
        response = gcal_service.events().list(calendarId=calendar_id,
                                              pageToken=None).execute()
        events = [{
            "id": api_event["id"],
            "text": api_event["summary"],
            "start_date": from_google_datetime(api_event["start"]["dateTime"]),
            "end_date": from_google_datetime(api_event["end"]["dateTime"]),
            "readonly": not has_permission(request.user, api_event)
        } for api_event in response['items']]
    except Exception as e:
        log.exception(e)
        return JsonResponse(data={'errors': e}, status=500, safe=False)
    else:
        return JsonResponse(data=events, status=200, safe=False)


def _get_event_data(post_data, username):
    event = {
        'id': post_data.get('id'),
        'summary': post_data['text'],
        'location': post_data.get('description', ''),
        'description': post_data.get('description', ''),
        'start': {
            'dateTime': to_google_datetime(post_data['start_date']),
        },
        'end': {
            'dateTime': to_google_datetime(post_data['end_date']),
        },
        'username': username,
    }
    return event


def _create_event(request, response):
    """
    Creates new event in google calendar and returns feedback.
    """
    calendar_id = get_calendar_id(request.user)
    event = _get_event_data(request.POST, request.user.username)
    try:
        new_event = gcal_service.events().insert(calendarId=calendar_id,
                                                 body=event).execute()
    except Exception as e:
        log.exception(e)
        status = 500
    else:
        cc_event = UserCalendarEvent(user_calendar_id=calendar_id,
                                       event_id=new_event['id'],
                                       edx_user=request.user)
        cc_event.save()

        status = 201
        response.update({"action": "inserted",
                         "tid": new_event['id']})

    return status, response


def _update_event(request, response):
    """
    Updates given event in google calendar and returns feedback.
    """
    calendar_id = get_calendar_id(request.user)
    event = _get_event_data(request.POST, request.user.username)
    try:
        if has_permission(request.user, event):
            updated_event = gcal_service.events()\
                                        .update(calendarId=calendar_id,
                                                eventId=event['id'],
                                                body=event).execute()
            status = 200
            response.update({"action": "updated",
                             "sid": event["id"],
                             "tid": updated_event["id"]})
        else:
            status = 403
            response["tid"] = event["id"]

    except Exception as e:
        log.exception(e)
        status = 500

    return status, response


def _delete_event(request, response):
    """
    Deletes given event in google calendar and returns feedback.
    """
    calendar_id = get_calendar_id(request.user)
    event = _get_event_data(request.POST, request.user.username)
    try:
        if has_permission(request.user, event):
            gcal_service.events().delete(calendarId=calendar_id,
                                         eventId=event['id']).execute()
            try:
                UserCalendarEvent.objects.get(event_id=event['id']).delete()
            except ObjectDoesNotExist as e:
                log.warn(e)

            status = 200
            response.update({"action": "deleted",
                             "sid": event["id"]})
        else:
            status = 403
            response["tid"] = event["id"]

    except Exception as e:
        log.exception(e)
        status = 500

    return status, response


@csrf_exempt
def dataprocessor_view(request):
    """
    Processes insert/update/delete event requests.
    """
    status = 401
    response = {'action': 'error',
                'sid': request.POST['id'],
                'tid': '0'}

    if request.method == 'POST':
        command = request.POST['!nativeeditor_status']

        if command == 'inserted':
            status, response = _create_event(request, response)
        elif command == 'updated':
            status, response = _update_event(request, response)
        elif command == 'deleted':
            status, response = _delete_event(request, response)

    return JsonResponse(data=response, status=status, safe=False)


class InitCalendarView(View):
    """
    Creates google calendar and associates it with user.
    """
    def post(self, request, *args, **kwargs):

        calendar_data = {
            'summary': request.user.username,
            'timeZone': settings.TIME_ZONE}

        try:
            created_calendar = gcal_service.calendars().insert(
                body=calendar_data).execute()
        except Exception as e:
            log.exception(e)
            return JsonResponse(data={'errors': e}, status=500, safe=False)
        else:
            UserCalendar.objects.create(username=request.user.username,
                                          calendar_id=created_calendar['id'])
            return JsonResponse({"calendarId": created_calendar['id']},
                                status=201)


def get_calendar(request):
    """
    Display Calendar for user.
    """
    context = _create_base_calendar_view_context(request)
    return render_to_response('calendar_tab/calendar_tab_fragment.html',context)

