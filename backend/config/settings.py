"""Django settings — schema owned by Goose migrations, not Django."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-change-me-in-production")
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "corsheaders",
    "accounts",
    "inventory_api",
    "sync_api",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("INVENTORY_DB_NAME", "db_inventory"),
        "USER": os.environ.get("INVENTORY_DB_USER", "postgres"),
        "PASSWORD": os.environ.get("INVENTORY_DB_PASSWORD", "postgres"),
        "HOST": os.environ.get("INVENTORY_DB_HOST", "localhost"),
        "PORT": os.environ.get("INVENTORY_DB_PORT", "5433"),
    }
}

AUTH_USER_MODEL = "accounts.AppUser"
AUTHENTICATION_BACKENDS = ["accounts.backends.AppUserBackend"]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.CursorPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Inventory API",
    "DESCRIPTION": "Conversational inventory management (DRF + PowerSync upload connector)",
    "VERSION": "0.1.0",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "USER_ID_FIELD": "user_id",
    "USER_ID_CLAIM": "user_id",
}

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
]

# Safari (especially iOS) preflights custom headers on PowerSync requests.
from corsheaders.defaults import default_headers  # noqa: E402

CORS_ALLOW_HEADERS = (
    *default_headers,
    "x-user-agent",
)

# pydantic-ai — set INVENTORY_AGENT_MODEL in .env (see .env.example)
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# OpenRouter keys (sk-or-…) are often pasted into OPENAI_API_KEY by mistake.
if not OPENROUTER_API_KEY and OPENAI_API_KEY.startswith("sk-or-"):
    OPENROUTER_API_KEY = OPENAI_API_KEY
    os.environ["OPENROUTER_API_KEY"] = OPENAI_API_KEY


def _resolve_agent_model() -> str:
    if explicit := os.environ.get("INVENTORY_AGENT_MODEL"):
        return explicit
    if OPENROUTER_API_KEY:
        return "openrouter:openai/gpt-4o"
    if os.environ.get("GOOGLE_API_KEY"):
        return "google:gemini-2.5-flash-lite"
    if os.environ.get("DEEPSEEK_API_KEY"):
        return "deepseek:deepseek-v4-flash"
    return "openai:gpt-4o"


INVENTORY_AGENT_MODEL = _resolve_agent_model()
