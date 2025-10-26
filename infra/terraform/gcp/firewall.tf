resource "google_compute_firewall" "allow_http_https" {
  name    = "allow-http-https-${var.environment}"
  project = var.gcp_project
  network = var.network

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = concat(try(var.instance_tags, []), ["web"])
  description   = "Allow HTTP/HTTPS to web instances"
}