from functools import cached_property
import itertools

from django.db import models
from django.db.models import Sum, Count, Q, F, Func, IntegerField
from django.conf import settings
from django.utils import timezone
from django.dispatch import Signal
from django.core.exceptions import ValidationError
from django.db.models.functions import Abs, Cast

from . import sports
from ..exceptions import PickerResultException
from .. import utils

__all__ = [
    "Picker",
    "PickerGrouping",
    "PickerFavorite",
    "PickerMembership",
    "PickSet",
    "GamePick",
    "GameSetPicks",
    "active_pickers_for_league",
]


class Round(Func):
    function = "ROUND"
    template = "%(function)s(%(expressions)s, 1)"


class RosterStats:
    def __init__(self, picker, league, season=None, **kwargs):
        self.picker = picker
        self.season = season
        self.league = league
        self.__dict__.update(kwargs)

    def __repr__(self):
        return f"{__class__.__name__}(picker={self.picker}, correct={self.correct})"


class PickerManager(models.Manager):
    def active(self, **kwargs):
        return self.filter(is_active=True, user__is_active=True, **kwargs)

    def create(self, user=None, name=None, is_active=True):
        if user is None and name is None:
            raise ValidationError("Either user or name required")

        if not name:
            name = user.username

        return super().create(user=user, name=name, is_active=is_active)


class PickerStatsManager(models.Manager):
    stats_prefix = "_pickerstats_v2_"

    def get_annotations(self, q=None):
        prefix = self.stats_prefix
        is_winner_q = Q(picksets__is_winner=True)
        points_q = Q(picksets__gameset__points__gt=0)
        if q:
            is_winner_q &= q
            points_q &= q

        return {
            f"{prefix}correct": Sum("picksets__correct", filter=q, default=0),
            f"{prefix}wrong": Sum("picksets__wrong", filter=q, default=0),
            f"{prefix}picksets_played": Count("picksets__id", filter=q),
            f"{prefix}picksets_won": Count("picksets__pk", filter=is_winner_q),
            f"{prefix}points": Sum("picksets__points", filter=q),
            f"{prefix}total_points_weeks": Count("picksets", filter=points_q),
            f"{prefix}actual_points": Sum("picksets__gameset__points", filter=q),
            f"{prefix}points_delta": Sum(
                Abs(
                    Cast(F("picksets__points"), output_field=IntegerField()) -
                    Cast(F("picksets__gameset__points"), output_field=IntegerField())
                ),
                filter=points_q,
            ),
            f"{prefix}avg_points_delta": F(f"{prefix}points_delta") / F(f"{prefix}total_points_weeks"),
            f"{prefix}total_correct_wrong": F(f"{prefix}correct") + F(f"{prefix}wrong"),
            f"{prefix}pct": Round(
                F(f"{prefix}correct") * 100.0 / (F(f"{prefix}correct") + F(f"{prefix}wrong"))
            ),
        }

    def stats_queryset(self, league, group=None, season=None, picker=None):
        q = Q(picksets__gameset__league=league)
        if season:
            q &= Q(picksets__gameset__season=season)

        annotations = self.get_annotations(q)
        queryset = self.filter(Q(picksets__correct__gt=0) | Q(picksets__wrong__gt=0))

        if group:
            queryset = queryset.filter(picker_memberships__group=group)

        if picker:
            queryset = queryset.filter(id=picker.id)

        return queryset.annotate(**annotations)

    def _prefixed_attrs(self, obj):
        prefix = self.stats_prefix
        return {k.replace(prefix, ""): v for k, v in vars(obj).items() if k.startswith(prefix)}

    def _for_group(self, group, league, season=None):
        prefix = self.stats_prefix
        queryset = self.stats_queryset(league, group, season).order_by(
            f"-{prefix}correct", f"{prefix}points_delta", f"-{prefix}picksets_won"
        )

        items = []
        for obj in queryset:
            items.append(RosterStats(obj, league, season, **self._prefixed_attrs(obj)))

        return utils.weighted_standings(items)

    def group_stats(self, group, league, season=None):
        all_stats = self._for_group(group, league)
        by_picker = {e.picker: e for e in all_stats}

        season_stats = self._for_group(group, league, season or league.current_season)
        return [(stat, by_picker[stat.picker]) for stat in season_stats]

    def for_picker(self, picker, league):
        seasons = list(league.available_seasons) + [None]
        items = []
        for season in seasons:
            queryset = self.stats_queryset(league, season=season, picker=picker)
            if not queryset:
                continue

            r = RosterStats(picker, league, season, **self._prefixed_attrs(queryset[0]))
            if r.picksets_played:
                items.append(r)

        return items


