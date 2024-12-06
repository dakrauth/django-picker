from django.shortcuts import get_object_or_404

from .base import SimplePickerViewBase
from ..models import Game


class Team(SimplePickerViewBase):
    template_name = "@teams/detail.html"

    def get_context_data(self, **kwargs):
        team_abbr = kwargs.pop("team", None) or self.kwargs.get("team")
        team = get_object_or_404(self.league.teams, abbr=team_abbr)
        return super().get_context_data(team=team, **kwargs)


class Teams(SimplePickerViewBase):
    template_name = "@teams/listing.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            teams=self.league.teams.select_related("conference", "division"), **kwargs
        )


class Schedule(SimplePickerViewBase):
    template_name = "@schedule/season.html"

    def get_context_data(self, **kwargs):
        season = self.season or self.league.latest_season
        gamesets = []
        current = None
        previous = None
        for game in (
            Game.objects.filter(gameset__season=season, gameset__league=self.league)
            .select_related(
                "home",
                "away",
                "gameset",
            )
            .order_by("gameset__sequence", "start_time")
        ):
            if game.gameset.sequence != previous:
                current = (game.gameset, [game])
                gamesets.append(current)
                previous = game.gameset.sequence
            else:
                current[1].append(game)

        return super().get_context_data(gamesets=gamesets, **kwargs)
