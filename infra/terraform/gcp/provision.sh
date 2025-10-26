#!/usr/bin/env bash
# Provision startup script for GCE instance.
# - Installs Docker and Docker Compose v2 plugin
# - Clones repository (supports private repo via GITHUB_TOKEN metadata)
# - Executes scripts/provision_ubuntu_full.sh if present
# - Runs docker compose up -d using docker-compose.yml from repo root
# - Creates a systemd unit to ensure docker compose is up on boot
set -euo pipefail
IFS=$'\n\t'

METADATA_BASE="http://metadata.google.internal/computeMetadata/v1/instance/attributes"
get_meta() {
  curl -sf -H "Metadata-Flavor: Google" "${METADATA_BASE}/$1" || true
}

# Config from metadata (set via Terraform metadata or instance metadata)
GITHUB_REPO="$(get_meta GITHUB_REPO || echo 'snebur84/projeto_integracao_provisionamento')"
GITHUB_BRANCH="$(get_meta GITHUB_BRANCH || echo 'main')"
GITHUB_TOKEN="$(get_meta GITHUB_TOKEN || true)"
WORKDIR="/opt/myapp"
REPO_URL="https://github.com/${GITHUB_REPO}.git"

log() { echo "provision: $*"; }

# Install prerequisites and Docker if missing
if ! command -v docker >/dev/null 2>&1; then
  log "Installing Docker..."
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg lsb-release git || true

  # Install Docker using convenience script
  curl -fsSL https://get.docker.com | sh
fi

# Install docker compose plugin (Compose V2)
if ! docker compose version >/dev/null 2>&1; then
  log "Installing docker compose plugin..."
  mkdir -p /usr/local/lib/docker/cli-plugins
  curl -fsSL "https://github.com/docker/compose/releases/download/v2.18.1/docker-compose-linux-x86_64" -o /usr/local/lib/docker/cli-plugins/docker-compose
  chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi

systemctl enable --now docker || true

# Prepare working directory
mkdir -p "${WORKDIR}"
cd "${WORKDIR}"

# Clone repository (prefer authenticated clone if token provided)
if [ -n "${GITHUB_TOKEN:-}" ] && [ "${GITHUB_TOKEN}" != "true" ]; then
  log "Cloning private repo using token..."
  # Use short clone to avoid exposing token in process list
  git -c http.extraHeader="AUTHORIZATION: bearer ${GITHUB_TOKEN}" clone --depth 1 --branch "${GITHUB_BRANCH}" "https://github.com/${GITHUB_REPO}.git" "${WORKDIR}/repo" || {
    log "Authenticated git clone failed; trying token-in-URL fallback..."
    rm -rf "${WORKDIR}/repo"
    git clone --depth 1 --branch "${GITHUB_BRANCH}" "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPO}.git" "${WORKDIR}/repo"
  }
else
  # Try public clone first
  log "Attempting public git clone of ${REPO_URL} (branch ${GITHUB_BRANCH})..."
  if git ls-remote --exit-code --heads "${REPO_URL}" "${GITHUB_BRANCH}" >/dev/null 2>&1; then
    git clone --depth 1 --branch "${GITHUB_BRANCH}" "${REPO_URL}" "${WORKDIR}/repo" || true
  else
    log "Public clone not available; attempting to download raw files as fallback..."
    mkdir -p "${WORKDIR}/repo"
    curl -fsSL "https://raw.githubusercontent.com/${GITHUB_REPO}/${GITHUB_BRANCH}/docker-compose.yml" -o "${WORKDIR}/repo/docker-compose.yml" || true
    curl -fsSL "https://raw.githubusercontent.com/${GITHUB_REPO}/${GITHUB_BRANCH}/scripts/provision_ubuntu_full.sh" -o "${WORKDIR}/repo/scripts/provision_ubuntu_full.sh" || true
  fi
fi

cd "${WORKDIR}/repo" || cd "${WORKDIR}" || true

# If the repo contains scripts/provision_ubuntu_full.sh, run it (reference script)
if [ -f "./scripts/provision_ubuntu_full.sh" ]; then
  log "Found scripts/provision_ubuntu_full.sh — executing it (non-interactive)..."
  chmod +x ./scripts/provision_ubuntu_full.sh || true
  # Execute safely: export metadata-derived envs so the script can read them
  export GITHUB_REPO GITHUB_BRANCH
  ./scripts/provision_ubuntu_full.sh || log "scripts/provision_ubuntu_full.sh exited with non-zero status (continuing)"
else
  log "No scripts/provision_ubuntu_full.sh found in repo; continuing"
fi

# Ensure docker compose file exists
if [ ! -f ./docker-compose.yml ]; then
  log "docker-compose.yml not found in repo root; aborting compose startup"
  exit 0
fi

# Pull images and start stack
log "Pulling images (docker compose pull) and starting stack (docker compose up -d)..."
docker compose pull --quiet || true
docker compose up -d

# Optional: attempt migrations and collectstatic if the web service provides manage.py
if docker compose ps -q web >/dev/null 2>&1; then
  log "Running migrations and collectstatic (if available) inside web service..."
  docker compose run --rm web bash -lc "python manage.py migrate --noinput" || log "migrate failed (continuing)"
  docker compose run --rm web bash -lc "python manage.py collectstatic --noinput" || log "collectstatic failed (continuing)"
fi

# Create systemd unit to ensure docker compose is started on boot
SERVICE_PATH="/etc/systemd/system/myapp-docker-compose.service"
cat > "${SERVICE_PATH}" <<'UNIT'
[Unit]
Description=Docker Compose stack for MyApp
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/myapp/repo
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
UNIT

chmod 644 "${SERVICE_PATH}"
systemctl daemon-reload
systemctl enable --now myapp-docker-compose.service || true

# Wait a short while and print container status
sleep 3
log "Provision finished. Containers:"
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}'