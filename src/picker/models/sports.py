import random
from datetime import timedelta
from collections import ChainMap, OrderedDict
from functools import partialmethod
from types import SimpleNamespace

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.db import OperationalError
from django.utils.functional import cached_property
from django.core.exceptions import ValidationError

from dateutil.parser import parse as parse_dt

from ..conf import picker_settings
from .. import importers
from ..utils import random_bool

__all__ = [
    "League",
    "GameSet",
    "Team",
    "Game",
    "Conference",
    "Division",
    "Alias",
    "temp_slug",
    "valid_team_abbr",
    "TIE_KEY",
]

LOGOS_DIR = picker_settings.get("LOGOS_UPLOAD_DIR", "picker/logos")
TIE_KEY = "__TIE__"


def temp_slug():
    return "{:10.0f}".format(random.random() * 10000000000)


class LeagueManager(models.Manager):
    def active(self):
        return self.filter(is_active=True)


class League(models.Model):
    name = models.CharField(max_length=50, unique=True)
    abbr = models.CharField(max_length=8)
    logo = models.ImageField(upload_to=LOGOS_DIR, blank=True, null=True)
    current_season = models.IntegerField(blank=True, null=True)
    slug = models.SlugField(default=temp_slug)
    avg_game_duration = models.PositiveIntegerField(default=240)
    is_active = models.BooleanField(default=True)

    objects = LeagueManager()

    class Meta:
        permissions = (("can_update_score", "Can update scores"),)

    def __str__(self):
        return self.name

    def _reverse(self, name):
        return reverse(name, args=[self.slug])

    get_absolute_url = partialmethod(_reverse, "picker-home")
    picks_url = partialmethod(_reverse, "picker-picks")
    results_url = partialmethod(_reverse, "picker-results")
    roster_url = partialmethod(_reverse, "picker-roster")
    teams_url = partialmethod(_reverse, "picker-teams")
    schedule_url = partialmethod(_reverse, "picker-schedule")
    manage_url = partialmethod(_reverse, "picker-manage")

    def to_dict(self):
        return {
            "schema": "complete",
            "league": {
                "schema": "league",
                "name": self.name,
                "slug": self.slug,
                "abbr": self.abbr,
                "current_season": self.current_season,
                "is_active": self.is_active,
                "teams": [team.to_dict() for team in self.teams.all()],
            },
            "season": {
                "schema": "season",
                "league": self.abbr,
                "season": self.current_season,
                "gamesets": [
                    gs.to_dict() for gs in self.gamesets.filter(season=self.current_season)
                ],
            },
        }

    @cached_property
    def team_list(self):
        return list(
            Team.objects
            .filter(league=self)
            .select_related("league", "conference", "division")
        )
    
    @cached_property
    def team_dict(self):
        names = {}
        aliases = {}
        for tm_id, name in Alias.objects.filter(team__league=self).values_list("team_id", "name"):
            aliases.setdefault(tm_id, []).append(name)

        for team in self.team_list:
            names[team.abbr.lower()] = team
            names[team.abbr.upper()] = team
            names[team.id] = team
            if team.nickname:
                full_name = "{} {}".format(team.name, team.nickname)
                names[full_name] = team

            if team.id in aliases:
                for name in aliases[team.id]:
                    names[name] = team

        return names

    def team(self, key):
        return self.team_dict[key]

    @property
    def latest_gameset(self):
        rel = timezone.now()
        try:
            return self.gamesets.filter(points=0, opens__gte=rel).earliest("opens")
        except GameSet.DoesNotExist:
            pass

        try:
            return self.gamesets.filter(closes__lte=rel).latest("closes")
        except GameSet.DoesNotExist:
            return None

    @property
    def latest_season(self):
        gs = self.latest_gameset
        return gs.season if gs else None

    @property
    def current_gameset(self):
        rel = timezone.now()
        return self.gamesets.filter(opens__lte=rel, closes__gte=rel).order_by("opens").first()

    @cached_property
    def available_seasons(self):
        return self.gamesets.order_by("-season").values_list("season", flat=True).distinct()

    def season_gamesets(self, season=None):
        season = season or self.current_season or self.latest_season
        return self.gamesets.filter(season=season)

    def random_points(self):
        d = self.gamesets.filter(points__gt=0).aggregate(
            stddev=models.StdDev("points"), avg=models.Avg("points")
        )
        avg = int(d.get("avg") or 0)
        stddev = int(d.get("stddev") or 0)
        return random.randint(avg - stddev, avg + stddev)

    @cached_property
    def _config(self):
        core = {}
        base = {}
        league = {}
        for key, value in picker_settings.items():
            if key == "_BASE":
                base = picker_settings[key]
            elif isinstance(value, dict) and key == self.abbr:
                league = value
            else:
                core[key] = value

        return ChainMap(league, base, core)

    def config(self, key=None, default=None):
        if key is None:
            return SimpleNamespace(**self._config)

        return self._config.get(key, default)

    @classmethod
    def import_season(cls, data):
        return importers.import_season(cls, data)

    @classmethod
    def import_league(cls, data):
        return importers.import_league(cls, data)

    @classmethod
    def get(cls, abbr=None):
        abbr = abbr or picker_settings.get("DEFAULT_LEAGUE", "nfl")
        return cls.objects.get(abbr__iexact=abbr)


