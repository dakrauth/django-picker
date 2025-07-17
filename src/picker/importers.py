import warnings
from datetime import timedelta

from dateutil.parser import parse as parse_dt
from .exceptions import PickerConfigurationError


def valid_schema(data, expected_schema):
    schema = data.get("schema")
    if not schema:
        raise PickerConfigurationError("Missing schema type for {}".format(expected_schema))

    if schema == "complete":
        data = data[expected_schema]

    if data.get("schema") != expected_schema:
        raise PickerConfigurationError("Missing schema type for {}".format(expected_schema))

    return data


def import_season(cls, data):
    data = valid_schema(data, "season")
    gs = None
    league = cls.objects.get(abbr=data["league"])
    season = data["season"]
    teams = league.team_dict
    gamesets = []
    for sequence, item in enumerate(data["gamesets"], 1):
        opens = item.get("opens")
        if opens:
            opens = parse_dt(opens)
        else:
            dt = parse_dt(item["games"][0]["start"])
            opens = dt - timedelta(days=dt.weekday() - 1)
            opens = opens.replace(hour=12, minute=0)

        closes = item.get("closes")
        if closes:
            closes = parse_dt(closes)
        else:
            closes = opens + timedelta(
                **league.config("GAMESET_DURATION", {"days": 7, "seconds": -1})
            )

        gs, is_new = league.gamesets.get_or_create(
            season=season,
            sequence=item.get("sequence", sequence),
            defaults={"opens": opens, "closes": closes},
        )
        gamesets.append([gs, is_new])
        if not is_new:
            if gs.opens != opens or gs.closes != closes:
                gs.opens = opens
                gs.closes = closes
                gs.save()

        games = gs.import_games(item, teams)
        gamesets[-1].append(games)

    return gamesets


def import_league(cls, data):
    data = valid_schema(data, "league")
    name = data["name"]
    default_abbr = "".join(c[0] for c in name.upper().split())
    abbr = data.get("abbr", default_abbr).upper()
    league, created_league = cls.objects.get_or_create(
        name=name,
        abbr=abbr,
        slug=abbr.lower(),
        defaults={"current_season": data.get("current_season")},
    )
    confs = {}
    divs = {}
    teams = {}
    teams_results = []
    for tm in data["teams"]:
        conf = div = None
        if "sub" in tm and len(tm["sub"]):
            conf_abbr = conf_name = tm["sub"][0]
            if not isinstance(conf_name, str):
                conf_name, conf_abbr = conf_name

            conf_abbr = "-".join(conf_abbr.lower().split())

            if conf_name in confs:
                conf = confs[conf_name]
            else:
                print(f"Creating {conf_name} {conf_abbr}")
                conf, conf_created = league.conferences.get_or_create(
                    name=conf_name, league=league, abbr=conf_abbr
                )
                confs[conf_name] = conf

            if len(tm["sub"]) > 1:
                div_name = tm["sub"][1]
                if (div_name, conf_name) in divs:
                    div = divs[(div_name, conf_name)]
                else:
                    div, div_created = confs[conf_name].divisions.get_or_create(name=div_name)
                    divs[(div_name, conf_name)] = div

        colors = ",".join(tm.get("colors", []))
        team, created = league.teams.get_or_create(
            name=tm["name"],
            abbr=tm["abbr"],
            defaults={
                "nickname": tm.get("nickname", ""),
                "colors": colors,
                "conference": conf,
                "division": div,
                "logo": tm.get("logo", ""),
                "location": tm.get("location", ""),
            },
        )
        for alias in tm.get("aliases", []):
            team.aliases.get_or_create(name=alias)

        teams[tm["abbr"]] = team
        teams_results.append([team, created])

    if "aliases" in data:
        warnings.warn(
            "aliases should be set on the team",
            DeprecationWarning,
            stacklevel=2,
        )
        for name, key in data.get("aliases", {}).items():
            teams[key].aliases.get_or_create(name=name)

    return [[league, created_league], teams_results]
