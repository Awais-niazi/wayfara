"""Django settings for Wayfara.

Environment-driven configuration. Set DATABASE_URL to use PostgreSQL
(production and normal dev); falls back to SQLite so a fresh clone runs
with zero setup.
"""

from datetime import timedelta
from pathlib import Path
import os
import sys

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "dev-only-insecure-key-change-in-production"
)

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"

TESTING = "test" in sys.argv

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_celery_beat",
    "accounts",
    "advisor",
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

# Cache — backs DRF throttle counters, so it must be shared across workers in
# production (Redis db 6; broker is db 5, Ash's keyspace untouched). Tests use
# in-process memory: no Redis dependency, and no throttle state bleeding
# between test runs.
if TESTING:
    CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": os.environ.get("CACHE_URL", "redis://localhost:6379/6"),
        }
    }

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
    # Safety-net throttles on everything; the abuse-prone public endpoints
    # (OTP, register, onboarding) carry much tighter scoped rates below.
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        # Per-IP scoped rates
        "register": "10/hour",
        "onboarding": "10/hour",
        "otp_request": "10/hour",
        "otp_verify": "20/hour",  # model also caps 5 attempts per code
        # Per-target-inbox rate: stops many-IP spamming of one mailbox
        "otp_email": "5/hour",
        # Advisor invite-link password set — blunts token brute-forcing
        "advisor_activate": "20/hour",
    },
}

if TESTING:
    # Keep throttling exercised in dedicated tests (via override_settings)
    # without tripping the rest of the suite, which shares one client IP.
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
        scope: "10000/min" for scope in REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    }

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    # Rotated-out refresh tokens are dead immediately; logout blacklists too.
    "BLACKLIST_AFTER_ROTATION": True,
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

# Base URL of the advisor web console; activation links are built off it.
ADVISOR_CONSOLE_URL = os.environ.get("ADVISOR_CONSOLE_URL", "http://localhost:5173/advisor")

# Expo push notifications. No-ops without registered device tokens, so it is
# safe on by default; set PUSH_ENABLED=false to hard-disable delivery.
PUSH_ENABLED = os.environ.get("PUSH_ENABLED", "true").lower() == "true"

# Error tracking — activates only when SENTRY_DSN is set (production).
# Django + Celery errors both report; PII stays out of events by default.
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if SENTRY_DSN and not TESTING:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=os.environ.get("SENTRY_ENVIRONMENT", "production"),
        send_default_pii=False,  # student emails/documents never leave our infra
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        # Sentry Logs: WARNING+ records from Python logging ship as searchable
        # logs alongside the error events they contextualize.
        enable_logs=True,
    )

# Logging — structured console output (12-factor: the host captures stdout).
# Request/security errors always surface; scraping gets its own channel since
# it runs unattended at 2 AM.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "console"},
    },
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
    "loggers": {
        "django.request": {"level": "WARNING"},
        "django.security": {"level": "WARNING"},
        "scraping": {"level": "INFO"},
        "celery": {"level": "INFO"},
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
