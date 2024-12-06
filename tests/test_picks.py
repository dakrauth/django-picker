import pytest
from django.urls import reverse
from picker import models as picker
from picker.stats import RosterStats

from .conftest import _now

YEAR = _now.year

PICK_ARGS = [
    # /<league>/picks/<season>/ picker.views.picks.PicksBySeason picker-picks-season
    ("picker-picks-season", ["hq", str(YEAR)]),
    # /<league>/picks/<season>/<var>/ picker.views.picks.PicksByWeek  picker-picks-sequence
    ("picker-picks-sequence", ["hq", str(YEAR), "1"]),
    # /<league>/results/  picker.views.picks.Results  picker-results
    ("picker-results-group", ["hq", "1"]),
    # /<league>/results/<season>/ picker.views.picks.ResultsBySeason  picker-results-season
    ("picker-results-season", ["hq", "1", str(YEAR)]),
    # /<league>/results/<season>/<var>/ picker.views.picks.ResultsByWeek picker-results-sequence
    ("picker-results-sequence", ["hq", "1", str(YEAR), "1"]),
]


@pytest.mark.django_db
class TestViews:
    def test_lookup(self, client, league, gamesets, user):
        # /<league>/picks/    picker.views.picks.Picks    picker-picks
        url = reverse("picker-picks", args=["hq"])
        r = client.get(url)
        assert r.status_code == 302
        assert r.url == reverse("login") + "?next=" + url

        client.force_login(user)
        r = client.get(url, follow=False)
        assert r.status_code == 302
        assert r.url == "/hq/picks/{}/1/".format(YEAR)

    @pytest.mark.parametrize("name,args", PICK_ARGS)
    def test_views_not_logged_in(self, client, league, name, args):
        url = reverse(name, args=args)
        r = client.get(url)
        assert r.status_code == 302
        assert r.url == reverse("login") + "?next=" + url

    @pytest.mark.parametrize("name,args", PICK_ARGS)
    def test_views_logged_in(self, client, league, gamesets, user, name, args):
        client.force_login(user)
        url = reverse(name, args=args)
        r = client.get(url)
        assert r.status_code == 200


@pytest.mark.django_db
class TestPicksForm:
    def test_picks_form(self, client, league, grouping, gamesets, users):
        slug = league.slug
        season = league.current_season
        superuser, user1, user2 = users

        client.force_login(user1)
        url = reverse("picker-picks-sequence", args=[slug, season, 1])
        r = client.post(url, {"points": "X"})
        assert r.status_code == 200
        assert b"Enter a whole number" in r.content
        assert b"errorlist" in r.content
        assert picker.PickSet.objects.count() == 0

        GRF = str(league.teams.get(abbr="GRF").id)  # 1
        HUF = str(league.teams.get(abbr="HUF").id)  # 2
        RVN = str(league.teams.get(abbr="RVN").id)  # 3
        SLY = str(league.teams.get(abbr="SLY").id)  # 4

        #  GM,       WHO, USER1, PTS1, USER2, PTS2, RES,  PTS, SC1, SC2,  WON
        #   1, GRF @ HUF,   GRF,     ,   HUF,     , GRF,     ,   1,   0,
        #   2, RVN @ SLY,   RVN,  100,   SLY,  200, RVN,  300,   1,   0, USER1

        #   3, GRF @ RVN,   GRF,     ,   RVN,     , RVN,     ,   0,   1,
        #   4, HUF @ SLY,   HUF,  200,   SLY,  300, SLY,  300,   0,   1, USER2

        #   5, SLY @ GRF,   SLY,     ,   GRF,     , GRF,     ,   0,   1,
        #   6, HUF @ RVN,   HUF,  300,   RVN,  400, HUF,  300,   1,   0, USER1

        client.force_login(user1)
        url = reverse("picker-picks-sequence", args=[slug, season, 1])
        r = client.post(url, {"game_1": GRF, "points": "100"})
        assert picker.PickSet.objects.count() == 1

        for data, user, seq in [
            [{"game_1": GRF, "game_2": RVN, "points": "0"}, user1, 1],
            [{"game_1": HUF, "game_2": SLY, "points": "0"}, user2, 1],
            [{"game_1": GRF, "game_2": RVN, "points": "100"}, user1, 1],
            [{"game_1": HUF, "game_2": SLY, "points": "200"}, user2, 1],
        ]:
            client.force_login(user)
            r = client.post(reverse("picker-picks-sequence", args=[slug, season, seq]), data)

        assert picker.PickSet.objects.count() == 2
        assert picker.PickSet.objects.filter(is_winner=True).count() == 0

        url = reverse("picker-manage-week", args=[slug, season, 1])
        client.force_login(superuser)
        r = client.post(url, {"game_1": GRF, "game_2": RVN, "points": "0"})
        assert picker.PickSet.objects.filter(is_winner=True).count() == 0

        r = client.post(url, {"game_1": GRF, "game_2": RVN, "points": "300"})
        assert picker.PickSet.objects.filter(is_winner=True).count() == 1

        assert user1.picksets.get(gameset__sequence=1).is_winner is True
        assert user2.picksets.get(gameset__sequence=1).is_winner is False

        for data, user, seq in [
            [{"game_3": GRF, "game_4": HUF, "points": "200"}, user1, 2],
            [{"game_3": RVN, "game_4": SLY, "points": "300"}, user2, 2],
            [{"game_5": SLY, "game_6": HUF, "points": "300"}, user1, 3],
            [{"game_5": GRF, "game_6": RVN, "points": "400"}, user2, 3],
        ]:
            client.force_login(user)
            r = client.post(reverse("picker-picks-sequence", args=[slug, season, seq]), data)

        assert picker.PickSet.objects.count() == 6

        client.force_login(superuser)
        for data, seq in [
            [{"game_1": GRF, "game_2": RVN, "points": "300"}, 1],
            [{"game_3": RVN, "game_4": SLY, "points": "300"}, 2],
            [{"game_5": GRF, "game_6": HUF, "points": "300"}, 3],
        ]:
            url = reverse("picker-manage-week", args=[slug, season, seq])
            r = client.post(url, data)

        assert picker.Team.objects.get(abbr="HUF").record_as_string == "1-2"
        assert picker.Team.objects.get(abbr="RVN").record_as_string == "2-1"
        assert picker.Team.objects.get(abbr="SLY").record_as_string == "1-2"

        grf = picker.Team.objects.get(abbr="GRF")
        assert grf.record_as_string == "2-1"
        assert grf.complete_record() == [[1, 0, 0], [1, 1, 0], [2, 1, 0]]

        assert user1.picksets.filter(is_winner=True).count() == 2
        assert user2.picksets.filter(is_winner=True).count() == 1

        assert user1.picksets.get(gameset__sequence=1).is_winner is True
        assert user2.picksets.get(gameset__sequence=1).is_winner is False

        assert user1.picksets.get(gameset__sequence=2).is_winner is False
        assert user2.picksets.get(gameset__sequence=2).is_winner is True

        assert user1.picksets.get(gameset__sequence=3).is_winner is True
        assert user2.picksets.get(gameset__sequence=3).is_winner is False

        rs = RosterStats.get_details(league, grouping, season=None)
        rs1 = rs[0][0]
        rs2 = rs[1][0]

        # from pprint import pprint
        # pprint(vars(rs1))
        # pprint(vars(rs2))

        assert rs1.user == user2
        assert rs1.picksets_won == 1
        assert rs2.picksets_won == 2

        assert rs1.points_delta == 200
        assert rs2.points_delta == 300
