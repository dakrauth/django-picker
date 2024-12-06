import os
import json

import pytest
from django.urls import reverse
from django.core.management import call_command

from picker import models as picker
from picker import importers, exceptions


def load_json(filename):
    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath) as fin:
        return json.load(fin)


@pytest.mark.django_db
class TestImporters:
    def test_import_schema(self):
        try:
            importers.valid_schema({}, "complete")
        except exceptions.PickerConfigurationError:
            pass
        else:
            assert False

        try:
            importers.valid_schema({"schema": "league"}, "complete")
        except exceptions.PickerConfigurationError:
            pass
        else:
            assert False

    def test_management_commands(self):
        call_command("import_picks", "tests/quidditch.json")
        data = load_json("quidditch.json")
        data["season"]["gamesets"][0].update(opens="2018-08-18T00:30Z", closes="2018-09-07T12:00Z")
        league = picker.League.get("hq")
        gs = league.gamesets.first()
        opens, closes = gs.opens, gs.closes
        importers.import_season(picker.League, data)
        gs = picker.GameSet.objects.first()
        assert opens != gs.opens
        assert closes != gs.closes

    def test_import(self, client):
        nfl_data = load_json("nfl2019.json")

        league_info, teams_info = picker.League.import_league(nfl_data["league"])
        league, created = league_info
        assert created is True

        assert league.slug == "nfl"
        assert league.abbr == "NFL"
        assert league.current_season == 2019
        assert league.conferences.count() == 2
        assert picker.Division.objects.count() == 8
        assert league.teams.count() == 32

        info = league.import_season(nfl_data["season"])
        assert len(info) == 17
        assert league.gamesets.first().sequence == 1
        for gs, is_new, games in info:
            assert is_new is True
            assert all(is_new for g, is_new in games)
        assert picker.Game.objects.incomplete().count() == 256

        assert picker.Alias.objects.count() == 10
        td = league.team_dict
        assert td["WAS"] == td["WSH"]

        assert league.config("TEAM_PICKER_WIDGET") == "django.forms.RadioSelect"

        tm = picker.Team.objects.get(league=league, nickname="Jaguars")
        aliases = list(tm.aliases.values_list("name", flat=True))
        assert aliases == ["JAX"]
        assert str(aliases[0]) == "JAX"

        assert tm.season_points() == 0
        assert tm.complete_record() == [[0, 0, 0], [0, 0, 0], [0, 0, 0]]

        # /<league>/teams/    picker.views.picks.Teams    picker-teams
        r = client.get(reverse("picker-teams", args=["nfl"]))
        assert r.status_code == 200

        # /<league>/teams/<var>/  picker.views.picks.Team picker-team
        r = client.get(reverse("picker-team", args=["nfl", "SEA"]))
        assert r.status_code == 200

        # /<league>/schedule/ picker.views.picks.Schedule picker-schedule
        r = client.get(reverse("picker-schedule", args=["nfl"]))
        assert r.status_code == 200

        # /<league>/schedule/<season>/    picker.views.picks.Schedule picker-schedule-year
        r = client.get(reverse("picker-schedule-year", args=["nfl", "2019"]))
        assert r.status_code == 200
