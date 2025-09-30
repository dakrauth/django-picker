import string
import random
import pytest
from datetime import timedelta
from picker.models import League, GameSetPicks, PickerGrouping, PickerMembership, Picker
from django.utils import timezone
from django.contrib.auth.models import User

_now = timezone.now()


@pytest.fixture
def now():
    return _now


@pytest.fixture
def league(now):
    league = League.objects.create(
        name="Hogwarts Quidditch",
        slug="hq",
        abbr="HQ",
        current_season=now.year,
    )
    conf = league.conferences.create(name="Hogwarts", abbr="HW")
    division = conf.divisions.create(name="Varsity")
    for tm in [
        {
            "id": 1,
            "abbr": "GRF",
            "name": "Gryffindor",
            "logo": "picker/logos/hq/12656_Gold.jpg",
            "colors": "#c40002,#f39f00",
            "nickname": "Lions",
        },  # noqa
        {
            "id": 2,
            "abbr": "HUF",
            "name": "Hufflepuff",
            "logo": "picker/logos/hq/12657_Black.jpg",
            "colors": "#fff300,#000000",
            "nickname": "Badgers",
        },  # noqa
        {
            "id": 3,
            "abbr": "RVN",
            "name": "Ravenclaw",
            "logo": "picker/logos/hq/12654_Navy.jpg",
            "colors": "#0644ad,#7e4831",
            "nickname": "Eagles",
        },  # noqa
        {
            "id": 4,
            "abbr": "SLY",
            "name": "Slytherin",
            "logo": "picker/logos/hq/12655_Dark_Green.jpg",
            "colors": "#004101,#dcdcdc",
            "nickname": "Serpents",
        },  # noqa
    ]:
        league.teams.create(conference=conf, division=division, **tm)

    return league


@pytest.fixture
def teams(league):
    return list(league.teams.all())


@pytest.fixture
def gameset(league, now):
    teams = league.team_dict
    gs = GameSetPicks.objects.create(
        league=league,
        season=now.year,
        sequence=1,
        points=0,
        opens=now - timedelta(days=1),
        closes=now + timedelta(days=6),
    )
    for away, home in [["GRF", "HUF"], ["RVN", "SLY"]]:
        gs.games.create(home=teams[home], away=teams[away], start_time=now, location="Hogwards")
    return gs


@pytest.fixture
def gamesets(league, now):
    teams = league.team_dict
    gamesets = []

    for i, data in enumerate(
        [
            [["GRF", "HUF"], ["RVN", "SLY"]],
            [["GRF", "RVN"], ["HUF", "SLY"]],
            [["SLY", "GRF"], ["HUF", "RVN"]],
        ]
    ):
        rel = now + timedelta(days=i * 7)
        gs = league.gamesets.create(
            season=now.year,
            sequence=i + 1,
            points=0,
            opens=rel - timedelta(days=1),
            closes=rel + timedelta(days=6),
        )
        gamesets.append(gs)
        for j, (away, home) in enumerate(data, 1):
            gs.games.create(
                home=teams[home],
                away=teams[away],
                start_time=rel + timedelta(days=j),
                location="Hogwards",
            )

    return gamesets


@pytest.fixture
def grouping2(league):
    grouping = PickerGrouping.objects.create(name="grouping2")
    grouping.leagues.add(league)
    return grouping


@pytest.fixture
def grouping(league):
    grouping = PickerGrouping.objects.create(name="grouping")
    grouping.leagues.add(league)
    return grouping


def _make_mbr(picker, grouping):
    PickerMembership.objects.create(picker=picker, group=grouping)
    return picker


def create_user(username, email, passwd):
    return User.objects.create_user(username, email, passwd)


def create_picker(user):
    return Picker.objects.create(name=user.username, is_active=True, user=user)


@pytest.fixture
def user():
    name = "".join(random.sample(list(string.ascii_lowercase) * 3, 8))
    return create_user(name, f"{name}@example.com", "password")


@pytest.fixture
def superuser(client, grouping):
    su = User.objects.create_superuser(
        username="super", email="super@example.com", password="password"
    )
    client.force_login(su)
    return _make_mbr(create_picker(su), grouping)


@pytest.fixture
def picker(grouping):
    return _make_mbr(create_picker(create_user("user1", "user1@example.com", "password")), grouping)


@pytest.fixture
def picker2(grouping):
    return _make_mbr(create_picker(create_user("user2", "user2@example.com", "password")), grouping)


@pytest.fixture
def picker_ng():
    return create_picker(create_user("user3", "user3@example.com", "password"))


@pytest.fixture
def pickers(superuser, picker, picker2):
    return [superuser, picker, picker2]
