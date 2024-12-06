import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestViews:
    def test_require_manager(self, client, league, gamesets, user):
        # /<league>/manage/   picker.views.manage.ManagementHome  picker-manage
        r = client.get(reverse("picker-manage", args=["hq"]))
        assert r.status_code == 302

        # /<league>/manage/<season>/  picker.views.manage.ManageSeason    picker-manage-season
        r = client.get(reverse("picker-manage-season", args=["hq", league.current_season]))
        assert r.status_code == 302

        # /<league>/manage/<season>/<var>/    picker.views.manage.ManageWeek  picker-manage-week
        r = client.get(reverse("picker-manage-week", args=["hq", league.current_season, "1"]))
        assert r.status_code == 302

        # /<league>/manage/game/<var>/    picker.views.manage.ManageGame  picker-manage-game
        r = client.get(reverse("picker-manage-game", args=["hq", "1"]))
        assert r.status_code == 302

    def test_manager(self, client, league, gameset, superuser):
        # /<league>/manage/   picker.views.manage.ManagementHome  picker-manage
        r = client.get(reverse("picker-manage", args=["hq"]))
        assert r.status_code == 200

        # /<league>/manage/<season>/  picker.views.manage.ManageSeason    picker-manage-season
        r = client.get(reverse("picker-manage-season", args=["hq", league.current_season]))
        assert r.status_code == 200

        # /<league>/manage/<season>/<var>/    picker.views.manage.ManageWeek  picker-manage-week
        r = client.get(reverse("picker-manage-week", args=["hq", league.current_season, "1"]))
        assert r.status_code == 200

        # /<league>/manage/game/<var>/    picker.views.manage.ManageGame  picker-manage-game
        r = client.get(reverse("picker-manage-game", args=["hq", "1"]))
        assert r.status_code == 200
