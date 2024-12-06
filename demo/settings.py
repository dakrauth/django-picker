import os
from pathlib import Path

from freezegun import freeze_time


PROJECT_DIR = Path(__file__).parent
BASE_DIR = PROJECT_DIR.parent

SECRET_KEY = "@$n=(b+ih211@e02_kup2i26e)o4ovt6ureh@xbkfz!&@b(hh*"
DEBUG = True
ALLOWED_HOSTS = ["*"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_REDIRECT_URL = LOGOUT_REDIRECT_URL = "/"

INSTALLED_APPS = (
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.sites",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django_bootstrap5",
    "django_extensions",
    "picker.apps.PickerConfig",
    "demo",
)

MIDDLEWARE = (
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "demo/templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "demo.wsgi.application"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.getenv("DEMO_DB_NAME", PROJECT_DIR / "demo.sqlite3"),
    }
}

SITE_ID = 1
ROOT_URLCONF = "demo.project"
LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/New_York"
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = "/static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = PROJECT_DIR / "media"

PICKER = {
    "FAKE_DATETIME_NOW": None,
    "NFL": {
        "TEAM_PICKER_WIDGET": "demo.project.TemplateTeamChoice",
    },
    "HQ": {
        "TEAM_PICKER_WIDGET": "demo.project.TemplateTeamChoice",
        "SHOW_TV": False,
    },
    "ENG1": {
        "TEAM_PICKER_WIDGET": "demo.project.TemplateTeamChoice",
        "ALLOW_TIES": True,
        "SHOW_TV": False,
    },
}


freezer = freeze_time("2024-10-01 12:00:01")
freezer.start()
