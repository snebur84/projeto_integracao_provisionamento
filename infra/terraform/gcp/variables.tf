variable "gcp_project" {
  type        = string
  description = "GCP Project ID"
}

variable "gcp_region" {
  type        = string
  description = "GCP Region"
}

variable "gcp_zone" {
  type        = string
  description = "GCP Zone"
}

variable "name_prefix" {
  type        = string
  description = "Resource name prefix"
  default     = "meuprojeto"
}

variable "presigned_url" {
  type        = string
  description = "Signed URL to the provision script (passed by workflow)"
  default     = ""
}

variable "create_instance" {
  type        = bool
  description = "Create the compute instance"
  default     = true
}

variable "existing_instance_sa" {
  type        = string
  description = "Optional existing service account email to attach to the VM"
  default     = ""
}