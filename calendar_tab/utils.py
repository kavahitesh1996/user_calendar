"""
Google Calendar API utils.
"""
import os
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from oauth2client.service_account import ServiceAccountCredentials
from apiclient.discovery import build

scopes = ['https://www.googleapis.com/auth/calendar']

try:
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'edx-calendar-tab-google-api-private-key.json'), scopes)
except (IOError, KeyError) as e:
    raise ImproperlyConfigured(
        "You must set edx-calendar-tab-google-api-private-key.json ` when "
        "`FEATURES['ENABLE_CALENDAR']` is True."
    )

gcal_service = build('calendar', 'v3',
                     credentials=credentials,
                     cache_discovery=False)
