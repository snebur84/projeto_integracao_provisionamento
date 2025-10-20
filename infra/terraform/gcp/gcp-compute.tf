# Example GCP compute instance that downloads and runs the provision script
locals {
  use_existing_sa = length(trimspace(var.existing_instance_sa)) > 0
}

resource "google_compute_instance" "provision" {
  count        = var.create_instance ? 1 : 0
  name         = "${var.name_prefix}-provision"
  machine_type = "e2-micro"
  zone         = var.gcp_zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 10
    }
  }

  network_interface {
    network = "default"
    access_config {} # give external IP (remove if unnecessary)
  }

  # Attach a service account to allow VM to access GCS (optional).
  service_account {
    email  = local.use_existing_sa ? var.existing_instance_sa : null
    scopes = local.use_existing_sa ? ["https://www.googleapis.com/auth/cloud-platform"] : []
  }

  metadata_startup_script = <<-EOF
    #!/bin/bash
    set -euo pipefail
    PRESIGNED_URL="${var.presigned_url}"
    ENV="${var.gcp_region}"
    if [ -n "${var.presigned_url}" ]; then
      echo "Downloading provision script..."
      curl -fsSL "${var.presigned_url}" -o /tmp/provision.sh || exit 1
      chmod +x /tmp/provision.sh
      /bin/bash /tmp/provision.sh "${ENV}" || exit 1
    else
      echo "No presigned URL provided; skipping provision."
    fi
  EOF

  tags = ["provision"]
}

output "instance_id" {
  value       = try(google_compute_instance.provision[0].id, "")
  description = "ID of created instance (empty if not created)"
}

output "public_ip" {
  value       = try(google_compute_instance.provision[0].network_interface[0].access_config[0].nat_ip, "")
  description = "Public IP if assigned"
}