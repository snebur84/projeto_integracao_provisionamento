#!/usr/bin/env bash
# Provision script executed on VM startup.
# Reads metadata attributes CONTAINER_IMAGE and CONTAINER_PORT and starts the container.
set -euo pipefail
IFS=$'\n\t'

# Read metadata values (if missing, fall back to defaults)
METADATA_BASE="http://metadata.google.internal/computeMetadata/v1/instance/attributes"
get_meta() {
  curl -sf -H "Metadata-Flavor: Google" "${METADATA_BASE}/$1" || true
}

ENV="$(get_meta ENV || echo "prod")"
CONTAINER_IMAGE="$(get_meta CONTAINER_IMAGE || echo "nginx:stable")"
CONTAINER_PORT="$(get_meta CONTAINER_PORT || echo "80")"
HOST_PORT="${CONTAINER_PORT}"

echo "Provision script starting. ENV=${ENV}, IMAGE=${CONTAINER_IMAGE}, PORT=${CONTAINER_PORT}"

# Install docker quickly (use official convenience script for speed)
if ! command -v docker >/dev/null 2>&1; then
  echo "Installing Docker..."
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg lsb-release
  curl -fsSL https://get.docker.com | sh
fi

# ensure docker is available
if ! systemctl is-active --quiet docker; then
  systemctl enable docker || true
  systemctl start docker || true
fi

# Pull the container image
echo "Pulling container image ${CONTAINER_IMAGE}..."
/usr/bin/docker pull "${CONTAINER_IMAGE}"

# Create a systemd service so the container starts on reboot
SERVICE_PATH="/etc/systemd/system/myapp.service"
cat > "${SERVICE_PATH}" <<EOF
[Unit]
Description=MyApp container
After=docker.service
Requires=docker.service

[Service]
Restart=always
ExecStartPre=/usr/bin/docker rm -f myapp || true
ExecStart=/usr/bin/docker run --name myapp --rm -p ${HOST_PORT}:${CONTAINER_PORT} --restart unless-stopped ${CONTAINER_IMAGE}
ExecStop=/usr/bin/docker stop myapp
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

chmod 644 "${SERVICE_PATH}"
systemctl daemon-reload
systemctl enable --now myapp.service

# Simple healthcheck loop to wait until container responds (timeout ~60s)
echo "Waiting for container to become healthy..."
for i in $(seq 1 30); do
  if curl -s "http://127.0.0.1:${HOST_PORT}/" >/dev/null 2>&1; then
    echo "Application is responding locally on port ${HOST_PORT}"
    exit 0
  fi
  sleep 2
done

echo "Warning: container did not respond on localhost:${HOST_PORT} within timeout"
exit 0