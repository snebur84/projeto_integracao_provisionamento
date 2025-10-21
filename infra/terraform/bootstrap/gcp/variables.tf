variable "project" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for backend resources"
  type        = string
  default     = "us-central1"
}

variable "state_bucket_name" {
  description = "Name of the GCS bucket for Terraform state"
  type        = string
}

variable "environment" {
  description = "Environment name (e.g., prod, staging)"
  type        = string
  default     = "prod"
}