class Picker(models.Model):
    name = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField()
    autopick_enabled = models.BooleanField(default=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="picker",
        null=True,
        blank=True,
    )

    objects = PickerManager()
    stats = PickerStatsManager()

    def __str__(self):
        return self.name

    @cached_property
    def is_manager(self):
        return self.user.is_superuser or self.user.is_staff

    @cached_property
    def email(self):
        return self.user.email

    @cached_property
    def last_login(self):
        return self.user.last_login

    @classmethod
    def from_user(cls, user):
        if not user.id:
            return None

        try:
            return cls.objects.get(user=user)
        except Picker.DoesNotExist:
            return None


class PickerGroupingManager(models.Manager):
    def active(self):
        return self.filter(
            status=self.model.Status.ACTIVE, leagues__is_active=True
        ).prefetch_related("leagues", "members")


class PickerGrouping(models.Model):
    class Category(models.TextChoices):
        PUBLIC = "PUB", "Public"
        PROTECTED = "PRT", "Protected"
        PRIVATE = "PVT", "Private"

    class Status(models.TextChoices):
        ACTIVE = "ACTV", "Active"
        INACTIVE = "IDLE", "Inactive"

    name = models.CharField(max_length=75, unique=True)
    leagues = models.ManyToManyField(sports.League, blank=True)
    status = models.CharField(max_length=4, choices=Status.choices, default=Status.ACTIVE)
    category = models.CharField(max_length=3, choices=Category.choices, default=Category.PRIVATE)

    objects = PickerGroupingManager()

    def __str__(self):
        return self.name


