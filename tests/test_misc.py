import datetime
import pytest

from django import forms as django_forms
from picker import VERSION, get_version
from picker import utils, conf, forms
from picker.models import PickSet, League
from picker.templatetags import picker_tags

model_urls = [
    "conference",
    "division",
    "gameset",
    "league",
    "pickset",
    "picker",
    "team",
]


@pytest.mark.django_db
class TestMisc:
    def test_version(self):
        ver = get_version()
        assert isinstance(ver, str)
        assert tuple(int(i) for i in ver.split(".")) == VERSION

    def test_picker_result_templagtetag(self, picker):
        pick = ["foo", "yes"]
        result = picker_tags.picker_result(pick, {})
        assert result == "error"

        result = picker_tags.picker_result(pick, {"foo": {"winner": "yes"}})
        assert result == "correct"

        result = picker_tags.picker_result(pick, {"foo": {"winner": "no"}})
        assert result == "incorrect"

    def test_favorite_team_templatetag(self, league, picker):
        assert picker_tags.favorite_team({"league": league}, picker) is None
        assert picker_tags.favorite_team({}, picker, league) is None
        team = league.teams.first()
        picker.picker_favorites.create(league=league, team=team)
        assert picker_tags.favorite_team({}, picker, league) == team
    
    def test_picker_widget(self):
        league = League.objects.create(id=999, name="XFL", abbr="XFL")
        assert forms.get_picker_widget(league) == django_forms.RadioSelect


@pytest.mark.django_db
class TestAdmin:
    @pytest.mark.parametrize("bit", model_urls)
    def test_landing(self, client, superuser, gameset, bit):
        if bit == "pickset":
            PickSet.objects.create(picker=superuser, gameset=gameset)

        r = client.get(f"/admin/picker/{bit}/")
        assert r.status_code == 200

        r = client.get(f"/admin/picker/{bit}/add/")
        assert r.status_code == 200

    def test_gameset_form(self, client, superuser, gameset):
        r = client.get(f"/admin/picker/gameset/{gameset.pk}/change/")
        assert r.status_code == 200

    def test_pickset_inlines(self, client, superuser, gameset):
        ps = PickSet.objects.create(picker=superuser, gameset=gameset)
        ps.gamepicks.create(game=gameset.games.first())
        r = client.get(f"/admin/picker/pickset/{ps.pk}/change/")
        assert r.status_code == 200


def can_participate(user, gs):
    return gs


class TestUtils:
    def test_participate(self):
        conf.picker_settings["PARTICIPATION_HOOKS"] = ["tests.test_misc.can_participate"]
        assert utils.can_picker_participate(None, True) is True
        assert utils.can_picker_participate(None, False) is False

    def test_get_templates(self):
        assert utils.get_templates("foo.html") == "foo.html"
        assert utils.get_templates("@foo.html") == [
            "picker/foo.html",
            "picker/_base/foo.html",
        ]

    def test_parse_datetime(self):
        assert utils.parse_datetime("Oct 9, 2025 00:00:00+0:00") == datetime.datetime(
            2025, 10, 9, tzinfo=datetime.timezone.utc
        )
        assert utils.parse_datetime("Oct 9, 2025 00:00:00").astimezone(
            datetime.timezone.utc
        ) == datetime.datetime(2025, 10, 9, 4, tzinfo=datetime.timezone.utc)
