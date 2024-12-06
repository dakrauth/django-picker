from django import http
from django.contrib import messages
from django.utils.functional import cached_property
from django.shortcuts import get_object_or_404, get_list_or_404
from django.contrib.auth.mixins import UserPassesTestMixin

from .. import forms
from ..models import Game, GameSetPicks
from .base import PickerViewBase, SimpleFormMixin


__all__ = ["ManagementHome", "ManageSeason", "ManageWeek", "ManageGame"]


class ManagementMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.has_perm("can_update_score")


class ManagementViewBase(ManagementMixin, PickerViewBase):
    def get_context_data(self, **kwargs):
        return super().get_context_data(management=True, **kwargs)


class ManagementHome(ManagementViewBase):
    template_name = "@manage/home.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(gameset=self.league.current_gameset, **kwargs)


class ManageSeason(ManagementViewBase):
    template_name = "@manage/season.html"

    def get_context_data(self, **kwargs):
        gamesets = get_list_or_404(self.league.gamesets, season=self.season)
        return super().get_context_data(gamesets=gamesets, **kwargs)


class ManageWeek(SimpleFormMixin, ManagementViewBase):
    template_name = "@manage/results.html"
    form_class = forms.ManagementPickForm

    @cached_property
    def gameset(self):
        return get_object_or_404(
            GameSetPicks, league=self.league, season=self.season, sequence=self.kwargs["sequence"]
        )

    def get_context_data(self, **kwargs):
        return super().get_context_data(gameset=self.gameset, **kwargs)

    def get_form(self):
        return self.form_class(self.gameset, **self.get_form_kwargs())

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Results saved")
        return http.HttpResponseRedirect(self.request.path)

    def post(self, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data())


class ManageGame(SimpleFormMixin, ManagementViewBase):
    template_name = "@manage/game.html"
    form_class = forms.GameForm
    success_msg = "Game saved"

    @cached_property
    def game(self):
        return get_object_or_404(Game, pk=self.kwargs["game_id"])

    def get_context_data(self, **kwargs):
        return super().get_context_data(instance=self.game, **kwargs)

    def get_form_kwargs(self):
        data = super().get_form_kwargs()
        data["instance"] = self.game
        return data

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)
