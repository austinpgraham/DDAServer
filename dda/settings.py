import os
import dj_database_url
from dda.env import Env


# TODO: Allowed hosts?


SECRET_KEY = os.environ["DJANGO_SECRET"]
DEBUG = os.environ.get("DEBUG", None) == "True"
ROOT_URLCONF = "dda.urls"

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)


ENVIRONMENT = Env.get_env()


def get_log_level() -> str:
    if ENVIRONMENT == Env.LOCAL or DEBUG:
        return "DEBUG"
    return "INFO"


SESSION_LENGTH_MINUTES = int(os.environ.get("SESSION_LENGTH_MINUTES", 15))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "basic": {
            "format": "[{asctime}] level={levelname} tid={tid} user_id={user_id} message={message}",
            "style": "{",
        }
    },
    "handlers": {
        "console": {
            "level": get_log_level(),
            "class": "logging.StreamHandler",
            "formatter": "basic",
        }
    },
    "loggers": {
        "dda": {
            "handlers": ["console"],
            "level": get_log_level(),
            "propagate": True,
        }
    },
}


# This order is specific
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "dda.v1.routes.middleware.transaction.transaction_middleware",
    "dda.v1.routes.middleware.authentication.authentication_middleware",
]


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": ["django.template.context_processors.debug"],
        },
    },
]


DATABASES = {
    "default": dj_database_url.config(conn_max_age=600, conn_health_checks=True)
}


INSTALLED_APPS = ["django.contrib.contenttypes", "dda.v1"]
