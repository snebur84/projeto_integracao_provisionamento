output "state_bucket" {
  description = "GCS bucket name for Terraform state"
  value       = google_storage_bucket.terraform_state.name
}

output "state_bucket_url" {
  description = "GCS bucket URL for Terraform state"
  value       = "gs://${google_storage_bucket.terraform_state.name}"
}

output "region" {
  description = "Region for bootstrap resources"
  value       = var.region
}
