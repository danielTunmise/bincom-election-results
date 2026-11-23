"""
Django settings - kept deliberately small.

We do NOT use Django's auth/admin/sessions apps, so Django never needs to
create its own tables: the only tables in db.sqlite3 are the election tables
imported from the MySQL dump (and our models are mapped onto them).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Secrets / switches come from environment variables so nothing sensitive is
# committed. The fallback key is for local development only.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,.pythonanywhere.com"
).split(",")

INSTALLED_APPS = [
    "django.contrib.messages",     # the green "success" banner after saving
    "django.contrib.staticfiles",  # serves our CSS / JS
    "elections",                   # our app
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",        # protects the POST form
    "django.contrib.messages.middleware.MessageMiddleware",
]

# Store flash messages in a cookie, so we don't need the sessions app/table.
MESSAGE_STORAGE = "django.contrib.messages.storage.cookie.CookieStorage"

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# SQLite file created by import_mysql_dump.py
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"   # `collectstatic` copies files here (for hosting)

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
TIME_ZONE = "Africa/Lagos"
USE_TZ = False   # the dump stores naive datetimes, so keep them naive