class Conference(models.Model):
    name = models.CharField(max_length=50)
    abbr = models.CharField(max_length=8)
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name="conferences")

    def __str__(self):
        return self.name


class Division(models.Model):
    name = models.CharField(max_length=50)
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE, related_name="divisions")

    def __str__(self):
        return "{} {}".format(self.conference.name, self.name)


def valid_team_abbr(value):
    if value.startswith("__"):
        raise ValidationError('Team abbr cannot start with "__"')
    

class Team(models.Model):
    """
    Common team attributes.
    """

    name = models.CharField(max_length=50)
    abbr = models.CharField(max_length=8, blank=True, validators=[valid_team_abbr])
    nickname = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=100, blank=True)
    coach = models.CharField(max_length=50, blank=True)
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name="teams")
    conference = models.ForeignKey(
        Conference,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="teams",
    )
    division = models.ForeignKey(
        Division, on_delete=models.SET_NULL, blank=True, null=True, related_name="teams"
    )
    colors = models.CharField(max_length=40, blank=True)
    logo = models.ImageField(upload_to=LOGOS_DIR, blank=True, null=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ("name",)
        base_manager_name = "objects"

    def __str__(self):
        return "{} {}".format(self.name, self.nickname)

    def get_absolute_url(self):
        return reverse("picker-team", args=[self.league.slug, self.abbr])

    def to_dict(self):
        return {
            "abbr": self.abbr,
            "logo": self.logo.name,
            "name": self.name,
            "nickname": self.nickname,
            "sub": [self.conference.name, self.division.name],
            "aliases": list(self.aliases.values_list("name", flat=True)),
            "coach": self.coach,
            "location": self.location,
        }

    def season_record(self, season=None):
        season = season or self.league.current_season
        Q, Count, Status = models.Q, models.Count, Game.Status
        values = Game.objects.filter(gameset__season=season).aggregate(
            wins=Count(
                "pk",
                filter=Q(status=Status.AWAY_WIN, away=self) | Q(status=Status.HOME_WIN, home=self),
            ),
            losses=Count(
                "pk",
                filter=Q(status=Status.AWAY_WIN, home=self) | Q(status=Status.HOME_WIN, away=self),
            ),
            ties=Count("pk", filter=Q(status=Status.TIE, away=self) | Q(status=Status.TIE, home=self)),
        )
        return (values["wins"], values["losses"], values["ties"])

    def season_points(self, season=None):
        w, l, t = self.season_record(season)
        return w * 2 + t

    @property
    def record(self):
        return self.season_record()

    @property
    def record_as_string(self):
        record = self.record
        if not record[2]:
            record = record[:2]
        return "-".join(str(s) for s in record)

    @property
    def color_options(self):
        if not self.colors:
            return []

        return [color if color.startswith("#") else f"#{color}" for color in self.colors.split(",")]

    def schedule(self, season=None):
        return Game.objects.select_related("gameset").filter(
            models.Q(away=self) | models.Q(home=self),
            gameset__season=season or self.league.current_season,
        )

    def byes(self, season=None):
        return self.bye_set.filter(season=season or self.league.current_season)

    def complete_record(self):
        home_games = [0, 0, 0]
        away_games = [0, 0, 0]

        for games, accum, status in (
            (self.away_games, away_games, Game.Status.AWAY_WIN),
            (self.home_games, home_games, Game.Status.HOME_WIN),
        ):
            for res in games.exclude(status=Game.Status.UNPLAYED).values_list("status", flat=True):
                if res == status:
                    accum[0] += 1
                elif res == Game.Status.TIE:
                    accum[2] += 1
                else:
                    accum[1] += 1

        return [
            home_games,
            away_games,
            [
                away_games[0] + home_games[0],
                away_games[1] + home_games[1],
                away_games[2] + home_games[2],
            ],
        ]


class Alias(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="aliases")
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class GameSet(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name="gamesets")
    season = models.PositiveSmallIntegerField()
    sequence = models.PositiveSmallIntegerField()
    points = models.PositiveSmallIntegerField(default=0)
    opens = models.DateTimeField()
    closes = models.DateTimeField()
    description = models.CharField(max_length=60, default="", blank=True)
    label = models.CharField(max_length=12, blank=True)

    byes = models.ManyToManyField(
        Team, blank=True, verbose_name="Bye Teams", related_name="bye_set"
    )

    class Meta:
        ordering = ("season", "sequence")

    def __str__(self):
        return "{}:{}".format(self.sequence, self.season)

    def picks_url(self):
        return reverse(
            "picker-picks-sequence",
            args=[self.league.slug, str(self.season), str(self.sequence)],
        )

    def to_dict(self):
        return {
            "byes": list(self.byes.values_list("abbr", flat=True)),
            "opens": self.opens.isoformat(),
            "closes": self.closes.isoformat(),
            "games": [g.to_dict() for g in self.games.select_related("home", "away")],
        }

    def import_games(self, data, teams=None):
        teams = teams or self.league.team_dict
        byes = data.get("byes")
        if byes:
            self.byes.add(*[teams[t] for t in byes])

        games = []
        for dct in data["games"]:
            start_time = parse_dt(dct["start"])
            game, is_new = self.games.get_or_create(
                home=teams.get(dct["home"]),
                away=teams.get(dct["away"]),
                defaults={"start_time": start_time},
            )
            game.start_time = start_time
            game.description = dct.get("description", game.description)
            game.tv = dct.get("tv", game.tv)
            game.location = dct.get("location", game.location)
            game.notes = dct.get("notes", game.notes)
            game.save()
            games.append([game, is_new])

        return games

    @cached_property
    def next_gameset(self):
        try:
            return self.league.gamesets.get(season=self.season, sequence=self.sequence + 1)
        except GameSet.DoesNotExist:
            return None

    @cached_property
    def previous_gameset(self):
        if self.sequence > 1:
            return self.league.gamesets.get(season=self.season, sequence=self.sequence - 1)

    @cached_property
    def dates(self):
        return sorted(set(d.date() for d in self.games.values_list("start_time", flat=True)))

    @cached_property
    def last_game(self):
        return self.games.last()

    @cached_property
    def first_game(self):
        return self.games.first()

    @cached_property
    def start_time(self):
        return self.first_game.start_time

    @property
    def end_time(self):
        return self.last_game.end_time

    @property
    def in_progress(self):
        return self.end_time >= timezone.now() >= self.start_time

    @property
    def has_started(self):
        return timezone.now() >= self.start_time

    @property
    def is_open(self):
        gm = self.last_game
        return (timezone.now() < self.last_game.start_time) if gm else False

    def reset_games_status(self):
        UNPLAYED = Game.Status.UNPLAYED
        self.games.exclude(status=UNPLAYED).update(status=UNPLAYED)


class GameManager(models.Manager):
    def display_results(self):
        return OrderedDict(
            [
                (item["id"], item)
                for item in self.games_started()
                .annotate(
                    winner=models.Case(
                        models.When(status="H", then="home__abbr"),
                        models.When(status="A", then="away__abbr"),
                        models.When(status="T", then=models.Value(TIE_KEY)),
                        default=None,
                        output_field=models.CharField(),
                    )
                )
                .values("id", "home__abbr", "away__abbr", "winner")
            ]
        )

    def games_started(self):
        return self.filter(start_time__lte=timezone.now())

    def incomplete(self, **kws):
        kws["status"] = self.model.Status.UNPLAYED
        return self.filter(**kws)

    def played(self, **kws):
        Status = self.model.Status
        kws["status__in"] = [Status.TIE, Status.HOME_WIN, Status.AWAY_WIN]
        return self.filter(**kws)


class Game(models.Model):
    class Category(models.TextChoices):
        REGULAR = "REG", "Regular Season"
        POST = "POST", "Post Season"
        PRE = "PRE", "Pre Season"
        FRIENDLY = "FRND", "Friendly"

    class Status(models.TextChoices):
        UNPLAYED = "U", "Unplayed"
        TIE = "T", "Tie"
        HOME_WIN = "H", "Home Win"
        AWAY_WIN = "A", "Away Win"
        CANCELLED = "X", "Cancelled"

    home = models.ForeignKey(
        Team,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="home_games",
    )
    home_score = models.PositiveIntegerField(default=0)
    away = models.ForeignKey(
        Team,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="away_games",
    )
    away_score = models.PositiveIntegerField(default=0)
    gameset = models.ForeignKey(GameSet, on_delete=models.CASCADE, related_name="games")
    start_time = models.DateTimeField()
    tv = models.CharField("TV", max_length=24, blank=True)
    notes = models.TextField(blank=True)
    category = models.CharField(max_length=4, choices=Category.choices, default=Category.REGULAR)
    status = models.CharField(max_length=1, choices=Status.choices, default=Status.UNPLAYED)
    location = models.CharField(blank=True, default="", max_length=60)
    description = models.CharField(max_length=60, default="", blank=True)

    objects = GameManager()

    class Meta:
        ordering = ("start_time", "away")

    def __str__(self):
        return "{} @ {} {}".format(self.away.abbr, self.home.abbr, self.gameset)

    def to_dict(self):
        return {
            "away": self.away.abbr,
            "home": self.home.abbr,
            "start": self.start_time.isoformat(),
            "tv": self.tv,
            "location": self.location,
        }

    @property
    def is_tie(self):
        return self.status == self.Status.TIE

    @property
    def has_started(self):
        return timezone.now() >= self.start_time

    @property
    def short_description(self):
        return "%s @ %s" % (self.away, self.home)

    @property
    def vs_description(self):
        return "%s vs %s" % (self.away.nickname, self.home.nickname)

    @property
    def is_home_win(self):
        return self.status == self.Status.HOME_WIN

    @property
    def is_away_win(self):
        return self.status == self.Status.AWAY_WIN

    @property
    def winner(self):
        if self.status == self.Status.HOME_WIN:
            return self.home

        if self.status == self.Status.AWAY_WIN:
            return self.away

        return None

    @winner.setter
    def winner(self, team):
        """``team`` can be either a Team instance or PK, or ``None`` to indicate a tie"""
        if team is None:
            self.status = self.Status.TIE
        else:
            team_id = team.id if isinstance(team, Team) else int(team)
            if team_id == self.away.id:
                self.status = self.Status.AWAY_WIN
            elif team_id == self.home.id:
                self.status = self.Status.HOME_WIN
            else:
                raise ValueError(f"{team} is not a valid winning team")

        self.save()

    def get_random_winner(self):
        return self.home if random_bool() else self.away

    @property
    def end_time(self):
        return self.start_time + timedelta(minutes=self.gameset.league.avg_game_duration)

    @property
    def in_progress(self):
        now = timezone.now()
        return self.end_time >= now >= self.start_time
