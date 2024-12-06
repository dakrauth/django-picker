import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestViews:
    def test_roster(self, client, league, gamesets, user, user_ng):
        client.force_login(user)

        # /<league>/roster/ picker.views.picks.RosterRedirect   picker-roster
        url = reverse("picker-roster", args=["hq"])
        r = client.get(url)
        assert r.status_code == 302

        client.force_login(user_ng)
        r = client.get(url)
        assert r.status_code == 200
        assert b"<h1>Membership group unavailable</h1>" in r.content

    def test_views(self, client, league, gamesets, user):
        for code in [302, 200]:
            if code == 200:
                client.force_login(user)

            # /<league>/roster/<var>/ picker.views.picks.Roster   picker-roster
            r = client.get(reverse("picker-roster-group", args=["hq", "1"]))
            assert r.status_code == code

            # /<league>/roster/<var>/<season>/    picker.views.picks.Roster   picker-season-roster
            r = client.get(reverse("picker-roster-season", args=["hq", "1", league.current_season]))
            assert r.status_code == code

            # /<league>/roster/<var>/p/<var>/ picker.views.picks.RosterProfile picker-roster-profile
            url = reverse("picker-roster-profile", args=["hq", "1", user.username])
            print("url =", url)
            r = client.get(url)
            assert r.status_code == code
