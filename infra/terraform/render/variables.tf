variable "render_api_key" {
  type = string
}

variable "render_owner_id" {
  type = string
}

variable "service_name" {
  type    = string
  default = "provision" # ajuste para o nome real do serviço no Render
}

# Controle condicional: quando false, o Terraform não criará o recurso de serviço (útil quando o serviço já existe)
variable "create_service" {
  type    = bool
  default = true
}

# Variáveis para Postgres (se seu TF criar a DB no Render)
variable "create_postgres" {
  type    = bool
  default = true
}
variable "postgres_database" { type = string default = "provision_db" }
variable "postgres_user" { type = string default = "provision_user" }
variable "postgres_password" { type = string default = "" }