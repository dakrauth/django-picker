from django.template import Library

from ..models import PickerFavorite
from ..utils import get_templates

register = Library()


@register.simple_tag
def user_result(user_pick, actual_results):
    try:
        res = actual_results[user_pick[0]]
        if res["winner"]:
            return "correct" if res["winner"] == user_pick[1] else "incorrect"

        return "unknown"
    except KeyError:
        return "error"


@register.inclusion_tag(get_templates("@season_nav.html"), takes_context=True)
def season_nav(context, gameset, relative_to):
    user = context["user"]
    league = context["league"]
    prev = following = None
    if gameset:
        prev = gameset.previous_gameset
        following = gameset.next_gameset

    return {
        "gameset": gameset,
        "relative_to": relative_to,
        "user": user,
        "group": context.get("group"),
        "league": league,
        "previous": prev,
        "following": following,
        "is_manager": user.is_superuser or user.is_staff,
        "season_gamesets": league.season_gamesets(gameset.season if gameset else None),
    }


@register.inclusion_tag(get_templates("@season_nav_all.html"), takes_context=True)
def all_seasons_nav(context, current, league, relative_to):
    user = context["user"]
    return {
        "label": "All seasons",
        "group": context.get("group"),
        "current": int(current) if current else None,
        "relative_to": relative_to,
        "user": user,
        "is_manager": user.is_superuser or user.is_staff,
        "league": league,
    }


@register.simple_tag(takes_context=True)
def favorite_team(context, user, league=None):
    league = league or context["league"]
    try:
        return PickerFavorite.objects.get(user=user, league=league).team
    except PickerFavorite.DoesNotExist:
        pass
