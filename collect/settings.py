"""
Django settings for collect project.

Generated by 'django-admin startproject' using Django 5.1.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path

from decouple import config
from dj_database_url import parse as db_url
from django.utils.translation import gettext_lazy as _


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

SECRET_KEY = config("DJANGO_SECRET_KEY", default="not-secret")

DEBUG = config("DJANGO_DEBUG", default=False, cast=bool)

ALLOWED_HOSTS: list[str] = config(
    "DJANGO_ALLOWED_HOSTS",
    default="localhost",
    cast=lambda v: [s.strip() for s in v.split(",")],
)

SECURE_HSTS_SECONDS = config("DJANGO_SECURE_HSTS_SECONDS", default=0, cast=int)
SECURE_SSL_REDIRECT = False if DEBUG else True
SESSION_COOKIE_SECURE = False if DEBUG else True
CSRF_COOKIE_SECURE = False if DEBUG else True

# Application definition

INSTALLED_APPS = [
    "collectable.apps.CollectableConfig",
    "accounts",
    # 3rd party
    "simple_history",
    "taggit",
    "imagekit",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
if DEBUG:
    INSTALLED_APPS += [
        "debug_toolbar",
    ]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]
if DEBUG:
    MIDDLEWARE += [
        "debug_toolbar.middleware.DebugToolbarMiddleware",
    ]

ROOT_URLCONF = "collect.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "collect.context_processors.constants",
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "collect.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    "default": config(
        "DJANGO_DATABASE_URL",
        default="sqlite:///" + str(BASE_DIR / "db.sqlite3"),
        cast=db_url,
    )
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

LANGUAGES = (
    ("en", _("English")),
    ("fr", _("French")),
)

LOCALE_PATHS = [
    BASE_DIR / "locale/",
]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = config("DJANGO_STATIC_ROOT", default=None)

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TAGGIT_CASE_INSENSITIVE = True

MEDIA_URL = "/media/"
MEDIA_ROOT = config("DJANGO_MEDIA_ROOT", default=BASE_DIR / "uploads")

ADMIN_ENABLED = config("DJANGO_ADMIN_ENABLED", default=DEBUG, cast=bool)

COLLECTABLE_THUMBNAIL_SIZE = config(
    "COLLECT_COLLECTABLE_THUMBNAIL_SIZE", default=320, cast=int
)
COLLECTABLE_THUMBNAIL_QUALITY = config(
    "COLLECT_COLLECTABLE_THUMBNAIL_QUALITY", default=80, cast=int
)
COLLECTABLE_PHOTO_MAX_SIZE = config(
    "COLLECT_COLLECTABLE_PHOTO_MAX_SIZE", default=640, cast=int
)

LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

SIGNUP_SECRETS_WORDS: list[str] = config(
    "COLLECT_SIGNUP_SECRETS_WORDS", cast=lambda v: [s.strip() for s in v.split(",")]
)

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

INTERNAL_IPS: list[str] = config(
    "DJANGO_INTERNAL_IPS", cast=lambda v: [s.strip() for s in v.split(",")]
)
SECURE_HSTS_INCLUDE_SUBDOMAINS: bool = config(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False, cast=bool
)
SECURE_HSTS_PRELOAD: bool = config(
    "DJANGO_SECURE_HSTS_PRELOAD", default=False, cast=bool
)
SECURE_SSL_REDIRECT: bool = config(
    "DJANGO_SECURE_SSL_REDIRECT", default=False, cast=bool
)
SESSION_COOKIE_SECURE: bool = config(
    "DJANGO_SESSION_COOKIE_SECURE", default=False, cast=bool
)
CSRF_COOKIE_SECURE: bool = config(
    "DJANGO_CSRF_COOKIE_SECURE", default=False, cast=bool
)
