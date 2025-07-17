from django.utils.functional import cached_property
from django.shortcuts import get_object_or_404, get_list_or_404

from .. import forms
from ..stats import RosterStats
from .base import SimplePickerViewBase, PickerViewBase, SimpleFormMixin
from ..models import Preference, PickerGrouping, GameSetPicks


class Home(SimplePickerViewBase):
    template_name = "@home.html"


class GroupMembershipRedirect(PickerViewBase):
    redirect_view_name = None  # "picker-roster"
    template_name = "@group_select.html"

    def get(self, request, *args, **kwargs):
        memberships = self.memberships
        count = len(memberships)
        if count == 1:
            return self.redirect(self.redirect_view_name, self.league.slug, memberships[0].group.id)
        elif count > 1:
            return self.render_to_response(self.get_context_data())

        return self.render_to_response(
            {
                "league_base": "picker/base.html",
                "heading": "Membership group unavailable",
                "description": "Please check back later",
            },
            template_override="@unavailable.html",
        )


class RosterMixin:
    @cached_property
    def group(self):
        return get_object_or_404(PickerGrouping, pk=self.kwargs["group_id"])

    def get_context_data(self, **kwargs):
        return super().get_context_data(group=self.group, **kwargs)


class Roster(RosterMixin, PickerViewBase):
    template_name = "@roster/season.html"

    @property
    def season(self):
        if len(self.args) == 2:
            return int(self.args[1])

        return super().season

    def get_context_data(self, **kwargs):
        roster = RosterStats.get_details(self.league, self.group, self.season)
        return super().get_context_data(
            roster=roster,
            other_groups=PickerGrouping.objects.filter(members__user=self.request.user),
            **kwargs,
        )


class RosterProfile(RosterMixin, PickerViewBase):
    template_name = "@roster/picker.html"

    def get_context_data(self, **kwargs):
        league = self.league
        username = self.kwargs["username"]
        pref = get_object_or_404(Preference, user__username=username)
        seasons = list(league.available_seasons) + [None]
        return super().get_context_data(
            profile=pref, stats=[RosterStats(pref.user, league, s) for s in seasons], **kwargs
        )


#  Results


class ResultsBase(RosterMixin, PickerViewBase):
    pass


class Results(ResultsBase):
    template_name = "@results/results.html"

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        league = self.league
        gameset = GameSetPicks.objects.current_gameset(league=league)
        if gameset:
            context["gameset"] = gameset
        else:
            self.template_name = "@unavailable.html"
            context["heading"] = "Results currently unavailable"

        return self.render_to_response(context)


class ResultsBySeason(ResultsBase):
    template_name = "@results/season.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            gamesets=GameSetPicks.objects.filter(league=self.league, season=self.season), **kwargs
        )


class ResultsByWeek(ResultsBase):
    template_name = "@results/results.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            gameset=get_object_or_404(
                GameSetPicks,
                league=self.league,
                season=self.season,
                sequence=self.kwargs["sequence"],
            ),
            **kwargs,
        )


#  Picks


class PicksBySeason(PickerViewBase):
    template_name = "@picks/season.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            gamesets=[
                (gs, gs.pick_for_user(self.request.user))
                for gs in get_list_or_404(GameSetPicks, league=self.league, season=self.season)
            ],
            **kwargs,
        )


class Picks(PickerViewBase):
    template_name = "@unavailable.html"

    def get(self, request, *args, **kwargs):
        league = self.league
        gameset = GameSetPicks.objects.current_gameset(league=league)
        if gameset:
            return self.redirect(
                "picker-picks-sequence", league.slug, gameset.season, gameset.sequence
            )

        return self.render_to_response(
            self.get_context_data(heading="Picks currently unavailable", **kwargs)
        )


class PicksByGameset(SimpleFormMixin, PickerViewBase):
    success_msg = "Your picks have been saved"
    form_class = forms.UserPickForm
    template_name = "@picks/make.html"

    @cached_property
    def gameset(self):
        return get_object_or_404(
            GameSetPicks, league=self.league, season=self.season, sequence=self.kwargs["sequence"]
        )

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(user=self.request.user, gameset=self.gameset)
        return kwargs

    def get_context_data(self, **kwargs):
        return super().get_context_data(gameset=self.gameset, **kwargs)

    def show_picks(self, gameset, **kwargs):
        return self.render_to_response(
            self.get_context_data(picks=gameset.pick_for_user(self.request.user), **kwargs),
            template_override="@picks/show.html",
        )

    def post(self, request, *args, **kwargs):
        gameset = self.gameset
        if not gameset.is_open:
            self.show_picks(gameset, **kwargs)

        return super().post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        gameset = self.gameset
        if not gameset.is_open:
            return self.show_picks(gameset, **kwargs)

        return self.render_to_response(self.get_context_data(**kwargs))
