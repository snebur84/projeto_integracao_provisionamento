variable "gcp_project" {
  description = "GCP project id"
  type        = string
}

variable "gcp_region" {
  description = "GCP region"
  type        = string
}

variable "gcp_zone" {
  description = "GCP zone"
  type        = string
}

variable "environment" {
  description = "Deployment environment (prod, staging, ...)"
  type        = string
  default     = "prod"
}

variable "instance_name" {
  description = "Optional instance name"
  type        = string
  default     = null
}

variable "machine_type" {
  description = "Instance machine type"
  type        = string
  default     = "e2-medium"
}

variable "boot_image" {
  description = "Boot image for instance"
  type        = string
  default     = "debian-cloud/debian-12"
}

variable "boot_disk_size_gb" {
  description = "Boot disk size in GB"
  type        = number
  default     = 20
}

variable "boot_disk_type" {
  description = "Boot disk type"
  type        = string
  default     = "pd-standard"
}

variable "network" {
  description = "VPC network to attach instance to"
  type        = string
  default     = "default"
}

variable "service_account_email" {
  description = "Service account email to attach to the instance (optional)"
  type        = string
  default     = null
}

variable "service_account_scopes" {
  description = "Scopes for the service account"
  type        = list(string)
  default     = ["cloud-platform"]
}

variable "instance_tags" {
  description = "List of network tags for the instance"
  type        = list(string)
  default     = []
}

variable "instance_labels" {
  description = "Map of labels to apply to the instance"
  type        = map(string)
  default     = {}
}