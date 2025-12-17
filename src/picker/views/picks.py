from django.utils.functional import cached_property
from django.shortcuts import get_object_or_404, get_list_or_404
from .. import forms
from .base import SimplePickerViewBase, PickerViewBase, SimpleFormMixin
from ..models import Picker, PickerGrouping, GameSetPicks


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

    def get_context_data(self, **kwargs):
        roster = Picker.stats.group_stats(self.group, self.league, self.season)
        return super().get_context_data(
            roster=roster,
            other_groups=PickerGrouping.objects.filter(members__picker__user=self.request.user),
            **kwargs,
        )


class RosterProfile(RosterMixin, PickerViewBase):
    template_name = "@roster/picker.html"

    def get_context_data(self, **kwargs):
        league = self.league
        other = get_object_or_404(Picker, name=self.kwargs["pickername"])
        return super().get_context_data(
            other=other, stats=Picker.stats.for_picker(other, league), **kwargs
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
            context["results"] = gameset.results(context["group"])
        else:
            self.template_name = "@unavailable.html"
            context["heading"] = "Results currently unavailable"

        return self.render_to_response(context)


class ResultsBySeason(ResultsBase):
    template_name = "@results/season.html"

    def get_context_data(self, **kwargs):
        gamesets = [
            (gs, gs.winners(self.group))
            for gs in GameSetPicks.objects.filter(league=self.league, season=self.season)
        ]

        return super().get_context_data(gamesets=gamesets, **kwargs)


class ResultsByWeek(ResultsBase):
    template_name = "@results/results.html"

    def get_context_data(self, **kwargs):
        gameset = get_object_or_404(
            GameSetPicks,
            league=self.league,
            season=self.season,
            sequence=self.kwargs["sequence"],
        )
        results = gameset.results(self.group)
        return super().get_context_data(gameset=gameset, results=results, **kwargs)


#  Picks


class PicksBySeason(PickerViewBase):
    template_name = "@picks/season.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            gamesets=[
                (gs, gs.pick_for_picker(self.picker))
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
        kwargs.update(picker=self.picker, gameset=self.gameset)
        return kwargs

    def get_context_data(self, **kwargs):
        return super().get_context_data(gameset=self.gameset, **kwargs)

    def show_picks(self, gameset, **kwargs):
        return self.render_to_response(
            self.get_context_data(picks=gameset.pick_for_picker(self.picker), **kwargs),
            template_override="@picks/show.html",
        )

    def post(self, request, *args, **kwargs):
        gameset = self.gameset
        if not gameset.is_open:
            return self.show_picks(gameset, **kwargs)

        return super().post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        gameset = self.gameset
        if not gameset.is_open:
            return self.show_picks(gameset, **kwargs)

        return self.render_to_response(self.get_context_data(**kwargs))
