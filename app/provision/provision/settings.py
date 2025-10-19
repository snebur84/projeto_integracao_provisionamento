"""
Django settings for provision project.

This settings.py is intended to be used for local development and production,
reading configuration from environment variables. It preserves the standard
AUTH_PASSWORD_VALIDATORS and adds configuration for Django REST Framework,
drf-spectacular (OpenAPI) and django-oauth-toolkit (OAuth2 provider).

After editing/adding this file you should:
 - set environment variables (see README)
 - install dependencies (including django-oauth-toolkit and drf-spectacular)
 - run: python manage.py migrate
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Basic secrets / env
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me-in-development")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]

# Application definition
INSTALLED_APPS = [
    # Default Django apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third party
    "rest_framework",
    "drf_spectacular",

    # OAuth2 provider
    "oauth2_provider",

    # Local apps
    "core",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # oauth2_provider has a middleware for scoped token introspection if needed:
    # "oauth2_provider.middleware.OAuth2TokenMiddleware",
]

ROOT_URLCONF = "provision.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "provision.wsgi.application"

# Database configuration (MySQL) - values come from environment (.env)
DATABASES = {
    "default": {
        "ENGINE": os.getenv("DJANGO_DB_ENGINE", "django.db.backends.mysql"),
        "NAME": os.getenv("MYSQL_DATABASE", os.getenv("DJANGO_DB_NAME", "provision_db")),
        "USER": os.getenv("MYSQL_USER", os.getenv("DJANGO_DB_USER", "provision_user")),
        "PASSWORD": os.getenv("MYSQL_PASSWORD", os.getenv("DJANGO_DB_PASSWORD", "changeme")),
        "HOST": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "PORT": os.getenv("MYSQL_PORT", "3306"),
        "OPTIONS": {
            # Use this option if you use MySQL and want to force engine/charset
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            # If using pymysql, no special option required here
        },
    }
}

# Mongo configuration (used by app utilities)
MONGODB = {
    "HOST": os.getenv("MONGODB_HOST", "localhost"),
    "PORT": int(os.getenv("MONGODB_PORT", 27017)),
    "DB_NAME": os.getenv("MONGODB_DB_NAME", "provision_mongo"),
    "USER": os.getenv("MONGODB_USER", ""),
    "PASSWORD": os.getenv("MONGODB_PASSWORD", ""),
}

# Password validation (kept as requested)
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST framework + OpenAPI (drf-spectacular)
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Authentication classes will include OAuth2 (below) and SessionAuthentication
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Provision API",
    "DESCRIPTION": "API de Provisionamento - documentação OpenAPI gerada pelo drf-spectacular.",
    "VERSION": "1.0.0",
    # Declare OAuth2 security scheme (client credentials)
    "COMPONENTS": {
        "securitySchemes": {
            "oauth2": {
                "type": "oauth2",
                "flows": {
                    "clientCredentials": {
                        "tokenUrl": "/o/token/",
                        "scopes": {
                            "read": "Read scope",
                            "write": "Write scope",
                            "provision": "Access device provisioning endpoints",
                            "admin": "Admin-level access",
                        },
                    }
                },
            }
        }
    },
    # By default add oauth2 security to operations; you may restrict in specific views if needed
    "SECURITY": [{"oauth2": ["provision", "read"]}],
}

# ---------------------------------------------------------------------
# OAuth2 (django-oauth-toolkit) integration
# ---------------------------------------------------------------------
# Keep oauth2_provider in INSTALLED_APPS (added above).
# Configure DRF to accept OAuth2 bearer tokens via django-oauth-toolkit and
# keep SessionAuthentication as a fallback for browser sessions/admin.
REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = [
    "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
    "rest_framework.authentication.SessionAuthentication",
]

# Default permission: read-only for anonymous, authenticated required for writes
REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] = [
    "rest_framework.permissions.IsAuthenticatedOrReadOnly",
]

# django-oauth-toolkit settings; tweak lifetimes/scopes using env vars
OAUTH2_PROVIDER = {
    "ACCESS_TOKEN_EXPIRE_SECONDS": int(os.getenv("OAUTH_ACCESS_TOKEN_EXPIRE", 3600)),
    "REFRESH_TOKEN_EXPIRE_SECONDS": int(os.getenv("OAUTH_REFRESH_TOKEN_EXPIRE", 60 * 60 * 24 * 30)),
    "ROTATE_REFRESH_TOKEN": True,
    "SCOPES": {
        "read": "Read scope",
        "write": "Write scope",
        "provision": "Access device provisioning endpoints",
        "admin": "Admin-level access",
    },
    # other optional settings:
    # "OAUTH2_BACKEND_CLASS": "oauth2_provider.oauth2_backends.OAuthLibCore",
}

# Optional: API key used by device endpoint as fallback (kept for backward compatibility)
PROVISION_API_KEY = os.getenv("PROVISION_API_KEY", "")

# Logging (minimal default, adjust as needed)
LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
}

# Email (used by password reset flows)
EMAIL_BACKEND = os.getenv("DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT") or 25)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "0") == "1"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "webmaster@localhost")

# Other useful security settings (can be toggled via env)
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "0") == "1"
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "0") == "1"
SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "0") == "1"

# Allow additional settings via env to remain flexible in different deployments