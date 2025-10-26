// google_compute_instance "provision" rewritten to avoid inline heredoc interpolation
// The startup script is loaded from a file using file("${path.module}/provision.sh")
// which prevents Terraform from trying to parse/interpolate the script contents.
// Add infra/terraform/gcp/provision.sh to the repo (example provided below).

resource "google_compute_instance" "provision" {
  name         = coalesce(var.instance_name, "provision-instance")
  project      = var.gcp_project
  zone         = var.gcp_zone
  machine_type = coalesce(var.machine_type, "e2-medium")

  boot_disk {
    initialize_params {
      image = coalesce(var.boot_image, "debian-cloud/debian-12")
      size  = coalesce(var.boot_disk_size_gb, 20)
      type  = coalesce(var.boot_disk_type, "pd-standard")
    }
  }

  network_interface {
    network = coalesce(var.network, "default")
    access_config {}
  }

  // Provide the deployment environment as instance metadata
  metadata = {
    ENV = coalesce(var.environment, "prod")
  }

  // Optional service account and scopes
  service_account {
    email  = try(var.service_account_email, null)
    scopes = try(var.service_account_scopes, ["cloud-platform"])
  }

  // Load the startup script from a file in the module directory. Using file()
  // ensures Terraform does not try to parse or interpolate the script content.
  // Make sure infra/terraform/gcp/provision.sh exists in the repository.
  metadata_startup_script = file("${path.module}/provision.sh")

  tags = try(var.instance_tags, [])

  lifecycle {
    create_before_destroy = false
  }

  // Optional labels
  labels = try(var.instance_labels, null)
}