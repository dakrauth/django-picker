from datetime import datetime, timedelta
import pytest

from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from picker import forms, exceptions
from picker.models import (
    PickSet,
    PickerFavorite,
    Picker,
    Game,
    Team,
    League,
    Alias,
    PickerGrouping,
    GameSetPicks,
    GamePick,
    PickerMembership,
    active_pickers_for_league,
    valid_team_abbr,
)

from freezegun import freeze_time

from .conftest import _now


results = {
    "sequence": 1,
    "season": _now.year,
    "type": "REG",
    "games": [
        {
            "home": "HUF",
            "away": "GRF",
            "home_score": 150,
            "away_score": 100,
            "status": "Half",
            "winner": "GRF",
        }
    ],
}


@pytest.mark.django_db
class TestGameSet:
    def test_previous_gameset(self, gamesets):
        a = gamesets[0]
        b = gamesets[1]

        assert a.previous_gameset is None
        assert b.previous_gameset.id == a.id

    def test_gameset(self, gameset, now):
        assert gameset.in_progress
        assert gameset.dates[0] == now.date()

    def test_results(self, league, gameset):
        with pytest.raises(exceptions.PickerResultException):
            gameset.update_results(None)

        bad_seq = results.copy()
        bad_seq["sequence"] = 2
        with pytest.raises(exceptions.PickerResultException):
            gameset.update_results(bad_seq)

        assert (0, None) == gameset.update_results(results)

        results["games"][0]["status"] = "Final"
        assert (1, 0) == gameset.update_results(results)

        games = list(gameset.games.all())
        assert gameset.end_time == games[-1].end_time

        game = games[0]
        assert game.winner.abbr == "GRF"
        assert isinstance(str(game), str)
        assert isinstance(game.short_description, str)

        game.winner = None
        assert game.is_tie

        tm = league.teams.create(name="FOO", abbr="foo")
        assert tm.color_options == []
        Alias.objects.create(team=tm, name="Baz")
        assert str(tm.aliases.get()) == "Baz"
        with pytest.raises(ValueError):
            game.winner = tm

    def test_gamesetpicks_update_results(self, gameset):
        # [["GRF", "HUF"], ["RVN", "SLY"]]
        data = {
            "sequence": gameset.sequence,
            "season": gameset.season,
            "games": [
                {
                    "status": "Final",
                    "home": "HUF",
                    "away": "GRF",
                    "home_score": "15",
                    "away_score": "100",
                    "winner": "GRF",
                    "start": "1993-10-15T13:00Z",
                },
                {
                    "status": "Final",
                    "home": "SLY",
                    "away": "RVN",
                    "home_score": "75",
                    "away_score": "100",
                    "winner": "RVN",
                    "start": "1993-10-15T17:00Z",
                },
            ],
        }
        with freeze_time(timedelta(days=5)):
            gameset.update_results(data)
        gs = GameSetPicks.objects.get(id=gameset.id)
        assert gs.points == 175


@pytest.mark.django_db
class TestPickSet:
    def test_pickset(self, gameset, picker):
        ps = PickSet.objects.create(picker=picker, gameset=gameset)
        assert not ps.is_autopicked
        assert not ps.is_complete
        assert ps.progress == 0
        assert ps.points_delta == 0

        assert ps.update_picks() is None

    def test_create_picks(self, gameset, picker):
        PickSet.objects.for_gameset_picker(gameset, picker, PickSet.Strategy.RANDOM)

    def test_no_game_picks(self):
        assert list(GamePick.objects.games_started()) == []
        assert list(GamePick.objects.games_started_display()) == []


@pytest.mark.django_db
class TestGame:
    def test_in_progress(self, gameset):
        g = gameset.games.first()
        assert g.in_progress is True
        with freeze_time("1990-08-01 12:00"):
            assert g.in_progress is False

    def test_display_results(self, gamesets):
        results = Game.objects.display_results()
        for g in results:
            assert g.get("winner") is None

    def test_reset_game(self, gameset):
        gameset.reset_games_status()
        for g in gameset.games.all():
            assert g.status == Game.Status.UNPLAYED


@pytest.mark.django_db
class TestLeague:
    def test_no_gamesets(self, league):
        assert league.current_gameset is None
        assert league.latest_gameset is None
        assert league.latest_season is None
        assert isinstance(league.random_points(), int) is True

    def test_export(self, league, gamesets):
        dct = league.to_dict()
        assert dct.get("schema") == "complete"
        assert "league" in dct
        assert "season" in dct
        assert "gamesets" in dct["season"]
        assert len(dct["season"]["gamesets"]) == 3
        for gs in dct["season"]["gamesets"]:
            assert len(gs["games"]) == 2

    def test_league_current_gameset(self, league, now):
        assert league.current_gameset is None
        assert league.gamesets.count() == 0
        gs = league.gamesets.create(
            season=league.current_season,
            sequence=1,
            opens=now - timedelta(days=1),
            closes=now + timedelta(days=2),
        )
        assert league.gamesets.count() == 1
        assert league.current_gameset.id == gs.id
    
    def test_random_points(self, league):
        # no games yet
        assert league.random_points() == 0



