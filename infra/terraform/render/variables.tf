variable "render_api_key" {
  type        = string
  description = "Render API key. Pass via TF_VAR_render_api_key (GitHub Actions) or set TF var locally."
  sensitive   = true
}

variable "render_owner_id" {
  type        = string
  description = "Owner ID (usr-... or tea-...). Optional; provider reads RENDER_OWNER_ID env if set."
  default     = ""
}

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