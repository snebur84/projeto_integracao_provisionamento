# Variáveis usadas pelo Terraform (nomes esperados pelo workflow).
variable "render_api_key" {
  type        = string
  description = "Render API key. Also can be passed via env RENDER_API_KEY."
  sensitive   = true
}

variable "django_secret_key" {
  type      = string
  description = "DJANGO_SECRET_KEY to set in the app service env"
  sensitive = true
}

variable "django_debug" {
  type    = string
  default = "0"
  description = "DJANGO_DEBUG (0 or 1)"
}

variable "django_allowed_hosts" {
  type    = string
  default = "localhost"
  description = "DJANGO_ALLOWED_HOSTS (comma separated)"
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
  description = "Persistent disk size for MySQL service in GB"
}

# MongoDB
variable "mongodb_service_name" {
  type    = string
  default = "mvp-mongo"
}

variable "mongodb_root_username" {
  type      = string
  default   = "mongo_root"
  sensitive = false
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
  description = "Persistent disk size for MongoDB service in GB"
}

# App
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
  description = "Optional build command for Render service build settings"
}

variable "provision_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

# Misc
variable "region" {
  type    = string
  default = ""
  description = "Optional region if supported by provider"
}