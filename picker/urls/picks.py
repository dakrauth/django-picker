from django.urls import include, path
from django.urls import converters

from .. import views


class SignedIntConverter(converters.IntConverter):
    regex = "-?[0-9]+"


converters.register_converter(SignedIntConverter, "uint")

management_urls = [
    path("", views.ManagementHome.as_view(), name="picker-manage"),
    path("game/<int:game_id>/", views.ManageGame.as_view(), name="picker-manage-game"),
    path(
        "<int:season>/",
        include(
            [
                path("", views.ManageSeason.as_view(), name="picker-manage-season"),
                path("<uint:sequence>/", views.ManageWeek.as_view(), name="picker-manage-week"),
            ]
        ),
    ),
]

picks_urls = [
    path("", views.Picks.as_view(), name="picker-picks"),
    path(
        "<int:season>/",
        include(
            [
                path("", views.PicksBySeason.as_view(), name="picker-picks-season"),
                path(
                    "<uint:sequence>/",
                    views.PicksByGameset.as_view(),
                    name="picker-picks-sequence",
                ),
            ]
        ),
    ),
]

results_urls = [
    path(
        "",
        views.GroupMembershipRedirect.as_view(redirect_view_name="picker-results-group"),
        name="picker-results",
    ),
    path(
        "<int:group_id>/",
        include(
            [
                path("", views.Results.as_view(), name="picker-results-group"),
                path(
                    "<int:season>/",
                    include(
                        [
                            path("", views.ResultsBySeason.as_view(), name="picker-results-season"),
                            path(
                                "<uint:sequence>/",
                                views.ResultsByWeek.as_view(),
                                name="picker-results-sequence",
                            ),
                        ]
                    ),
                ),
            ]
        ),
    ),
]

roster_urls = [
    path(
        "",
        views.GroupMembershipRedirect.as_view(redirect_view_name="picker-roster-group"),
        name="picker-roster",
    ),
    path(
        "<int:group_id>/",
        include(
            [
                path("", views.Roster.as_view(), name="picker-roster-group"),
                path("<int:season>/", views.Roster.as_view(), name="picker-roster-season"),
                path(
                    "p/<slug:username>/",
                    views.RosterProfile.as_view(),
                    name="picker-roster-profile",
                ),
            ]
        ),
    ),
]
