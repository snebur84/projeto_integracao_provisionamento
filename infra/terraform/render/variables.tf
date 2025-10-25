# Project / environment
variable "project_name" {
  type    = string
  default = "mvp-project"
}

# Map of environments: key -> { name, protected_status, network_isolated }
variable "project_environments" {
  type = map(object({
    name             = string
    protected_status = string
    network_isolated = bool
  }))
  default = {
    production = {
      name             = "production"
      protected_status = "unprotected"
      network_isolated = false
    }
  }
}

# Region / plans / runtime defaults
variable "region" {
  type    = string
  default = "oregon"
}

variable "mysql_plan" {
  type    = string
  default = "starter"
}

variable "mongodb_plan" {
  type    = string
  default = "starter"
}

variable "app_plan" {
  type    = string
  default = "starter"
}

# App build/runtime settings
variable "app_service_name" {
  type    = string
  default = "provision-app"
}

variable "app_repo" {
  type    = string
  default = "https://github.com/snebur84/projeto_integracao_provisionamento"
}

variable "app_branch" {
  type    = string
  default = "main"
}

variable "dockerfile_path" {
  type    = string
  default = "Dockerfile"
}

variable "docker_context" {
  type    = string
  default = "."
}

variable "app_auto_deploy" {
  type    = bool
  default = true
}

# Django / app secrets
variable "django_secret_key" {
  type      = string
  sensitive = true
}

variable "django_debug" {
  type    = string
  default = "0"
}

variable "django_allowed_hosts" {
  type    = string
  default = "localhost"
}

variable "django_superuser_username" {
  type    = string
  default = "admin"
}

variable "django_superuser_email" {
  type    = string
  default = "admin@example.com"
}

variable "django_superuser_password" {
  type      = string
  sensitive = true
}

variable "provision_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

# MySQL
variable "mysql_service_name" {
  type    = string
  default = "mvp-mysql"
}

variable "mysql_root_password" {
  type      = string
  sensitive = true
}

variable "mysql_database" {
  type    = string
  default = "provision_db"
}

variable "mysql_user" {
  type    = string
  default = "provision_user"
}

variable "mysql_password" {
  type      = string
  sensitive = true
}

variable "mysql_port" {
  type    = string
  default = "3306"
}

variable "mysql_disk_size_gb" {
  type    = number
  default = 20
}

# MongoDB
variable "mongodb_service_name" {
  type    = string
  default = "mvp-mongo"
}

variable "mongodb_root_username" {
  type    = string
  default = "mongo_root"
}

variable "mongodb_root_password" {
  type      = string
  sensitive = true
}

variable "mongodb_database" {
  type    = string
  default = "provision_mongo"
}

variable "mongodb_port" {
  type    = string
  default = "27017"
}

variable "mongodb_disk_size_gb" {
  type    = number
  default = 20
}