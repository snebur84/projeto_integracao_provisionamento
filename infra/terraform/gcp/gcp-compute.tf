resource "google_compute_instance" "provision" {
  name         = var.instance_name
  project      = var.gcp_project
  zone         = var.gcp_zone
  machine_type = var.machine_type

  boot_disk {
    initialize_params {
      image = var.boot_image
      size  = var.boot_disk_size_gb
      type  = "pd-standard"
    }
  }

  network_interface {
    network = var.network
    access_config {
      nat_ip = google_compute_address.provision_ip.address
    }
  }

  metadata = {
    ENV             = var.environment
    CONTAINER_IMAGE = var.container_image
    CONTAINER_PORT  = tostring(var.container_port)
  }

  # Ensure this instance has the 'web' tag so firewall rules can target it
  tags = concat(try(var.instance_tags, []), ["web"])

  service_account {
    email  = try(var.service_account_email, null)
    scopes = var.service_account_scopes
  }

  # Load startup script from file in module
  metadata_startup_script = file("${path.module}/provision.sh")

  lifecycle {
    create_before_destroy = false
  }
}