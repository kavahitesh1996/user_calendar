"""
Models for Calendar Module.
"""
from django.db import models


class UserCalendar(models.Model):
    """
    Mapping: User - Google calendar.
    """
    username = models.CharField(max_length=255)
    calendar_id = models.CharField(max_length=255, primary_key=True)

    class Meta(object):
        app_label = "calendar_tab"
        unique_together = ('username', 'calendar_id')

    def __str__(self):
        return self.calendar_id


class UserCalendarEvent(models.Model):
    """
    Model to control events ownership.
    """
    user_calendar = models.ForeignKey(UserCalendar,
                                        on_delete=models.CASCADE)
    event_id = models.CharField(max_length=255)
    edx_user = models.CharField(max_length=255)

    class Meta(object):
        app_label = "calendar_tab"
        unique_together = ('user_calendar', 'event_id')

    def __str__(self):
        return self.event_id
