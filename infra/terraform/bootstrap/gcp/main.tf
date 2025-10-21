# Bootstrap Terraform configuration for GCP GCS backend
# This creates the GCS bucket needed to store Terraform state remotely

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = var.project
  region  = var.region
}

# GCS bucket for Terraform state
resource "google_storage_bucket" "terraform_state" {
  name          = var.state_bucket_name
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  labels = {
    name        = "terraform-state"
    environment = var.environment
    managed_by  = "terraform-bootstrap"
  }
}
