# infra/terraform/render/main.tf
# Ajustado para diferenciar image_url e tag conforme schema do provider render-oss/render.

locals {
  sanitized_name = replace(var.service_name, "_", "-")
}

# Projeto que agrupa os serviços (ambientes)
resource "render_project" "project" {
  name = local.sanitized_name

  environments = {
    production = {
      name             = "production"
      protected_status = "unprotected"
    }
  }
}

# Serviço privado que provê Postgres (opcional)
resource "render_private_service" "postgres" {
  count = var.create_postgres ? 1 : 0

  name = "${local.sanitized_name}-postgres"

  # runtime_source como objeto: informamos image_url (sem tag) e tag separadamente
  runtime_source = {
    image = {
      image_url = var.postgres_image_repo
      tag       = var.postgres_image_tag
    }
  }

  plan   = var.postgres_plan
  region = var.region

  env_vars = {
    POSTGRES_DB       = { value = var.postgres_database }
    POSTGRES_USER     = { value = var.postgres_user }
    POSTGRES_PASSWORD = { value = var.postgres_password }
  }

  environment_id = render_project.project.environments["production"].id
}

# Serviço web para a aplicação Django (build via Dockerfile no repositório)
resource "render_web_service" "provision" {
  count = var.create_service ? 1 : 0

  name = local.sanitized_name

  runtime_source = {
    docker = {
      repo_url        = var.repo_url
      branch          = var.repo_branch
      dockerfile_path = var.dockerfile_path
    }
  }

  plan = var.web_plan
  region = var.region

  start_command = var.start_command

  env_vars = {
    DJANGO_SETTINGS_MODULE = { value = "provision.settings_render" }
  }

  environment_id = render_project.project.environments["production"].id
}