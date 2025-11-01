import os
from pathlib import Path
from urllib.parse import urlparse

# =====================================================================
# 1. CONFIGURAÇÕES BÁSICAS E DE AMBIENTE
# =====================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Variáveis Críticas ---
# Variável para determinar o ambiente de produção (injetada no Cloud Run)
IS_CLOUD_RUN_PRODUCTION = os.getenv("CLOUD_SQL_INSTANCE_CONNECTION_NAME")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me-in-development")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"

# Adiciona o domínio padrão do Cloud Run (*.run.app) e domínios customizados
ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost,*.run.app").split(",")
    if h.strip()
]

# --- Definição de Aplicação ---
INSTALLED_APPS = [
    # Default Django apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # Third party
    "rest_framework",
    "drf_spectacular",
    "oauth2_provider",

    # NOVO: Necessário para usar Google Cloud Storage
    'storages', 

    # Aplicativos Allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    # Adicione outros provedores aqui (ex: github)

    # Local apps
    "core",
    "api",
]

SITE_ID = 1

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    'allauth.account.middleware.AccountMiddleware',
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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


# =====================================================================
# 2. CONFIGURAÇÃO DE BANCOS DE DADOS E PERSISTÊNCIA
# =====================================================================

# --- MySQL (Cloud SQL) ---
if IS_CLOUD_RUN_PRODUCTION:
    # Perfil de Produção: Conexão via Unix Socket (Recomendado para Cloud Run)
    CLOUD_SQL_CONNECTION_NAME = os.getenv("CLOUD_SQL_INSTANCE_CONNECTION_NAME")

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.getenv("MYSQL_DATABASE"),
            "USER": os.getenv("MYSQL_USER"),
            "PASSWORD": os.getenv("MYSQL_PASSWORD"),
            "HOST": 'localhost', # Ignorado no socket
            "OPTIONS": {
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
                # O Cloud Run monta o socket neste caminho
                "unix_socket": f"/cloudsql/{CLOUD_SQL_CONNECTION_NAME}",
            }
        }
    }
    # Persistência de conexões ajuda a reduzir cold starts
    DATABASES["default"]["CONN_MAX_AGE"] = int(os.getenv("DJANGO_CONN_MAX_AGE", 60))

else:
    # Perfil de Desenvolvimento Local
    DATABASES = {
        "default": {
            "ENGINE": os.getenv("DJANGO_DB_ENGINE", "django.db.backends.mysql"),
            "NAME": os.getenv("MYSQL_DATABASE", os.getenv("DJANGO_DB_NAME", "provision_db")),
            "USER": os.getenv("MYSQL_USER", os.getenv("DJANGO_DB_USER", "provision_user")),
            "PASSWORD": os.getenv("MYSQL_PASSWORD", os.getenv("DJANGO_DB_PASSWORD", "changeme")),
            "HOST": os.getenv("MYSQL_HOST", "127.0.0.1"),
            "PORT": os.getenv("MYSQL_PORT", "3306"),
            "OPTIONS": {
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }


# --- MongoDB (Atlas) ---
MONGODB_URI = os.getenv("MONGODB_URI") 

if MONGODB_URI:
    # Conexão via URI completa (padrão para MongoDB Atlas)
    parsed_uri = urlparse(MONGODB_URI)
    
    MONGODB = {
        "URI": MONGODB_URI,
        "HOST": parsed_uri.hostname,
        "PORT": parsed_uri.port or 27017,
        # Tenta obter o nome do DB da URI ou usa uma variável de ambiente
        "DB_NAME": os.getenv("MONGODB_DB_NAME", parsed_uri.path.strip('/') or "provision_mongo"), 
        "USER": parsed_uri.username,
        "PASSWORD": parsed_uri.password,
    }
else:
    # Fallback para Localhost
    MONGODB = {
        "HOST": os.getenv("MONGODB_HOST", "localhost"),
        "PORT": int(os.getenv("MONGODB_PORT", 27017)),
        "DB_NAME": os.getenv("MONGODB_DB_NAME", "provision_mongo"),
        "USER": os.getenv("MONGODB_USER", ""),
        "PASSWORD": os.getenv("MONGODB_PASSWORD", ""),
    }


# --- Arquivos Estáticos e de Mídia (GCS) ---
if IS_CLOUD_RUN_PRODUCTION and os.getenv("GS_BUCKET_NAME"):
    # Produção: Usar Google Cloud Storage (GCS)
    
    # Define os backends de armazenamento para Django 4.2+
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
        },
        "staticfiles": {
            "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
        },
    }
    
    GS_BUCKET_NAME = os.getenv("GS_BUCKET_NAME")
    
    # URL de acesso ao bucket (garantir que o bucket seja público ou que a autenticação esteja correta)
    STATIC_URL = f"https://storage.googleapis.com/{GS_BUCKET_NAME}/static/"
    MEDIA_URL = f"https://storage.googleapis.com/{GS_BUCKET_NAME}/media/"
    
    STATIC_ROOT = None # Não é mais necessário no sistema de arquivos local
    
else:
    # Desenvolvimento Local: Uso do sistema de arquivos local
    STATIC_URL = "/static/"
    STATIC_ROOT = BASE_DIR / "staticfiles"
    

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# =====================================================================
# 3. AUTENTICAÇÃO, API E SEGURANÇA
# =====================================================================

# --- Autenticação e Allauth ---
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

LOGIN_REDIRECT_URL = os.getenv("LOGIN_REDIRECT_URL", "/")
ACCOUNT_LOGOUT_REDIRECT_URL = os.getenv("ACCOUNT_LOGOUT_REDIRECT_URL", "/")
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = os.getenv("ACCOUNT_EMAIL_VERIFICATION", "mandatory")
LOGIN_URL = '/accounts/login/' 

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- REST Framework e OAuth2 ---
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Provision API",
    "DESCRIPTION": "API de Provisionamento - documentação OpenAPI gerada pelo drf-spectacular.",
    "VERSION": "1.0.0",
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
}

PROVISION_API_KEY = os.getenv("PROVISION_API_KEY", "")


# --- Configurações de Segurança e Outros ---
if not DEBUG and IS_CLOUD_RUN_PRODUCTION:
    # Cloud Run usa HTTPS, forçamos cookies seguros
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # HSTS ativado
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000")) # 1 ano
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Cloud Run/Load Balancer enviam este cabeçalho
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

else:
    # Configurações de segurança para ambiente local (podem ser substituídas por ENV)
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
    CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "0") == "1"
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "0") == "1"
    SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "0") == "1"


# --- Logging e Email ---
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

EMAIL_BACKEND = os.getenv("DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT") or 25)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "0") == "1"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "webmaster@localhost")