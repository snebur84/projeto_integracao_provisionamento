variable "service_name" {
  type    = string
  # Ajustado para hífen por padrão (underscores podem ser rejeitados pelo provider)
  default = "provision-app"
}

variable "create_service" {
  type    = bool
  default = true
}

variable "create_postgres" {
  type    = bool
  default = true
}

variable "postgres_database" {
  type    = string
  default = "provision_db"
}

variable "postgres_user" {
  type    = string
  default = "provision_user"
}

variable "postgres_password" {
  type    = string
  default = ""
}

variable "postgres_plan" {
  type    = string
  default = "free"
}

# Imagem usada para o serviço Postgres: separa o repositório (image_url) do tag (image_tag)
variable "postgres_image_repo" {
  type    = string
  default = "docker.io/library/postgres"
}

variable "postgres_image_tag" {
  type    = string
  default = "15-alpine"
}

# Planos/tiers utilizados
variable "postgres_plan" {
  type    = string
  default = "starter"
}

variable "web_plan" {
  type    = string
  default = "starter"
}

# Código do app (repo + branch) — necessário para runtime_source.docker
variable "repo_url" {
  type    = string
  default = "https://github.com/snebur84/projeto_integracao_provisionamento"
}

variable "repo_branch" {
  type    = string
  default = "main"
}

variable "dockerfile_path" {
  type    = string
  default = "Dockerfile"
}

variable "region" {
  type    = string
  default = "oregon"
}

variable "start_command" {
  type    = string
  default = "gunicorn provision.wsgi:application --bind 0.0.0.0:$PORT"
}