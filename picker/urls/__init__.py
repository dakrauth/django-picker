from django.urls import include, path
from .. import views
from . import picks, sports

urlpatterns = [
    path("", views.Home.as_view(), name="picker-home"),
    path("teams/", include(sports.teams_urls)),
    path("schedule/", include(sports.schedule_urls)),
    path("roster/", include(picks.roster_urls)),
    path("results/", include(picks.results_urls)),
    path("picks/", include(picks.picks_urls)),
    path("manage/", include(picks.management_urls)),
]
