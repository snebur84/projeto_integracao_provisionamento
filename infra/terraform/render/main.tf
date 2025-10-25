/*
  Main Terraform resources for Render:
  - render_service.mysql (container mysql:8)
  - render_service.mongo (container mongo:6)
  - render_service.app (Django app built from this repo)
*/

# -------------------------
# MySQL service (container)
# -------------------------
resource "render_service" "mysql" {
  name         = var.mysql_service_name
  # Tipo: se o provider usa 'service_type' ou 'type' ajuste aqui.
  # service_type = "service"
  # Image pública Docker (mysql)
  docker_image = "mysql:8.0"

  # Variables to initialize the mysql container
  env = {
    MYSQL_ROOT_PASSWORD = var.mysql_root_password
    MYSQL_DATABASE      = var.mysql_database
    MYSQL_USER          = var.mysql_user
    MYSQL_PASSWORD      = var.mysql_password
    MYSQL_PORT          = var.mysql_port
  }

  # Persistent disk (ajuste a chave conforme provider)
  persistent_disk = {
    size_gb    = var.mysql_disk_size_gb
    mount_path = "/var/lib/mysql"
  }

  # Make DB internal/private so it's not publicly accessible
  internal = true

  # Optional health check (ajuste se o provider suportar)
  # health_check_path = "/"
}

# -------------------------
# MongoDB service (container)
# -------------------------
resource "render_service" "mongo" {
  name         = var.mongodb_service_name
  docker_image = "mongo:6.0"

  env = {
    MONGO_INITDB_ROOT_USERNAME = var.mongodb_root_username
    MONGO_INITDB_ROOT_PASSWORD = var.mongodb_root_password
    MONGO_INITDB_DATABASE      = var.mongodb_database
    MONGODB_PORT               = var.mongodb_port
  }

  persistent_disk = {
    size_gb    = var.mongodb_disk_size_gb
    mount_path = "/data/db"
  }

  internal = true
}

# -------------------------
# Django app service
# -------------------------
resource "render_service" "app" {
  name = var.app_service_name

  # Build from repo: provider implementations vary. Example generic fields:
  build = {
    # repo format owner/repo
    repo   = var.app_repo
    # branch to build
    branch = var.app_branch
    # Optional: build command (if you have a custom build)
    build_command = var.app_build_command
  }

  # Start command must use the PORT env provided by Render
  start_command = "gunicorn provision.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3"

  # Environment variables for the app - inject DB hostnames from the other services.
  # Assumes the provider exposes an attribute like internal_hostname for internal services.
  env = {
    DJANGO_SECRET_KEY           = var.django_secret_key
    DJANGO_DEBUG                = var.django_debug
    DJANGO_ALLOWED_HOSTS        = var.django_allowed_hosts
    DJANGO_SUPERUSER_USERNAME   = var.django_superuser_username
    DJANGO_SUPERUSER_EMAIL      = var.django_superuser_email
    DJANGO_SUPERUSER_PASSWORD   = var.django_superuser_password

    # MySQL connection - MySQL host will be the internal hostname of the mysql service.
    MYSQL_HOST     = render_service.mysql.internal_hostname
    MYSQL_PORT     = var.mysql_port
    MYSQL_DATABASE = var.mysql_database
    MYSQL_USER     = var.mysql_user
    MYSQL_PASSWORD = var.mysql_password

    # Mongo connection - repository code expects MONGODB_HOST and MONGODB_PORT
    MONGODB_HOST = render_service.mongo.internal_hostname
    MONGODB_PORT = var.mongodb_port

    PROVISION_API_KEY = var.provision_api_key
  }

  # Health check path (adjust per provider)
  # health_check_path = "/health" 
  # health_check_interval = 10
  # health_check_timeout = 5
}

# Depend on DB services to be sure they are created before app wiring
resource "null_resource" "wait_for_db_creation" {
  # This is a placeholder to express dependency ordering
  depends_on = [
    render_service.mysql,
    render_service.mongo,
    render_service.app
  ]
}