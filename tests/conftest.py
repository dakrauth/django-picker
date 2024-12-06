import pytest
from datetime import timedelta
from picker import models as picker
from django.utils import timezone
from django.contrib.auth.models import User

_now = timezone.now()


@pytest.fixture
def now():
    return _now


@pytest.fixture
def league(now):
    league = picker.League.objects.create(
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
def gameset(league, now):
    teams = league.team_dict
    gs = picker.GameSetPicks.objects.create(
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
def grouping(league):
    grouping = picker.PickerGrouping.objects.create(name="grouping")
    grouping.leagues.add(league)
    return grouping


def _make_mbr(user, grouping=None):
    if grouping:
        picker.PickerMembership.objects.create(user=user, group=grouping)
    return user


@pytest.fixture
def superuser(client, grouping):
    su = _make_mbr(
        User.objects.create_superuser(
            username="super", email="super@example.com", password="password"
        ),
        grouping,
    )
    client.force_login(su)
    return su


@pytest.fixture
def user(grouping):
    return _make_mbr(User.objects.create_user("user1", "user1@example.com", "password"), grouping)


@pytest.fixture
def user2(grouping):
    return _make_mbr(User.objects.create_user("user2", "user2@example.com", "password"), grouping)


@pytest.fixture
def user_ng():
    return User.objects.create_user("user3", "user3@example.com", "password")


@pytest.fixture
def users(superuser, user, user2):
    return [superuser, user, user2]
