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

variable "wait_for_deploy_completion" {
  type    = bool
  default = false
}

variable "skip_deploy_after_service_update" {
  type    = bool
  default = false
}