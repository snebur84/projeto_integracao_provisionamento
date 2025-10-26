# infra/terraform/render/main.tf
# Cria um project, um serviço web (Django) e opcionalmente um serviço privado Postgres
# Ajuste valores (repo/branch/region/plan) conforme sua conta Render e necessidades.
# Este arquivo foi adaptado ao schema do provider usado neste repositório (render-oss/render).

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

# Serviço privado que provê Postgres (opcional, criado quando var.create_postgres = true)
resource "render_private_service" "postgres" {
  count = var.create_postgres ? 1 : 0

  name = "${var.service_name}-postgres"

  # runtime_source como objeto (não bloco)
  runtime_source = {
    image = {
      image = "postgres:15-alpine"
    }
  }

  plan   = "starter"   # ajuste conforme necessidade
  region = "oregon"    # ajuste conforme sua conta

  # env_vars: map de objetos { value = ... } (schema do provider)
  env_vars = {
    POSTGRES_DB       = { value = var.postgres_database }
    POSTGRES_USER     = { value = var.postgres_user }
    POSTGRES_PASSWORD = { value = var.postgres_password }
  }

  # Conectar ao environment do projeto (use environment_id, não project_id)
  environment_id = render_project.project.environments["production"].id
}

# Serviço web para a aplicação Django (build via Dockerfile no repositório)
resource "render_web_service" "provision" {
  count = var.create_service ? 1 : 0

  name = var.service_name

  # runtime_source como objeto (docker)
  runtime_source = {
    docker = {
      dockerfile_path = "Dockerfile"
    }
  }

  # start command
  start_command = "gunicorn provision.wsgi:application --bind 0.0.0.0:$PORT"

  # região do serviço
  region = "oregon"

  # env_vars: DJANGO_SETTINGS_MODULE será sobrescrito pelo workflow CI
  env_vars = {
    DJANGO_SETTINGS_MODULE = { value = "provision.settings_render" }
  }

  # Ligar ao environment do project
  environment_id = render_project.project.environments["production"].id
}