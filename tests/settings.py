from pathlib import Path

DEMO_PROJECT = Path(__file__).parents[1] / "demo"

ALLOWED_HOSTS = ["*"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3"}}
DEBUG = False
LANGUAGE_CODE = "en-us"
MEDIA_ROOT = DEMO_PROJECT / "media"
MEDIA_URL = "/media/"
ROOT_URLCONF = "tests.urls"
SECRET_KEY = "secret-test"
SITE_ID = 1
STATIC_ROOT = DEMO_PROJECT / "static"
STATIC_URL = "/static/"
TIME_ZONE = "America/New_York"
USE_I18N = True
USE_TZ = True


INSTALLED_APPS = (
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.sites",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "picker.apps.PickerConfig",
    "django_bootstrap5",
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
        "DIRS": [DEMO_PROJECT / "templates"],
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

PICKER = {
    "NFL": {"TEAM_PICKER_WIDGET": "django.forms.RadioSelect"},
    "HQ": {"TEAM_PICKER_WIDGET": "django.forms.RadioSelect"},
}
