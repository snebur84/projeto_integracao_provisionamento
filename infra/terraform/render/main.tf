/*
Main Terraform resources (adaptados para render-oss/render):
- render_project: agora recebe `environments` (lista)
- render_private_service: exige `plan`, `region`, `runtime_source` e usa `project_id`
- render_web_service: exige `plan`, `region`, `runtime_source` e usa `project_id`
Observação: atributos como `docker_image`, `persistent_disk`, `internal_hostname`, `default_domain`
podem variar entre versões do provider. Se o plan reclamar de "Unknown argument" cole o erro aqui.
*/

# Optional project to group services
resource "render_project" "project" {
  name         = var.project_name
  environments = var.project_environments
}

# -------------------------
# MySQL private service (container)
# -------------------------
resource "render_private_service" "mysql" {
  name           = var.mysql_service_name
  project_id     = render_project.project.id

  # Required by provider
  plan           = var.mysql_plan
  region         = var.region
  runtime_source = var.runtime_source

  # Docker image to run (provider may accept this attr; if not, eu atualizo conforme o erro)
  docker_image = "mysql:8.0"

  # Persistent disk (se suportado pela versão do provider)
  persistent_disk = {
    size_gb    = var.mysql_disk_size_gb
    mount_path = "/var/lib/mysql"
  }

  # Note: environment variables for the service may need to be set via render_env_group/render_keyvalue
  # depending on the provider version. If provider accepts env in this block, re-add depois.
}

# -------------------------
# MongoDB private service (container)
# -------------------------
resource "render_private_service" "mongo" {
  name           = var.mongodb_service_name
  project_id     = render_project.project.id

  plan           = var.mongodb_plan
  region         = var.region
  runtime_source = var.runtime_source

  docker_image = "mongo:6.0"

  persistent_disk = {
    size_gb    = var.mongodb_disk_size_gb
    mount_path = "/data/db"
  }
}

# -------------------------
# Django app (public web service)
# -------------------------
resource "render_web_service" "app" {
  name       = var.app_service_name
  project_id = render_project.project.id

  plan           = var.app_plan
  region         = var.region
  runtime_source = var.runtime_source

  # NOTE: building from repo / configuring build may require a nested block different
  # depending on the provider version. If the provider accepts a docker_image you can
  # point to a pre-built image; otherwise adapt this to the provider's repository/build block.
  # Here we prefer to let the provider build the repo if it supports it; if not, set app_docker_image.
  dynamic "docker_image" {
    for_each = var.app_docker_image != "" ? [var.app_docker_image] : []
    content {
      value = docker_image.value
    }
  }

  # Start command: escape shell interpolation to avoid Terraform parsing
  start_command = "gunicorn provision.wsgi:application --bind 0.0.0.0:$${PORT:-8000} --workers 3"

  # Environment variables / secrets should be provided using render_env_group / render_env_group_link
  # or render_keyvalue depending on provider support. We don't declare a flat `env` block here
  # because that produced "unsupported argument" errors on your setup.
}