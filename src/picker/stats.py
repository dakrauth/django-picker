from django.db.models import Q
from django.contrib.auth import get_user_model
from .utils import sorted_standings


def percent(num, denom):
    return 0.0 if denom == 0 else num / denom * 100.0


class RosterStats:
    def __init__(self, user, league, season=None):
        self.user = user
        self.season = season
        self.league = league
        self.correct = 0
        self.wrong = 0
        self.points_delta = 0

        queryset = (
            self.user.picksets.filter(gameset__league=league)
            .select_related()
            .filter(Q(correct__gt=0) | Q(wrong__gt=0))
        )

        if season:
            queryset = queryset.filter(gameset__season=season)

        self.picksets_played = 0
        self.picksets_won = 0
        for correct, wrong, is_winner, points, actual_points in queryset.values_list(
            "correct", "wrong", "is_winner", "points", "gameset__points"
        ):
            self.picksets_played += 1
            self.correct += correct
            self.wrong += wrong
            if actual_points:
                self.points_delta += abs(points - actual_points)

            if is_winner:
                self.picksets_won += 1

        self.is_active = self.user.is_active
        self.pct = percent(self.correct, self.correct + self.wrong)
        self.avg_points_delta = (
            self.points_delta / self.picksets_played if self.picksets_played else 0
        )

    def __str__(self):
        return "{}{}".format(self.user, " ({})".format(self.season) if self.season else "")

    __repr__ = __str__

    @classmethod
    def get_details(cls, league, group, season=None):
        season = season or league.current_season
        users = get_user_model().objects.filter(is_active=True, picker_memberships__group=group)

        def keyfn(rs):
            return (rs.correct, -rs.points_delta, rs.picksets_played)

        stats = [cls(u, league) for u in users]
        by_user = {entry.user: entry for entry in sorted_standings(stats, key=keyfn)}
        stats = [cls(u, league, season) for u in users]
        results = [(e, by_user[e.user]) for e in sorted_standings(stats, key=keyfn)]
        return results
