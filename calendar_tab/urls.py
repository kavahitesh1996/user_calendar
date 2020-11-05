from django.conf.urls import  url
from django.contrib.auth.decorators import login_required

from .views import InitCalendarView, events_view, dataprocessor_view
from calendar_tab import views

urlpatterns = [
    url(r"^view/dataprocessor/$", views.dataprocessor_view, name="dataprocessor"),
    url(r"^init/$",
        login_required(InitCalendarView.as_view()),
        name="calendar_init"),
    url(r"^view/$", views.get_calendar, name="calendar_view"),
    url(r"^view/events/$", views.events_view, name="events_view"),
]
