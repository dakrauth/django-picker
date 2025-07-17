from django.conf import settings


DEFAULT_PICKER_SETTINGS = {
    "DEFAULT_LEAGUE": "NFL",
    "EMAIL_HANDLER": "django.core.mail.send_mail",
    "FAKE_DATETIME_NOW": False,
    "LOGOS_UPLOAD_DIR": "picker/logos",
    "GRAVATAR_KINDS": ["identicon", "monsterid", "wavatar", "retro", "robohash"],
    "AUTO_CREATE_PREFERENCES": True,
    "PARTICIPATION_HOOKS": [],
    "TEAM_PICKER_WIDGET": None,
    "_BASE": {
        "CURRENT_SEASON": None,
        "FORCE_AUTOPICK": True,
        "PARTICIPATION_HOOKS": [],
        "TEAM_PICKER_WIDGET": None,
        "FAKE_DATETIME_NOW": False,
        "ALLOW_TIES": False,
        "SHOW_TV": True,
        "GAMESET_DURATION": {"days": 7, "seconds": -1},
    },
}

picker_settings = {**DEFAULT_PICKER_SETTINGS, **getattr(settings, "PICKER", {})}
get_setting = picker_settings.get
