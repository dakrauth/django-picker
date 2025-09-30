from django.template import Library

from ..models import PickerFavorite
from ..utils import get_templates

register = Library()


@register.simple_tag
def picker_result(pick, actual_results):
    try:
        res = actual_results[pick[0]]
        return "correct" if res["winner"] == pick[1] else "incorrect"
    except KeyError:
        return "error"


@register.inclusion_tag(get_templates("@season_nav.html"), takes_context=True)
def season_nav(context, gameset, relative_to):
    picker = context["picker"]
    league = context["league"]
    prev = following = None
    if gameset:
        prev = gameset.previous_gameset
        following = gameset.next_gameset

    return {
        "gameset": gameset,
        "relative_to": relative_to,
        "picker": picker,
        "group": context.get("group"),
        "league": league,
        "previous": prev,
        "following": following,
        "is_manager": picker.is_manager,
        "season_gamesets": league.season_gamesets(gameset.season if gameset else None),
    }


@register.inclusion_tag(get_templates("@season_nav_all.html"), takes_context=True)
def all_seasons_nav(context, current, league, relative_to):
    picker = context["picker"]
    return {
        "label": "All seasons",
        "group": context.get("group"),
        "current": int(current) if current else None,
        "relative_to": relative_to,
        "picker": picker,
        "is_manager": picker.is_manager,
        "league": league,
    }


@register.simple_tag(takes_context=True)
def favorite_team(context, picker, league=None):
    league = league or context["league"]
    try:
        return PickerFavorite.objects.get(picker=picker, league=league).team
    except PickerFavorite.DoesNotExist:
        pass
