/*
Terraform resources adapted to use provider render-oss/render resource types
(discovered available resource types: render_project, render_private_service, render_web_service, etc.).

Notas importantes:
- Os nomes exatos de atributos (por exemplo persistent_disk, internal_hostname, default_domain, url)
  podem variar entre versões do provider. Se terraform plan reclamar de um campo desconhecido,
  cole o erro aqui que eu ajusto o bloco conforme a versão instalada.
- Escapei a interpolação de shell ($${PORT:-8000}) para que o Terraform não tente interpretar.
*/

# Optional project to group services
resource "render_project" "project" {
  name = var.project_name
}

# -------------------------
# MySQL private service (container)
# -------------------------
resource "render_private_service" "mysql" {
  name    = var.mysql_service_name
  # Associa ao projeto se o provider aceita project_id
  project = try(render_project.project.id, null)

  # Docker image to run
  docker_image = "mysql:8.0"

  # Env vars used by the mysql image on startup
  env = {
    MYSQL_ROOT_PASSWORD = var.mysql_root_password
    MYSQL_DATABASE      = var.mysql_database
    MYSQL_USER          = var.mysql_user
    MYSQL_PASSWORD      = var.mysql_password
    MYSQL_PORT          = var.mysql_port
  }

  # Persistent disk (ajuste se o provider usar outro bloco/atributo)
  persistent_disk = {
    size_gb    = var.mysql_disk_size_gb
    mount_path = "/var/lib/mysql"
  }

  # Make DB internal/private so it's not publicly accessible
  internal = true
}

# -------------------------
# MongoDB private service (container)
# -------------------------
resource "render_private_service" "mongo" {
  name    = var.mongodb_service_name
  project = try(render_project.project.id, null)

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
# Django app (public web service)
# -------------------------
resource "render_web_service" "app" {
  name = var.app_service_name
  project = try(render_project.project.id, null)

  # Build settings: provider implementations differ — try these fields first.
  # If your provider requires a nested "build" block or "repo" attribute in another shape,
  # adapte conforme o erro mostrado pelo terraform plan.
  repo         = var.app_repo
  branch       = var.app_branch
  build_command = var.app_build_command
  auto_deploy  = true

  # Start command: use $${PORT:-8000} to avoid Terraform interpolation
  start_command = "gunicorn provision.wsgi:application --bind 0.0.0.0:$${PORT:-8000} --workers 3"

  # Env vars for the Django app. Use the internal hostnames from the private services.
  # Attribute names for internal hostnames may differ; if terraform errors, substitua
  # render_private_service.*.internal_hostname pelo atributo correto exposto pelo provider.
  env = {
    DJANGO_SECRET_KEY           = var.django_secret_key
    DJANGO_DEBUG                = var.django_debug
    DJANGO_ALLOWED_HOSTS        = var.django_allowed_hosts
    DJANGO_SUPERUSER_USERNAME   = var.django_superuser_username
    DJANGO_SUPERUSER_EMAIL      = var.django_superuser_email
    DJANGO_SUPERUSER_PASSWORD   = var.django_superuser_password

    MYSQL_HOST     = try(render_private_service.mysql.internal_hostname, "")
    MYSQL_PORT     = var.mysql_port
    MYSQL_DATABASE = var.mysql_database
    MYSQL_USER     = var.mysql_user
    MYSQL_PASSWORD = var.mysql_password

    MONGODB_HOST = try(render_private_service.mongo.internal_hostname, "")
    MONGODB_PORT = var.mongodb_port

    PROVISION_API_KEY = var.provision_api_key
  }

  # Health-check fields (opcionais e dependem do provider)
  # health_check_path = "/"
  # health_check_interval_seconds = 10
}