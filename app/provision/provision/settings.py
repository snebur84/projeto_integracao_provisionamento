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
    # NOVO: Requisito do allauth
    "django.contrib.sites", 

  # Third party
  "rest_framework",
  "drf_spectacular",

  # OAuth2 provider (Servidor de Autorização - para proteger a API)
  "oauth2_provider",

  # Aplicativos Allauth (Cliente OAuth - para Login Social)
  'allauth',
  'allauth.account',
  'allauth.socialaccount',
  
  # Client OAuth providers
  'allauth.socialaccount.providers.google',
    # Adicione outros provedores aqui (ex: github)

  # Local apps
  "core",
  "api",
]

# NOVO: Necessário para django.contrib.sites (e allauth)
SITE_ID = 1

MIDDLEWARE = [
  "django.middleware.security.SecurityMiddleware",
  "django.contrib.sessions.middleware.SessionMiddleware",
  "django.middleware.common.CommonMiddleware",
  "django.middleware.csrf.CsrfViewMiddleware",
  "django.contrib.auth.middleware.AuthenticationMiddleware",
    # NOVO: Middleware do allauth para processar autenticação social
    'allauth.account.middleware.AccountMiddleware', 
  "django.contrib.messages.middleware.MessageMiddleware",
  "django.middleware.clickjacking.XFrameOptionsMiddleware",
  # Se for usar introspecção de token (geralmente não necessário para DRF/OAuth2Authentication)
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
                # IMPORTANTE: Requisito do allauth
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

# ---------------------------------------------------------------------
# AUTENTICAÇÃO E ALLAUTH (CLIENTE OAUTH)
# ---------------------------------------------------------------------

AUTHENTICATION_BACKENDS = [
  # MODO 1: Django-style authentication (username/password)
  'django.contrib.auth.backends.ModelBackend',
  
  # MODO 2: OAuth2 authentication via django-allauth (Login Social)
  'allauth.account.auth_backends.AuthenticationBackend',
]

# Configurações do ciclo de vida da conta
LOGIN_REDIRECT_URL = os.getenv("LOGIN_REDIRECT_URL", "/")  
ACCOUNT_LOGOUT_REDIRECT_URL = os.getenv("ACCOUNT_LOGOUT_REDIRECT_URL", "/")
ACCOUNT_AUTHENTICATION_METHOD = 'email'  # Usar e-mail como método de login
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = os.getenv("ACCOUNT_EMAIL_VERIFICATION", "mandatory") # Recomendado 'mandatory'
LOGIN_URL = '/accounts/login/' 

# Configuração dos Provedores OAuth (Login Social)
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        # 'APP' será preenchido via Django Admin -> Social Applications.
        # Estas configurações garantem o fluxo correto do provedor Google.
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        # Caso queira forçar a configuração via código/env, use:
        # 'APP': {
        #     'client_id': os.getenv('SOCIAL_AUTH_GOOGLE_KEY'),
        #     'secret': os.getenv('SOCIAL_AUTH_GOOGLE_SECRET'),
        # }
    },
}

# Password validation (kept as requested)
AUTH_PASSWORD_VALIDATORS = [
  {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
  {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
  {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
  {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "pt-br"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "America/Sao_Paulo")
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------
# REST FRAMEWORK E OAUTH2 PROVIDER (SERVIDOR OAUTH)
# ---------------------------------------------------------------------
# Configuração para que a API aceite tokens OAuth (Bearer) e Session Auth

REST_FRAMEWORK = {
  "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    
    # NOVO/AJUSTADO: Adiciona a autenticação OAuth2 para a API
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
        "rest_framework.authentication.SessionAuthentication", # Mantido para Admin/Browser
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
}

SPECTACULAR_SETTINGS = {
  "TITLE": "Provision API",
  "DESCRIPTION": "API de Provisionamento - documentação OpenAPI gerada pelo drf-spectacular.",
  "VERSION": "1.0.0",
  # ... (restante das configurações do SPECTACULAR_SETTINGS mantidas)
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
  "SECURITY": [{"oauth2": ["provision", "read"]}],
}

# django-oauth-toolkit settings (Authorization Server)
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
    # Tipicamente, o Servidor de Autorização não precisa da lógica do Allauth
    # "ALLOWED_GRANT_TYPES": ["authorization-code", "implicit", "password", "client-credentials"],
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

# Email (used by password reset flows E pela verificação de email do Allauth)
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

# FIM DO ARQUIVO