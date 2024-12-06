import pytest

from picker import models as picker
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

    def test_create_picks(self, league, gameset, user):
        picker.PickSet.objects.for_gameset_user(gameset, user, picker.PickSet.Strategy.RANDOM)


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

    def test_users(self, client, league, grouping, users):
        assert len(users) == 3
        assert users[0].is_superuser
        assert not any(u.is_superuser for u in users[1:])
        assert picker.Preference.objects.count() == 3
        assert picker.Preference.objects.filter(user__is_active=True).count() == 3
        assert picker.Preference.objects.last().should_autopick is True

        users_dct = {u.id: u for u in users}
        group = league.pickergrouping_set.get()

        mbr = group.members.first()
        assert str(mbr.user) in str(mbr)
        assert mbr.is_active is True
        assert mbr.is_management is False
        assert users_dct == {mbr.user.id: mbr.user for mbr in group.members.all()}

        user = users[0]
        fav = picker.PickerFavorite.objects.create(user=user, league=league, team=None)
        assert str(fav) == "{}: {} ({})".format(user, "None", league)
        fav.team = league.team_dict["GRF"]
        fav.save()
        assert str(fav) == "{}: {} ({})".format(user, "Gryffindor Lions", league)

        pref = picker.Preference.objects.get(user=user)
        form = forms.PreferenceForm(
            pref,
            {
                "hq_favorite": league.team_dict["RVN"].id,
                "autopick": picker.Preference.Autopick.NONE,
            },
        )

        is_valid = form.is_valid()
        if not is_valid:
            print(form.errors)

        assert is_valid
        form.save()
        fav = picker.PickerFavorite.objects.get(user=user, league=league)
        assert fav.team.abbr == "RVN"
