#!/usr/bin/env bash
# Provision script executed on VM startup. This file is injected by Terraform
# into the instance via metadata_startup_script using file("${path.module}/provision.sh").
# Keep it simple and safe; it will run on the VM, not during Terraform runtime.
set -euo pipefail
IFS=$'\n\t'

# Read ENV from instance metadata (GCE metadata server).
ENV="$(curl -fsSL -H 'Metadata-Flavor: Google' \
  'http://metadata.google.internal/computeMetadata/v1/instance/attributes/ENV' || true)"

# Fallback to default if metadata not available
if [ -z "${ENV}" ]; then
  ENV="prod"
fi

echo "Instance startup: running provision.sh with ENV='${ENV}'"

# If a local provision script exists, run it with ENV argument
if [ -f /tmp/provision.sh ]; then
  /bin/bash /tmp/provision.sh "${ENV}" || {
    echo "Provision script failed" >&2
    exit 1
  }
else
  echo "/tmp/provision.sh not found; no additional local provisioning to run"
  # Optional: fetch a remote provisioning script and run it (example)
  # gsutil cp gs://my-bucket/path/provision.sh /tmp/provision.sh || true
  # chmod +x /tmp/provision.sh || true
  # /bin/bash /tmp/provision.sh "${ENV}" || exit 1
fi

echo "Startup provision completed successfully"