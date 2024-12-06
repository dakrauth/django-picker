import pytest

from picker import VERSION, get_version
from picker import utils, conf
from picker import models as picker


class TestMisc:
    def test_version(self):
        ver = get_version()
        assert isinstance(ver, str)
        assert tuple(int(i) for i in ver.split(".")) == VERSION


model_urls = [
    "conference",
    "division",
    "gameset",
    "league",
    "pickset",
    "preference",
    "team",
]


@pytest.mark.django_db
class TestAdmin:
    @pytest.mark.parametrize("bit", model_urls)
    def test_landing(self, client, superuser, gameset, bit):
        if bit == "pickset":
            picker.PickSet.objects.create(user=superuser, gameset=gameset)

        r = client.get(f"/admin/picker/{bit}/")
        assert r.status_code == 200

        r = client.get(f"/admin/picker/{bit}/add/")
        assert r.status_code == 200

    def test_gameset_form(self, client, superuser, gameset):
        r = client.get(f"/admin/picker/gameset/{gameset.pk}/change/")
        assert r.status_code == 200

    def test_pickset_inlines(self, client, superuser, gameset):
        ps = picker.PickSet.objects.create(user=superuser, gameset=gameset)
        ps.gamepicks.create(game=gameset.games.first())
        r = client.get(f"/admin/picker/pickset/{ps.pk}/change/")
        assert r.status_code == 200


def can_participate(user, gs):
    return gs


class TestUtils:
    def test_participate(self):
        conf.picker_settings["PARTICIPATION_HOOKS"] = ["tests.test_misc.can_participate"]
        assert utils.can_user_participate(None, True) is True
        assert utils.can_user_participate(None, False) is False

    def test_get_templates(self):
        assert utils.get_templates("foo.html") == "foo.html"
        assert utils.get_templates("@foo.html") == [
            "picker/foo.html",
            "picker/_base/foo.html",
        ]
