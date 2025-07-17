from django.urls import path
from ..views import sports as views


teams_urls = [
    path("", views.Teams.as_view(), name="picker-teams"),
    path("<str:team>/", views.Team.as_view(), name="picker-team"),
]

schedule_urls = [
    path("", views.Schedule.as_view(), name="picker-schedule"),
    path("<int:season>/", views.Schedule.as_view(), name="picker-schedule-year"),
]
