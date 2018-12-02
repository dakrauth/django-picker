from datetime import timedelta

from dateutil.parser import parse as parse_dt
from .exceptions import PickerConfigurationError


def valid_schema(data, expected_schema):
    schema = data.get('schema')
    if not schema:
        raise PickerConfigurationError('Missing schema type for {}'.format(expected_schema))

    if schema == 'complete':
        data = data[expected_schema]

    if data.get('schema') != expected_schema:
        raise PickerConfigurationError('Missing schema type for {}'.format(expected_schema))

    return data


def import_season(cls, data):
    data = valid_schema(data, 'season')
    gs = None
    league = cls.objects.get(abbr=data['league'])
    season = data['season']
    teams = league.team_dict
    gamesets = []
    for sequence, item in enumerate(data['gamesets'], 1):
        opens = item.get('opens')
        if opens:
            opens = parse_dt(opens)
        else:
            dt = parse_dt(item['games'][0]['start'])
            opens = dt - timedelta(days=dt.weekday() - 1)
            opens = opens.replace(hour=12, minute=0)

        closes = item.get('closes')
        if closes:
            closes = parse_dt(closes)
        else:
            closes = opens + timedelta(
                **league.config('GAMESET_DURATION', {'days': 7, 'seconds': -1})
            )

        gs, is_new = league.gamesets.get_or_create(
            season=season,
            sequence=item.get('sequence', sequence),
            defaults={'opens': opens, 'closes': closes}
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
    data = valid_schema(data, 'league')
    name = data['name']
    default_abbr = ''.join(c[0] for c in name.upper().split())
    abbr = data.get('abbr', default_abbr).upper()
    league, created_league = cls.objects.get_or_create(
        name=name,
        abbr=abbr,
        slug=abbr.lower(),
        defaults={
            'is_pickable': data.get('is_pickable', False),
            'current_season': data.get('current_season')
        },
    )
    confs = {}
    divs = {}
    teams = {}
    teams_results = []
    for tm in data['teams']:
        conf = div = None
        if 'sub' in tm and len(tm['sub']):
            conf_name = tm['sub'][0]
            if conf_name not in confs:
                conf, conf_created = league.conferences.get_or_create(
                    name=conf_name,
                    league=league,
                    abbr=conf_name.lower()
                )
                confs[conf_name] = conf

            if len(tm['sub']) > 1:
                div_name = tm['sub'][1]
                if (div_name, conf_name) not in divs:
                    div, div_created = confs[conf_name].divisions.get_or_create(name=div_name)
                    divs[(div_name, conf_name)] = div

        team, created = league.teams.get_or_create(
            name=tm['name'],
            abbr=tm['abbr'],
            defaults={
                'nickname': tm.get('nickname', ''),
                'colors': tm.get('colors', ''),
                'conference': conf,
                'division': div,
                'logo': tm.get('logo', ''),
           }
        )
        teams[tm['abbr']] = team
        teams_results.append([team, created])

    for name, key in data.get('aliases', {}).items():
        teams[key].aliases.get_or_create(name=name)

    return [[league, created_league], teams_results]
