"""Django settings for Wayfara.

Environment-driven configuration. Set DATABASE_URL to use PostgreSQL
(production and normal dev); falls back to SQLite so a fresh clone runs
with zero setup.
"""

from datetime import timedelta
from pathlib import Path
import os

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "dev-only-insecure-key-change-in-production"
)

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "django_celery_beat",
    "accounts",
    "students",
    "universities",
    "applications",
    "chat",
    "scraping",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "wayfara.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "wayfara.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
}

CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:8081,http://localhost:19006"
).split(",")

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"  # local dev only; S3/R2 replaces this in production

# Background tasks — Celery + Redis. Tasks are thin invokers; business logic
# stays in service functions. Redis db index 5 keeps Wayfara out of any other
# local Redis user's keyspace (Ash runs on this machine too).
# CELERY_TASK_ALWAYS_EAGER=true (dev/test default) runs tasks inline with no
# worker; production sets it to false and runs `celery -A wayfara worker`.
CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/5")
CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://localhost:6379/5")
CELERY_TASK_ALWAYS_EAGER = (
    os.environ.get("CELERY_TASK_ALWAYS_EAGER", "true").lower() == "true"
)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_TIME_LIMIT = 60
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Scheduled tasks (Celery Beat). DB-backed schedule so it survives ephemeral
# hosts and is editable in admin. Scraper timezone = Helsinki: it runs at 2 AM
# local to the Finnish sites it scrapes (off-peak, polite). Production runs
# `celery -A wayfara beat --scheduler django_celery_beat.schedulers:DatabaseScheduler`.
CELERY_TIMEZONE = os.environ.get("CELERY_TIMEZONE", "Europe/Helsinki")
CELERY_ENABLE_UTC = True
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Wayfara <hello@wayfara.app>")

# Where critical-change review alerts are emailed.
SCRAPER_ALERT_EMAIL = os.environ.get("SCRAPER_ALERT_EMAIL", DEFAULT_FROM_EMAIL)

OTP_LIFETIME_MINUTES = 10
OTP_MAX_ATTEMPTS = 5

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
