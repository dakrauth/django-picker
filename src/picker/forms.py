from functools import cache
from django import forms
from django.utils import timezone
from django.utils.module_loading import import_string

from . import models as picker

_picker_widget = None
encoded_game_key = "game_{}".format


def decoded_game_key(value):
    return int(value.replace("game_", ""))


@cache
def get_picker_widget(league):
    widget_path = league.config("TEAM_PICKER_WIDGET")
    if widget_path:
        return import_string(widget_path)

    return forms.RadioSelect


class GameField(forms.ChoiceField):
    def __init__(self, game, manage=False, widget=None, allow_ties=False):
        self.winner = game.winner
        choices = [(str(game.away.id), game.away), (str(game.home.id), game.home)]
        if allow_ties:
            choices.insert(1, (picker.TIE_KEY, ""))

        self.game = game
        self.manage = manage
        self.game_id = game.id
        self.is_game = True
        widget = widget or get_picker_widget(game.gameset.league)
        super(GameField, self).__init__(
            choices=choices,
            label=game.start_time.strftime("%a, %b %d %I:%M %p"),
            required=False,
            help_text=game.tv,
            disabled=not self.manage and (self.game.start_time <= timezone.now()),
            widget=widget,
        )

    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        attrs["winner"] = self.winner
        return attrs


class FieldIter:
    def __init__(self, form):
        self.fields = []
        self.form = form

    def append(self, name):
        self.fields.append(name)

    def __iter__(self):
        for name in self.fields:
            yield self.form[name]


class BasePickForm(forms.Form):
    management = False

    def __init__(self, gameset, *args, **kws):
        self.allow_ties = kws.pop("allow_ties", gameset.league.config("ALLOW_TIES"))
        super(BasePickForm, self).__init__(*args, **kws)
        self.gameset = gameset
        self.game_fields = FieldIter(self)
        games = list(gameset.games.all())
        if games:
            for gm in games:
                key = encoded_game_key(gm.id)
                self.fields[key] = GameField(gm, manage=self.management, allow_ties=self.allow_ties)
                self.game_fields.append(key)

            self.fields["points"] = forms.IntegerField(
                label="{}:".format(games[-1].vs_description), required=False
            )


class ManagementPickForm(BasePickForm):
    management = True

    def __init__(self, gameset, *args, **kws):
        kws.setdefault("initial", {}).update(**self.get_initial_picks(gameset))
        kws["allow_ties"] = True
        super(ManagementPickForm, self).__init__(gameset, *args, **kws)

    def save(self):
        gameset = self.gameset
        data = self.cleaned_data.copy()
        gameset.points = data.pop("points", 0) or 0
        gameset.save()

        for key, winner in data.items():
            if winner:
                pk = decoded_game_key(key)
                game = gameset.games.get(pk=pk)
                game.winner = None if winner == picker.TIE_KEY else int(winner)

        gameset.update_pick_status()

    @staticmethod
    def get_initial_picks(gameset):
        return dict(
            {
                encoded_game_key(game.id): str(game.winner.id)
                for game in gameset.games.played()
                if game.winner
            },
            points=gameset.points,
        )


class UserPickForm(BasePickForm):
    def __init__(self, picker, gameset, *args, **kws):
        initial = self.get_initial_picks(gameset, picker)
        kws.setdefault("initial", {}).update(initial)
        self.picker = picker
        super(UserPickForm, self).__init__(gameset, *args, **kws)

    def save(self):
        data = self.cleaned_data.copy()
        picks = picker.PickSet.objects.for_gameset_picker(self.gameset, self.picker)
        points = data.pop("points", None)
        games = {decoded_game_key(k): v for k, v in data.items() if v}
        picks.update_picks(games=games, points=points)
        return picks

    @staticmethod
    def get_initial_picks(gameset, picker):
        ps = gameset.pick_for_picker(picker)
        initial = (
            dict(
                {
                    encoded_game_key(g_id): str(w_id)
                    for g_id, w_id in ps.gamepicks.picked_winner_ids()
                },
                points=ps.points,
            )
            if ps
            else {}
        )
        return initial


class GameForm(forms.ModelForm):
    class Meta:
        model = picker.Game
        fields = ("start_time", "location")


class PickerForm(forms.ModelForm):
    class Meta:
        model = picker.Picker
        fields = ("name",)

    def __init__(self, instance, *args, **kws):
        kws["instance"] = instance
        self.current_email = instance.user.email.lower()
        kws.setdefault("initial", {})["email"] = self.current_email
        super(PickerForm, self).__init__(*args, **kws)

        for league in picker.League.objects.all():
            field_name = "{}_favorite".format(league.slug)
            current = None
            if instance:
                try:
                    current = picker.PickerFavorite.objects.get(picker=instance, league=league)
                except picker.PickerFavorite.DoesNotExist:
                    pass

            self.fields[field_name] = forms.ModelChoiceField(
                picker.Team.objects.filter(league=league),
                label="{} Favorite".format(league.abbr.upper()),
                empty_label="-- Select --",
                required=False,
                initial=current.team if current else None,
            )

    def save(self, commit=True):
        super(PickerForm, self).save(commit)
        if commit:
            picker.PickerFavorite.objects.filter(picker=self.instance).delete()
            for key in self.cleaned_data:
                if not key.endswith("_favorite"):
                    continue

                slug = key.rsplit("_")[0]
                league = picker.League.objects.get(slug=slug)
                picker.PickerFavorite.objects.create(
                    league=league, picker=self.instance, team=self.cleaned_data[key]
                )
