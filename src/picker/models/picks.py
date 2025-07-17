import itertools

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.dispatch import Signal

from . import sports
from ..exceptions import PickerResultException
from .. import utils

__all__ = [
    "Preference",
    "PickerGrouping",
    "PickerFavorite",
    "PickerMembership",
    "PickSet",
    "GamePick",
    "GameSetPicks",
]


class PreferenceManager(models.Manager):
    def for_user(self, user):
        return self.get_or_create(user=user)[0]


class Preference(models.Model):
    class Autopick(models.TextChoices):
        NONE = "NONE", "None"
        RAND = "RAND", "Random"

    autopick = models.CharField(max_length=4, choices=Autopick.choices, default=Autopick.RAND)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="picker_preferences",
    )

    objects = PreferenceManager()

    def __str__(self):
        return str("{} Preference".format(self.user))

    @property
    def should_autopick(self):
        return self.autopick != self.Autopick.NONE


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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    league = models.ForeignKey(sports.League, on_delete=models.CASCADE)
    team = models.ForeignKey(sports.Team, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return "{}: {} ({})".format(self.user, self.team, self.league)

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

    def for_user(self, user, league=None):
        kwargs = {"user": user}
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

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="picker_memberships",
    )
    group = models.ForeignKey(PickerGrouping, on_delete=models.CASCADE, related_name="members")
    status = models.CharField(max_length=4, choices=Status.choices, default=Status.ACTIVE)
    autopick = models.CharField(max_length=4, choices=Autopick.choices, default=Autopick.RANDOM)

    objects = MembershipManager()

    def __str__(self):
        return f"{self.user}@{self.group}"

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def is_management(self):
        return self.status == self.Status.MANAGER


class PickSetManager(models.Manager):
    def for_gameset_user(self, gameset, user, strategy=None, autopick=False):
        Strategy = self.model.Strategy
        strategy = strategy or Strategy.USER
        picks, created = self.get_or_create(
            gameset=gameset, user=user, defaults={"strategy": strategy}
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
        USER = "USER", "User"
        RANDOM = "RAND", "Random"
        HOME = "HOME", "Home Team"
        BEST = "BEST", "Best Record"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="picksets"
    )

    gameset = models.ForeignKey(sports.GameSet, on_delete=models.CASCADE, related_name="picksets")
    points = models.PositiveSmallIntegerField(default=0)
    correct = models.PositiveSmallIntegerField(default=0)
    wrong = models.PositiveSmallIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    strategy = models.CharField(max_length=4, choices=Strategy.choices, default=Strategy.USER)
    is_winner = models.BooleanField(default=False)

    objects = PickSetManager()

    updated_signal = Signal()

    class Meta:
        unique_together = (("user", "gameset"),)

    def __str__(self):
        return "%s %s %d" % (self.gameset, self.user, self.correct)

    @property
    def is_autopicked(self):
        return self.strategy != self.Strategy.USER

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
        return "%s: %s - Game %d" % (self.pick.user, self.winner, self.game.id)

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

    def pick_for_user(self, user):
        try:
            return self.picksets.select_related().get(user=user)
        except models.ObjectDoesNotExist:
            return None

    def update_results(self, results):
        """
        results schema: {'sequence': 1, 'season': 2018, 'games': [{
            "home": "HOME",
            "away": "AWAY",
            "home_score": 15,
            "away_score": 10,
            "status": "Final",
            "winner": "HOME",
        }]}
        """

        if not results:
            raise PickerResultException("Results unavailable")

        if results["sequence"] != self.sequence or results["season"] != self.season:
            raise PickerResultException("Results not updated, wrong season or week")

        games = sorted(results["games"], key=lambda g: g.get("start"))
        completed = {g["home"]: g for g in games if g["status"].startswith("F")}
        if not completed:
            return (0, None)

        count = 0
        for game in self.games.incomplete(home__abbr__in=completed.keys()):
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

        result_final = games[-1]
        if result_final["status"].startswith("F"):
            result_score = int(result_final["home_score"]) + int(result_final["away_score"])
            last_game = self.last_game
            if self.points != result_score and last_game.winner:
                if timezone.now() > last_game.end_time:
                    self.points = result_score
                    self.save()

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
        return utils.sorted_standings(
            picks, key=lambda ps: (ps.correct, -ps.points_delta), reverse=True
        )
