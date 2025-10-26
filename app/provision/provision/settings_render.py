# Proposto: settings específico para deploy no Render
# Importa as configurações base do settings.py e sobrescreve DBs e Mongo
# Ajuste: o projeto já tem app/provision/provision/settings.py — aqui reaproveitamos a maior parte
import os
from pathlib import Path

# importa tudo do settings padrão (mantém INSTALLED_APPS, MIDDLEWARE, etc)
try:
    from .settings import *  # noqa: F401,F403
except Exception:
    # fallback caso import falhe (garante que arquivo funcione em isolamento)
    BASE_DIR = Path(__file__).resolve().parent.parent
    SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me-in-development")
    DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"
    ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",") if h.strip()]

# Secret & debug override (mantém compatibilidade)
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", globals().get("SECRET_KEY", "change-me-in-development"))
DEBUG = os.environ.get("DJANGO_DEBUG", str(int(globals().get("DEBUG", False)))).lower() in ("1", "true", "yes")
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", ",".join(globals().get("ALLOWED_HOSTS", ["*"]))).split(",") if h.strip()]

# --------------------------
# Database configuration
# - Prefer DATABASE_URL (Render Postgres padrão)
# - Fallback para variáveis POSTGRES_* (útil caso o Terraform/Render injete valores separados)
# --------------------------
# Requer dj-database-url no requirements.txt
import dj_database_url

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600, engine="django.db.backends.postgresql")
    }
else:
    # fallback para POSTGRES_* env vars (compatível com TF inputs)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DATABASE", os.environ.get("MYSQL_DATABASE", "provision_db")),
            "USER": os.environ.get("POSTGRES_USER", os.environ.get("MYSQL_USER", "provision_user")),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", os.environ.get("MYSQL_PASSWORD", "changeme")),
            "HOST": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": int(os.environ.get("DJANGO_DB_CONN_MAX_AGE", 600)),
        }
    }

# --------------------------
# MongoDB configuration
# - A aplicação usará MONGODB_URL (string de conexão). Se ausente, mantém o formato antigo MONGODB dict.
# - Exponho MONGODB_URL, MONGO_CLIENT e MONGO_DB para que o código da app possa reaproveitar.
# --------------------------
MONGODB_URL = os.environ.get("MONGODB_URL")
MONGO_CLIENT = None
MONGO_DB = None

if MONGODB_URL:
    # Requer pymongo no requirements.txt
    try:
        from pymongo import MongoClient  # type: ignore
        MONGO_CLIENT = MongoClient(MONGODB_URL)
        # get_default_database funciona quando a URI contém o nome do DB
        try:
            MONGO_DB = MONGO_CLIENT.get_default_database()
        except Exception:
            # se não houver DB na URL, use variável específica
            mongo_dbname = os.environ.get("MONGODB_DB_NAME", None)
            if mongo_dbname:
                MONGO_DB = MONGO_CLIENT[mongo_dbname]
            else:
                MONGO_DB = None
    except Exception:
        # caso a biblioteca não exista ou haja erro de conexão
        MONGO_CLIENT = None
        MONGO_DB = None
else:
    # mantém compatibilidade com antiga configuração MONGODB do settings.py
    MONGODB = globals().get("MONGODB", {})
    if MONGODB:
        MONGO_CLIENT = None
        MONGO_DB = None  # deixe a app inicializar com parâmetros antigos se necessário

# Static / media seguem do settings base (importado)
STATIC_ROOT = globals().get("STATIC_ROOT", BASE_DIR / "staticfiles")
STATIC_URL = globals().get("STATIC_URL", "/static/")

# Logging inherits from base settings; garante console handler
LOGGING = globals().get("LOGGING", {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO")},
})

# Conveniência: deixe claro qual settings o Render deve usar
# (DJANGO_SETTINGS_MODULE deve ser setado no Render: provision.settings_render)