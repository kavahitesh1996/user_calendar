# User calendar

Shared calendar for Users

Users can add/edit/delete his/her event on google calendar in openedx.

## Reference
    https://github.com/raccoongang/edx-calendar-tab.git

## Installation

    sudo -sHu edxapp
    cd
    . edxapp_env
    pip install -e git+https://github.com/kavahitesh1996/user_calendar.git@master#egg=user_calendar

Django's collectstatic should be performed (change to --settings=devstack for
devstack installation):

    python edx-platform/manage.py lms collectstatic --settings=aws --noinput

## Configuration

### Configure google service account

Google service accounts [documentation](https://developers.google.com/identity/protocols/OAuth2ServiceAccount).

In general process consists of these steps:

* create new Project in [developers console](https://console.developers.google.com/projectselector/iam-admin/serviceaccounts);

* create new Service Account via Project (with "Owner" role);

* [enable] Google Calendar API via Project;

[enable]: https://console.developers.google.com/apis/dashboard

* [create] credentials for Service Account (service account key)

* save json-api-private-key - _you'll need to put it on your server
  (into "/edx-platform/user_calendar/calendar_tab", for example_);

[create]: https://console.developers.google.com/apis/credentials

### Configure edx-platform

Add "edx-calendar-tab" to installed Django apps

In "/edx/app/edxapp/lms.env.json" add:

    "ADDL_INSTALLED_APPS": ["calendar_tab"],

and to the list of FEATURES add:

    "ENABLE_CALENDAR": true,

In "/edx/app/edxapp/edx-platform/lms/urls.py" add __before__
static_tab urls:

    if settings.FEATURES.get('ENABLE_CALENDAR'):
        urlpatterns += (
           url(
               r'^calendar/',
               include('calendar_tab.urls'),
               name='calendar_tab_endpoints',
           ),
        )

## Basic usage

From the very beginning after calendar is enabled, there is no
any google calendar associated with current user, so user has to
initialize one at first time by submitting "Initiate google
calendar" button.

Application then creates new Google Calendar (from behalf of Google
service account) and associates it with the current user.
This Calendar is private and can't be seen out of service account.

After initialization new google calendar is rendered on it.

Students can create/update/delete events.

Events may be edited via dialog box(on double click), by dragging
(whole event or its start/end border).


## Installed

After installation you should get the following state.

* LMS's main menu has Calendar tab:

![Calendar page](doc/img/lms_calander.png)
