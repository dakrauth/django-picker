import pytest

from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured

from picker.models import PickSet, Team, Picker
from picker.views.base import SimplePickerViewBase

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
    def test_simple_view_class(self, user, client):
        client.force_login(user)
        r = client.get("/hq/")
        req = r.wsgi_request
        req.user = user
        view = SimplePickerViewBase()
        view.setup(req)
        with pytest.raises(ImproperlyConfigured):
            view.get_template_names()

        assert view.picker is None
        assert list(view.leagues) == []


    def test_results_unavailable(self, client, league, picker, grouping):
        client.force_login(picker.user)
        r = client.get(
            reverse(
                "picker-results-group", args=[league.abbr.lower(), str(grouping.id)]
            )
        )
        assert b"Results currently unavailable" in r.content

    def test_picks_unavailable(self, client, picker, league):
        client.force_login(picker.user)
        r = client.get(reverse("picker-picks", args=[league.abbr.lower()]))
        assert r.status_code == 200
        assert b"Picks currently unavailable" in r.content

    def test_lookup(self, client, league, gamesets, picker):
        # /<league>/picks/    picker.views.picks.Picks    picker-picks
        url = reverse("picker-picks", args=["hq"])
        r = client.get(url)
        assert r.status_code == 302
        assert r.url == reverse("login") + "?next=" + url

        client.force_login(picker.user)
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
    def test_views_logged_in(self, client, league, gamesets, picker, name, args):
        client.force_login(picker.user)
        url = reverse(name, args=args)
        r = client.get(url)
        assert r.status_code == 200
    
    def test_picks_by_gameset_not_open(self, client, league, gameset, picker):
        client.force_login(picker.user)
        url = reverse(
            "picker-picks-sequence", args=[
                league.abbr.lower(), str(gameset.season), str(gameset.sequence)
            ]
        )
        r = client.get(url)
        assert r.status_code == 200
        assert all(["show.html" in t for t in r.template_name])

        r = client.post(url, {})
        assert r.status_code == 200
        assert all(["show.html" in t for t in r.template_name])


class PostPick:
    def __init__(self, client, league):
        self.client = client
        self.slug = league.slug
        self.season = league.current_season

    def __call__(self, picker, sequence, expect=302, **data):
        url = "picker-manage-week" if picker.user.is_superuser else "picker-picks-sequence"
        self.client.force_login(picker.user)
        r = self.client.post(reverse(url, args=[self.slug, self.season, sequence]), data)
        assert r.status_code == expect
        return r


if 0:
    def show_stats(grp_stats, msg):
        from pprint import pprint
        print(f"##### {msg} #####")
        pprint(vars(grp_stats[0][0]))
        pprint(vars(grp_stats[1][0]))
else:
    def show_stats(*args):
        pass

