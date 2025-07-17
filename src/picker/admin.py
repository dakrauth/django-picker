from django import forms
from django.contrib import admin
from . import models as picker


@admin.register(picker.League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ("name", "abbr")


class AliasInline(admin.TabularInline):
    model = picker.Alias


@admin.register(picker.Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "abbr", "nickname", "league", "conference", "division")
    list_filter = ("league",)
    inlines = [AliasInline]


@admin.register(picker.Conference)
class ConferenceAdmin(admin.ModelAdmin):
    list_display = ("name", "abbr", "league")
    list_filter = ("league",)


@admin.register(picker.Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ("name", "conference", "league")
    list_filter = ("conference", "conference__league")

    def league(self, obj):
        return obj.conference.league


class GameSetForm(forms.ModelForm):
    class Meta:
        model = picker.GameSet
        fields = "__all__"

    def __init__(self, *args, **kws):
        super(GameSetForm, self).__init__(*args, **kws)
        if self.instance and self.instance.id:
            self.fields["byes"].queryset = self.instance.league.teams.all()


class InlineGameForm(forms.ModelForm):
    class Meta:
        model = picker.Game
        exclude = ("notes",)


class GameInline(admin.TabularInline):
    model = picker.Game
    form = InlineGameForm
    extra = 0


@admin.register(picker.GameSet)
class GameSetAdmin(admin.ModelAdmin):
    list_display = ("__str__", "league", "points", "opens", "closes")
    list_filter = ("league", "season")
    ordering = ("-season", "sequence")
    filter_horizontal = ["byes"]
    inlines = [GameInline]
    form = GameSetForm


@admin.register(picker.Preference)
class PreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "autopick")


class GamePickInlineForm(forms.ModelForm):
    winner = forms.ModelChoiceField(queryset=picker.Team.objects.none(), required=False)
    model = picker.GamePick
    fields = ("winner",)

    def __init__(self, *args, **kws):
        super(GamePickInlineForm, self).__init__(*args, **kws)
        instance = kws.get("instance", None)
        if instance:
            game = instance.game
            self.fields["winner"].queryset = picker.Team.objects.filter(
                id__in=[game.away.id, game.home.id]
            )


class GamePickInline(admin.TabularInline):
    model = picker.GamePick
    form = GamePickInlineForm
    fields = (
        "game_info",
        "winner",
    )
    readonly_fields = ("game_info",)
    extra = 0

    def game_info(self, obj):
        return "{}".format(obj.game)


@admin.register(picker.PickSet)
class PickSetAdmin(admin.ModelAdmin):
    list_display = ("user", "gameset", "league")
    list_filter = ("user", "gameset")
    # fields = ('points', 'strategy')
    inlines = [GamePickInline]

    def league(self, obj):
        return obj.gameset.league


class PickerMembershipInline(admin.TabularInline):
    model = picker.PickerMembership


@admin.register(picker.PickerGrouping)
class PickerGroupingAdmin(admin.ModelAdmin):
    list_display = ("name", "id", "status", "category")
    filter_horizontal = ["leagues"]
    inlines = [PickerMembershipInline]
