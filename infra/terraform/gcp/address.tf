resource "google_compute_address" "provision_ip" {
  name    = "${var.instance_name}-ip"
  region  = var.gcp_region
  project = var.gcp_project
}