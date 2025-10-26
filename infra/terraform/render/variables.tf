variable "service_name" {
  type    = string
  default = "provision_app"
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