class PickerFavorite(models.Model):
    picker = models.ForeignKey(
        Picker,
        on_delete=models.CASCADE,
        related_name="picker_favorites",
        null=True,
        blank=True,
        default=None,
    )
    league = models.ForeignKey(sports.League, on_delete=models.CASCADE)
    team = models.ForeignKey(sports.Team, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return "{}: {} ({})".format(self.picker, self.team, self.league)

    def save(self, *args, **kws):
        if self.team and self.team.league != self.league:
            raise ValueError("Team {} not in league {}".format(self.team, self.league))

        return super().save(*args, **kws)


class MembershipManager(models.Manager):
    def active(self, **kwargs):
        return (
            self.filter(
                status=self.model.Status.ACTIVE,
                group__status=PickerGrouping.Status.ACTIVE,
                **kwargs,
            )
            .select_related("group")
            .prefetch_related(
                models.Prefetch("group__leagues", queryset=sports.League.objects.active())
            )
        )

    def for_picker(self, picker, league=None):
        if not (isinstance(picker, Picker) and picker.is_active):
            return self.none()

        kwargs = {"picker": picker}
        if league:
            kwargs["group__leagues"] = league

        return self.active(**kwargs)


class PickerMembership(models.Model):
    class Autopick(models.TextChoices):
        NONE = "NONE", "None"
        RANDOM = "RAND", "Random"

    class Status(models.TextChoices):
        ACTIVE = "ACTV", "Active"
        INACTIVE = "IDLE", "Inactive"
        SUSPENDED = "SUSP", "Suspended"
        MANAGER = "MNGT", "Manager"

    picker = models.ForeignKey(
        Picker,
        on_delete=models.CASCADE,
        related_name="picker_memberships",
        null=True,
        blank=True,
        default=None,
    )
    group = models.ForeignKey(PickerGrouping, on_delete=models.CASCADE, related_name="members")
    status = models.CharField(max_length=4, choices=Status.choices, default=Status.ACTIVE)
    autopick = models.CharField(max_length=4, choices=Autopick.choices, default=Autopick.RANDOM)

    objects = MembershipManager()

    def __str__(self):
        return f"{self.picker}@{self.group}"

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def is_management(self):
        return self.status == self.Status.MANAGER

    @property
    def should_autopick(self):
        return self.autopick != self.Autopick.NONE


def active_pickers_for_league(league, **kwargs):
    return Picker.objects.filter(
        is_active=True,
        picker_memberships__group__leagues=league,
        picker_memberships__status__in=(
            PickerMembership.Status.ACTIVE,
            PickerMembership.Status.MANAGER,
        ),
        picker_memberships__group__status=PickerGrouping.Status.ACTIVE,
        **kwargs,
    )


class PickSetManager(models.Manager):
    def for_gameset_picker(self, gameset, picker, strategy=None, autopick=False):
        Strategy = self.model.Strategy
        strategy = strategy or Strategy.PICKER
        picks, created = self.get_or_create(
            gameset=gameset, picker=picker, defaults={"strategy": strategy}
        )
        if created and autopick:
            picks.points = gameset.league.random_points()
            picks.save()

        games = set(gameset.games.values_list("id", flat=True))
        if not created:
            games -= set(picks.gamepicks.values_list("game__id", flat=True))

        for game in gameset.games.filter(id__in=games).select_related():
            winner = game.get_random_winner() if autopick else None
            picks.gamepicks.create(game=game, winner=winner)

        return picks


class PickSet(models.Model):
    class Strategy(models.TextChoices):
        PICKER = "PICK", "Picker"
        RANDOM = "RAND", "Random"
        HOME = "HOME", "Home Team"
        BEST = "BEST", "Best Record"

    picker = models.ForeignKey(
        Picker,
        on_delete=models.CASCADE,
        related_name="picksets",
        null=True,
        blank=True,
        default=None,
    )
    gameset = models.ForeignKey(sports.GameSet, on_delete=models.CASCADE, related_name="picksets")
    points = models.PositiveSmallIntegerField(default=0)
    correct = models.PositiveSmallIntegerField(default=0)
    wrong = models.PositiveSmallIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    strategy = models.CharField(max_length=4, choices=Strategy.choices, default=Strategy.PICKER)
    is_winner = models.BooleanField(default=False)

    objects = PickSetManager()

    updated_signal = Signal()

    class Meta:
        unique_together = (("picker", "gameset"),)

    def __str__(self):
        return "%s %s %d" % (self.gameset, self.picker, self.correct)

    @property
    def is_autopicked(self):
        return self.strategy != self.Strategy.PICKER

    @property
    def is_complete(self):
        return False if self.points == 0 else (self.progress == self.gameset.games.count())

    @property
    def progress(self):
        return self.gamepicks.filter(winner__isnull=False).count()

    def update_status(self, is_winner=False):
        picks = self.gamepicks.all()
        self.correct = sum([1 for gp in picks if gp.is_correct])
        self.wrong = len(picks) - self.correct
        self.is_winner = is_winner
        self.save()
        return self.correct

    @property
    def points_delta(self):
        if self.gameset.points == 0:
            return 0

        return abs(self.points - self.gameset.points)

    def update_picks(self, games=None, points=None):
        """
        games can be dict of {game.id: winner_id} for all picked games to update
        """
        if games:
            game_dict = {g.id: g for g in self.gameset.games.filter(id__in=games)}
            game_picks = {pick.game.id: pick for pick in self.gamepicks.filter(game__id__in=games)}
            for key, winner in games.items():
                game = game_dict[key]
                if not game.has_started:
                    pick = game_picks[key]
                    pick.winner_id = winner
                    pick.save()

        if points is not None:
            self.points = points
            self.save()

        if games or points:
            self.updated_signal.send(sender=self.__class__, pickset=self, auto_pick=False)


class GamePickManager(models.Manager):
    def games_started(self):
        return self.filter(game__start_time__lte=timezone.now())

    def games_started_display(self):
        return self.games_started().values_list("game__id", "winner__abbr")

    def picked_winner_ids(self):
        return self.filter(winner__isnull=False).values_list("game__id", "winner__id")


class GamePick(models.Model):
    game = models.ForeignKey(sports.Game, on_delete=models.CASCADE, related_name="gamepicks")
    winner = models.ForeignKey(sports.Team, on_delete=models.SET_NULL, null=True, blank=True)
    pick = models.ForeignKey(PickSet, on_delete=models.CASCADE, related_name="gamepicks")
    confidence = models.PositiveIntegerField(default=0)

    objects = GamePickManager()

    class Meta:
        ordering = ("game__start_time", "game__away")

    def __str__(self):
        return f"{self.pick.picker}: {self.winner} - Game {self.game.id}"

    def set_random_winner(self, force=False):
        if self.winner is None or force:
            self.winner = self.game.get_random_winner()
            self.save()

    @property
    def start_time(self):
        return self.game.start_time

    @property
    def short_description(self):
        return self.game.short_description

    @property
    def winner_abbr(self):
        return self.winner.abbr if self.winner else "N/A"

    @property
    def picked_home(self):
        return self.winner == self.game.home

    @property
    def picked_away(self):
        return self.winner == self.game.away

    @property
    def is_correct(self):
        winner = self.game.winner
        if winner:
            return self.winner == winner

        return None


class GameSetPicksManager(models.Manager):
    def current_gameset(self, league):
        rel = timezone.now()
        try:
            return self.get(league=league, opens__lte=rel, closes__gte=rel)
        except GameSetPicks.DoesNotExist:
            pass

        try:
            return self.filter(league=league, points=0, opens__gte=rel).earliest("opens")
        except GameSetPicks.DoesNotExist:
            pass

        try:
            return self.filter(league=league, closes__lte=rel).latest("closes")
        except sports.GameSet.DoesNotExist:
            return None


class GameSetPicks(sports.GameSet):
    objects = GameSetPicksManager()

    class Meta:
        proxy = True

    def pick_for_picker(self, picker):
        try:
            return self.picksets.select_related().get(picker=picker)
        except models.ObjectDoesNotExist:
            return None

    def _update_points(self, result):
        last_game = self.last_game
        if not (result["home"] == last_game.home.abbr and result["status"].startswith("F")):
            return

        score = int(result["home_score"]) + int(result["away_score"])
        if self.points != score and last_game.winner:
            if timezone.now() > last_game.end_time:
                self.points = score
                self.save()

    def update_results(self, results):
        """
        results schema: {'sequence': 1, 'season': 2018, 'games': [{
            "home": "HOME",
            "away": "AWAY",
            "home_score": 15,
            "away_score": 10,
            "status": "Final",
            "winner": "HOME",
            "start": "2025-10-15T13:00Z"
        }]}
        """

        if not results:
            raise PickerResultException("Results unavailable")

        if results["sequence"] != self.sequence or results["season"] != self.season:
            raise PickerResultException("Results not updated, wrong season or week")

        results_games = sorted(results["games"], key=lambda g: g.get("start"))
        completed = {g["home"]: g for g in results_games if g["status"].startswith("F")}
        if not completed:
            return (0, None)

        count = 0
        all_games = list(self.games.select_related("home", "away"))
        incomplete_games = [
            g for g in all_games if g.home.abbr in completed and g.status == g.Status.UNPLAYED
        ]
        for game in incomplete_games:
            result = completed.get(game.home.abbr, None)
            if result:
                winner = result["winner"]
                game.winner = (
                    game.home
                    if game.home.abbr == winner
                    else game.away
                    if game.away.abbr == winner
                    else None
                )
                count += 1

        self._update_points(results_games[-1])
        if count:
            self.update_pick_status()

        return (count, self.points)

    def winners(self):
        if self.points:
            yield from itertools.takewhile(lambda i: i.place == 1, self.results())

    def update_pick_status(self):
        winners = set(w.id for w in self.winners())
        for wp in self.picksets.all():
            wp.update_status(wp.id in winners)

    def results(self):
        picks = list(self.picksets.select_related())
        return utils.weighted_standings(
            sorted(picks, key=lambda ps: (ps.correct, -ps.points_delta), reverse=True)
        )
