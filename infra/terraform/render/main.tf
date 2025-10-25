locals {
  # key of the primary environment we create / use (default "production" - key name in project_environments)
  env_key = try(keys(var.project_environments)[0], "production")
  # convenience: the environment name object
  env_obj = var.project_environments[local.env_key]
}

# Project (requires environments map of objects)
resource "render_project" "project" {
  name         = var.project_name
  environments = var.project_environments
}

# PRIVATE SERVICE: MySQL (image-backed private service)
resource "render_private_service" "mysql" {
  name  = var.mysql_service_name
  plan  = var.mysql_plan
  region = var.region

  # runtime_source requires an object; use image (image_url)
  runtime_source = {
    image = {
      image_url = "docker.io/library/mysql:8.0"
    }
  }

  # attach a disk if supported
  disk = {
    name       = "${var.mysql_service_name}-disk"
    size_gb    = var.mysql_disk_size_gb
    mount_path = "/var/lib/mysql"
  }

  # env_vars is a map of objects { value = "..." } per schema
  env_vars = {
    MYSQL_ROOT_PASSWORD = { value = var.mysql_root_password }
    MYSQL_DATABASE      = { value = var.mysql_database }
    MYSQL_USER          = { value = var.mysql_user }
    MYSQL_PASSWORD      = { value = var.mysql_password }
    MYSQL_PORT          = { value = var.mysql_port }
  }

  # associate to the created project environment (environment_id is the attribute on services)
  # render_project.project.environments is a map; reference by key (local.env_key)
  environment_id = render_project.project.environments[local.env_key].id
}

# PRIVATE SERVICE: MongoDB (image-backed)
resource "render_private_service" "mongo" {
  name   = var.mongodb_service_name
  plan   = var.mongodb_plan
  region = var.region

  runtime_source = {
    image = {
      image_url = "docker.io/library/mongo:6.0"
    }
  }

  disk = {
    name       = "${var.mongodb_service_name}-disk"
    size_gb    = var.mongodb_disk_size_gb
    mount_path = "/data/db"
  }

  env_vars = {
    MONGO_INITDB_ROOT_USERNAME = { value = var.mongodb_root_username }
    MONGO_INITDB_ROOT_PASSWORD = { value = var.mongodb_root_password }
    MONGO_INITDB_DATABASE      = { value = var.mongodb_database }
    MONGODB_PORT               = { value = var.mongodb_port }
  }

  environment_id = render_project.project.environments[local.env_key].id
}

# WEB SERVICE: Django app (build from repo using Dockerfile)
resource "render_web_service" "app" {
  name   = var.app_service_name
  plan   = var.app_plan
  region = var.region

  runtime_source = {
    docker = {
      repo_url       = var.app_repo
      branch         = var.app_branch
      dockerfile_path = var.dockerfile_path
      context        = var.docker_context
      auto_deploy    = var.app_auto_deploy
    }
  }

  # override start command (escaped $${PORT:-8000} so Terraform doesn't interpolate)
  start_command = "gunicorn provision.wsgi:application --bind 0.0.0.0:$${PORT:-8000} --workers 3"

  # environment for the web app. Use service URLs from private services as host values.
  env_vars = {
    DJANGO_SECRET_KEY         = { value = var.django_secret_key }
    DJANGO_DEBUG              = { value = var.django_debug }
    DJANGO_ALLOWED_HOSTS      = { value = var.django_allowed_hosts }
    DJANGO_SUPERUSER_USERNAME = { value = var.django_superuser_username }
    DJANGO_SUPERUSER_EMAIL    = { value = var.django_superuser_email }
    DJANGO_SUPERUSER_PASSWORD = { value = var.django_superuser_password }

    # DB connection values (render_private_service.*.url is computed by provider)
    MYSQL_HOST     = { value = try(render_private_service.mysql.url, "") }
    MYSQL_PORT     = { value = var.mysql_port }
    MYSQL_DATABASE = { value = var.mysql_database }
    MYSQL_USER     = { value = var.mysql_user }
    MYSQL_PASSWORD = { value = var.mysql_password }

    MONGODB_HOST = { value = try(render_private_service.mongo.url, "") }
    MONGODB_PORT = { value = var.mongodb_port }

    PROVISION_API_KEY = { value = var.provision_api_key }
  }

  environment_id = render_project.project.environments[local.env_key].id
}