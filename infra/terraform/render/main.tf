# infra/terraform/render/main.tf
# Cria um project, um serviço web (Django) e opcionalmente um serviço privado Postgres
# Adaptado ao provider render-oss/render e ao esquema exigido (image_url, repo_url, branch, plan, env_vars).

# Projeto que agrupa os serviços (ambientes)
resource "render_project" "project" {
  name = var.service_name

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

  name = "${var.service_name}-postgres"

  # runtime_source como objeto: image requer image_url
  runtime_source = {
    image = {
      image_url = var.postgres_image_url
    }
  }

  plan   = var.postgres_plan
  region = var.region

  # env_vars: map de objetos { value = ... } (schema do provider)
  env_vars = {
    POSTGRES_DB       = { value = var.postgres_database }
    POSTGRES_USER     = { value = var.postgres_user }
    POSTGRES_PASSWORD = { value = var.postgres_password }
  }

  # Conectar ao environment do projeto
  environment_id = render_project.project.environments["production"].id
}

# Serviço web para a aplicação Django (build via Dockerfile no repositório)
resource "render_web_service" "provision" {
  count = var.create_service ? 1 : 0

  name = var.service_name

  # runtime_source como objeto (docker) — requer repo_url e branch
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
    # outros env vars mínimos podem ser adicionados aqui como placeholders
  }

  environment_id = render_project.project.environments["production"].id
}

# Observação:
# - Preencha/ajuste var.* (repo_url, branch, plans, region) via terraform.tfvars, TF_VAR_* no CI ou defaults abaixo.
# - O workflow do GitHub Actions deve passar TF_VAR_repo_url e TF_VAR_repo_branch se desejar controlar o source via CI.