@pytest.mark.django_db
class TestTeam:
    def test_team_season_record(self, teams):
        t = teams[0]
        r = t.season_record(1975)
        assert r == (0, 0, 0)

    def test_valid_team_abbr(self):
        with pytest.raises(ValidationError):
            valid_team_abbr("__team")

    def test_team(self, league, gamesets):
        team = league.teams.first()
        assert len(team.color_options) == 2
        assert team.byes().count() == 0
        assert team.complete_record() == [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        assert team.record == (0, 0, 0)


@pytest.mark.django_db
class TestPickerMisc:
    def test_membership_manager(self, league, picker):
        assert PickerMembership.objects.for_picker(picker, league).count() > 0
        pm = PickerMembership.objects.for_picker(picker)
        assert pm.count() > 0
        pm = list(pm)[0]
        assert pm.should_autopick is True

        picker.is_active = False
        assert PickerMembership.objects.for_picker(picker, league).count() == 0

    def test_picksetmanager(self, gameset, picker):
        picks = PickSet.objects.for_gameset_picker(gameset, picker, "RAND", True)
        assert all([bool(p.winner) for p in picks.gamepicks.all()])

    def test_gamepick(self, gameset, picker):
        ps = PickSet.objects.create(picker=picker, gameset=gameset)
        game = gameset.games.first()
        gp = GamePick.objects.create(game=game, pick=ps)

        assert gp.winner is None
        assert gp.start_time == game.start_time
        assert gp.short_description == game.short_description
        assert gp.winner_abbr == "N/A"
        assert gp.is_correct is None
        assert gp.picked_away is False
        assert gp.picked_home is False

        gp.set_random_winner()
        assert gp.winner is not None

        gp.set_random_winner(force=True)
        assert gp.winner is not None
        gp.set_random_winner()

    def test_picker_active(self, pickers):
        assert 1 == len(PickerGrouping.objects.active())

    def test_active_pickers_for_league(self, league, pickers):
        assert len(active_pickers_for_league(league)) == len(pickers)

    def test_current_gameset_for_gamesetpicks(self, league):
        tz = timezone.get_default_timezone()
        dt = datetime(1990, 9, 1, 12, tzinfo=tz)
        tz_offset = dt.utcoffset()
        teams = league.team_dict

        with freeze_time("1990-08-01 12:00", tz_offset=tz_offset):
            gsp = GameSetPicks.objects.current_gameset(league)
            assert gsp is None

        gamesets = [
            [["GRF", "HUF"], ["RVN", "SLY"]],
            [["GRF", "RVN"], ["SLY", "HUF"]],
            [["SLY", "GRF"], ["HUF", "RVN"]],
        ]

        for i, gs in enumerate(gamesets, 1):
            gsp = GameSetPicks.objects.create(
                league=league,
                season=dt.year,
                sequence=i,
                points=0,
                opens=dt - timedelta(days=1),
                closes=dt + timedelta(days=6),
            )
            for away, home in gs:
                gsp.games.create(
                    home=teams[home], away=teams[away], start_time=dt, location="Hogwards"
                )

            dt = dt + timedelta(days=14)

        with freeze_time("1990-09-01 12:00", tz_offset=-tz_offset):
            gsp = GameSetPicks.objects.current_gameset(league)
            assert gsp.sequence == 1

        with freeze_time("1990-09-10 12:00", tz_offset=-tz_offset):
            gsp = GameSetPicks.objects.current_gameset(league)
            assert gsp.sequence == 2

        with freeze_time("1990-10-10 12:00", tz_offset=-tz_offset):
            gsp = GameSetPicks.objects.current_gameset(league)
            assert gsp.sequence == 3
            assert timezone.now() > gsp.closes


@pytest.mark.django_db
class TestPicker:
    def test_favorite(self, picker, teams):
        lg2 = League.objects.create(name="Foo", abbr="foo")
        with pytest.raises(ValueError):
            PickerFavorite(picker=picker, team=teams[0], league=lg2).save()

    def test_league(self, client, league, gamesets):
        assert league.get_absolute_url() == "/hq/"
        assert league.latest_gameset == gamesets[1]

    def test_picker_manager(self, user):
        with pytest.raises(ValidationError):
            Picker.objects.create()

        p = Picker.objects.create(user=user)
        assert p.name == user.username
        assert p.email == user.email
        assert p.last_login == user.last_login

        items = list(Picker.objects.active())
        assert p in items

    def test_picker_from_user(self, user, picker):
        assert Picker.from_user(user) is None
        assert (
            Picker.from_user(User(username="a", email="a@example.com", password="password")) is None
        )
        assert Picker.from_user(picker.user) == picker

    def test_pickers(self, client, league, grouping, pickers):
        assert len(pickers) == 3
        assert pickers[0].user.is_superuser
        assert not any(p.user.is_superuser for p in pickers[1:])
        assert Picker.objects.count() == 3
        assert Picker.objects.filter(user__is_active=True).count() == 3

        pickers_dct = {p.id: p for p in pickers}
        group = league.pickergrouping_set.get()

        mbr = group.members.first()
        assert str(mbr.picker) in str(mbr)
        assert mbr.is_active is True
        assert mbr.is_management is False
        assert pickers_dct == {mbr.picker.id: mbr.picker for mbr in group.members.all()}

        picker = pickers[0]
        form = forms.PickerForm(picker, {"name": picker.name})
        assert form.is_valid

        fav = PickerFavorite.objects.create(picker=picker, league=league, team=None)
        assert str(fav) == "{}: {} ({})".format(picker, "None", league)
        fav.team = league.team_dict["GRF"]
        fav.save()
        assert str(fav) == "{}: {} ({})".format(picker, "Gryffindor Lions", league)

        form = forms.PickerForm(
            picker,
            {
                "name": picker.name,
                "hq_favorite": league.team_dict["RVN"].id,
            },
        )

        is_valid = form.is_valid()
        if not is_valid:
            print(form.errors)

        assert is_valid
        form.save()
        fav = PickerFavorite.objects.get(picker=picker, league=league)
        assert fav.team.abbr == "RVN"
