output "instance_external_ip" {
  description = "External IP of the provision instance"
  value       = google_compute_address.provision_ip.address
}