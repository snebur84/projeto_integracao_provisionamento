resource "google_compute_instance" "provision" {
  name         = coalesce(var.instance_name, "provision-instance")
  project      = var.gcp_project
  zone         = var.gcp_zone
  machine_type = coalesce(var.machine_type, "e2-medium")

  boot_disk {
    initialize_params {
      image = coalesce(var.boot_image, "debian-cloud/debian-12")
      size  = 20
      type  = "pd-standard"
    }
  }

  network_interface {
    network = coalesce(var.network, "default")
    access_config {}
  }

  // Provide the deployment environment as an instance metadata attribute.
  // The startup script will read this attribute from the metadata server.
  metadata = {
    ENV = coalesce(var.environment, "prod")
  }

  // Optional service account and scopes; adjust as needed in variables.tf
  service_account {
    email  = try(var.service_account_email, null)
    scopes = try(var.service_account_scopes, ["cloud-platform"])
  }

  // Use a single-quoted heredoc so Terraform will not attempt to interpolate
  // expressions like ${...} inside the script. The script runs on the VM and
  // may reference shell variables (e.g. $ENV) which are populated at runtime.
  metadata_startup_script = <<'EOF'
#!/bin/bash
set -euo pipefail

# Get the ENV metadata attribute from the metadata server (if present).
# This is the authoritative way to get instance metadata values.
ENV="$(curl -fsSL -H 'Metadata-Flavor: Google' \
  'http://metadata.google.internal/computeMetadata/v1/instance/attributes/ENV' \
  || true)"

# Fallback: if the metadata lookup failed, try to use an environment
# variable that might be present in the provisioning context.
if [ -z "${ENV}" ]; then
  ENV="${ENV:-prod}"
fi

echo "Instance startup: running provision.sh with ENV='${ENV}'"

# If a local /tmp/provision.sh script exists (for example copied by other
# provisioning steps), execute it with the ENV argument. Otherwise, try
# to fetch a provisioning script from a known location (optional).
if [ -f /tmp/provision.sh ]; then
  /bin/bash /tmp/provision.sh "${ENV}" || {
    echo "Provision script failed" >&2
    exit 1
  }
else
  echo "/tmp/provision.sh not found; no local provision script to run"
  # Example: you could fetch a script from a GCS object (uncomment and adapt)
  # gsutil cp gs://my-bucket/path/provision.sh /tmp/provision.sh || true
  # chmod +x /tmp/provision.sh || true
  # /bin/bash /tmp/provision.sh "${ENV}" || exit 1
fi

# Additional startup tasks can go here.
echo "Startup script completed successfully"
EOF

  // Tags, labels, etc — keep optional and non-breaking
  tags = try(var.instance_tags, [])

  // Add any necessary timeouts / lifecycle if desired
  lifecycle {
    create_before_destroy = false
  }
}