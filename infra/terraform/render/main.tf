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
# substituir a definição do Postgres privado por um recurso de banco gerenciado
# (o nome do recurso pode variar conforme versão do provider; aqui uso render_database como exemplo)

resource "render_postgres" "db" {
  count = var.create_postgres ? 1 : 0

  name         = "${local.sanitized_name}-db"
  plan         = var.postgres_plan 
  region       = var.region
  version      = "17"

  database_name = var.postgres_database
  user          = var.postgres_user
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