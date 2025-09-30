import pytest

from picker.models import PickSet, PickerFavorite, Picker
from picker import forms, exceptions

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
        assert isinstance(str(game), str)
        assert isinstance(game.short_description, str)

    def test_create_picks(self, league, gameset, picker):
        PickSet.objects.for_gameset_picker(gameset, picker, PickSet.Strategy.RANDOM)


@pytest.mark.django_db
class TestLeague:
    def test_no_gamesets(self, league):
        assert league.current_gameset is None
        assert league.latest_gameset is None
        assert league.latest_season is None
        assert isinstance(league.random_points(), int) is True


@pytest.mark.django_db
class TestTeam:
    def test_team(self, league, gamesets):
        team = league.teams.first()
        assert len(team.color_options) == 2
        assert team.byes().count() == 0
        assert team.complete_record() == [[0, 0, 0], [0, 0, 0], [0, 0, 0]]


@pytest.mark.django_db
class TestUserConf:
    def test_league(self, client, league, gamesets):
        assert league.get_absolute_url() == "/hq/"
        assert league.latest_gameset == gamesets[1]

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