@pytest.mark.django_db
class TestPicksForm:
    def test_picks_form(self, client, league, grouping, gamesets, pickers, teams):
        superuser, picker1, picker2 = pickers
        post_pick = PostPick(client, league)

        r = post_pick(picker1, 1, expect=200, points="X")
        assert r.status_code == 200
        assert b"Enter a whole number" in r.content
        assert b"errorlist" in r.content
        assert PickSet.objects.count() == 0

        GRF, HUF, RVN, SLY = [str(t.id) for t in teams]

        #  GM,    WHO,    USER1, PTS1, USER2, PTS2, RES,  PTS, SC1, SC2,  WON
        #   1, GRF @ HUF,   GRF,     ,   HUF,     , GRF,     ,   1,   0,
        #   2, RVN @ SLY,   RVN,  100,   SLY,  200, RVN,  300,   1,   0, USER1

        #   3, GRF @ RVN,   GRF,     ,   RVN,     , RVN,     ,   0,   1,
        #   4, HUF @ SLY,   HUF,  200,   SLY,  300, SLY,  300,   0,   1, USER2

        #   5, SLY @ GRF,   SLY,     ,   GRF,     , GRF,     ,   0,   1,
        #   6, HUF @ RVN,   HUF,  300,   RVN,  400, HUF,  300,   1,   0, USER1

        post_pick(picker1, 1, game_1=GRF, points="100")
        assert PickSet.objects.count() == 1

        for data, picker, seq in [
            [{"game_1": GRF, "game_2": RVN, "points": "0"}, picker1, 1],
            [{"game_1": HUF, "game_2": SLY, "points": "0"}, picker2, 1],
            [{"game_1": GRF, "game_2": RVN, "points": "100"}, picker1, 1],
            [{"game_1": HUF, "game_2": SLY, "points": "200"}, picker2, 1],
        ]:
            post_pick(picker, seq, **data)

        assert PickSet.objects.count() == 2
        assert PickSet.objects.filter(is_winner=True).count() == 0

        post_pick(superuser, 1, game_1=GRF, game_2=RVN, points="0")
        assert PickSet.objects.filter(is_winner=True).count() == 0

        show_stats(Picker.stats.group_stats(grouping, league, season=None), "Week 1 NO POINTS")

        post_pick(superuser, 1, game_1=GRF, game_2=RVN, points="300")
        assert PickSet.objects.filter(is_winner=True).count() == 1

        show_stats(Picker.stats.group_stats(grouping, league, season=None), "Week 1 300 POINTS")

        assert picker1.picksets.get(gameset__sequence=1).is_winner is True
        assert picker2.picksets.get(gameset__sequence=1).is_winner is False

        for data, picker, seq in [
            [{"game_3": GRF, "game_4": HUF, "points": "200"}, picker1, 2],
            [{"game_3": RVN, "game_4": SLY, "points": "300"}, picker2, 2],
            [{"game_5": SLY, "game_6": HUF, "points": "300"}, picker1, 3],
            [{"game_5": GRF, "game_6": RVN, "points": "400"}, picker2, 3],
        ]:
            post_pick(picker, seq, **data)

        assert PickSet.objects.count() == 6

        client.force_login(superuser.user)
        for data, seq in [
            [{"game_1": GRF, "game_2": RVN, "points": "300"}, 1],
            [{"game_3": RVN, "game_4": SLY, "points": "300"}, 2],
            [{"game_5": GRF, "game_6": HUF, "points": "300"}, 3],
        ]:
            post_pick(superuser, seq, **data)

        assert Team.objects.get(abbr="HUF").record_as_string == "1-2"
        assert Team.objects.get(abbr="RVN").record_as_string == "2-1"
        assert Team.objects.get(abbr="SLY").record_as_string == "1-2"

        grf = Team.objects.get(abbr="GRF")
        assert grf.record_as_string == "2-1"
        assert grf.complete_record() == [[1, 0, 0], [1, 1, 0], [2, 1, 0]]

        assert picker1.picksets.filter(is_winner=True).count() == 2
        assert picker2.picksets.filter(is_winner=True).count() == 1

        assert picker1.picksets.get(gameset__sequence=1).is_winner is True
        assert picker2.picksets.get(gameset__sequence=1).is_winner is False

        assert picker1.picksets.get(gameset__sequence=2).is_winner is False
        assert picker2.picksets.get(gameset__sequence=2).is_winner is True

        assert picker1.picksets.get(gameset__sequence=3).is_winner is True
        assert picker2.picksets.get(gameset__sequence=3).is_winner is False

        rs = Picker.stats.group_stats(grouping, league, season=None)
        rs1 = rs[0][0]
        rs2 = rs[1][0]

        show_stats(rs, "Week 3 ALL POINTS")

        assert rs1.picker == picker2
        assert rs1.picksets_won == 1
        assert rs2.picksets_won == 2

        assert rs1.points_delta == 200
        assert rs2.points_delta == 300

        rs = Picker.stats.for_picker(picker2, league)
        *seasons, all_time = rs
        assert len(seasons) == 1
        assert seasons[0].points_delta == 200