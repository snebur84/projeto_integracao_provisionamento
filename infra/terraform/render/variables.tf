variable "project_name" {
  type        = string
  description = "Name for the Render project that groups services"
  default     = "provision-app"
}

variable "project_environments" {
  type        = list(string)
  description = "Environments for the project (required by provider)"
  default     = ["production"]
}

# Provider / region / runtime choices
variable "region" {
  type        = string
  description = "Render region (required by provider)"
  default     = "oregon"
}

variable "runtime_source" {
  type        = string
  description = "Runtime source type required by provider (e.g. \"docker\", \"docker_image\", etc.). Adjust if provider expects other value."
  default     = "docker"
}

# Plans for services (provider requires a plan argument)
variable "mysql_plan" {
  type        = string
  description = "Plan for MySQL private service (adjust to available plans)"
  default     = "starter"
}

variable "mongodb_plan" {
  type        = string
  description = "Plan for MongoDB private service (adjust to available plans)"
  default     = "starter"
}

variable "app_plan" {
  type        = string
  description = "Plan for the web service (adjust to available plans)"
  default     = "starter"
}

# Django / app
variable "app_service_name" {
  type    = string
  default = "provision-app"
}

variable "app_repo" {
  type    = string
  default = "snebur84/projeto_integracao_provisionamento"
}

variable "app_branch" {
  type    = string
  default = "main"
}

variable "app_build_command" {
  type    = string
  default = ""
}

variable "app_docker_image" {
  type    = string
  default = "" # If you want to point to a prebuilt image, set this; otherwise leave empty to build from repo.
}

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

variable "mongodb_plan" {
  type    = string
  default = "starter"
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