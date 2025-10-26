#!/usr/bin/env bash
# Provision startup script for GCE instance (idempotent).
# - Installs Docker and Docker Compose (v2)
# - Clones repo (supports private repo via GITHUB_TOKEN instance metadata)
# - Generates .env from instance metadata if needed
# - Runs docker compose up -d and executes migrations/collectstatic
# - Creates systemd unit to start compose stack on boot
set -euo pipefail
IFS=$'\n\t'

METADATA_BASE="http://metadata.google.internal/computeMetadata/v1/instance/attributes"
get_meta() { curl -sf -H "Metadata-Flavor: Google" "${METADATA_BASE}/$1" || true; }

log() { echo "provision: $*"; }

GITHUB_REPO="$(get_meta GITHUB_REPO || echo 'snebur84/projeto_integracao_provisionamento')"
GITHUB_BRANCH="$(get_meta GITHUB_BRANCH || echo 'main')"
GITHUB_TOKEN="$(get_meta GITHUB_TOKEN || true)"   # may be empty or "true"
WORKDIR="/opt/myapp"
REPO_DIR="${WORKDIR}/repo"

# container defaults (can be overridden by repo .env or metadata)
CONTAINER_IMAGE="$(get_meta CONTAINER_IMAGE || echo 'nginx:stable')"
CONTAINER_PORT="$(get_meta CONTAINER_PORT || echo '80')"

# create workdir
mkdir -p "${WORKDIR}"
chown root:root "${WORKDIR}"
cd "${WORKDIR}"

# Install prerequisites and Docker if missing
if ! command -v docker >/dev/null 2>&1; then
  log "Installing Docker..."
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg lsb-release git || true
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

# Clone repository (authenticated if GITHUB_TOKEN provided)
rm -rf "${REPO_DIR}.tmp" || true
mkdir -p "${REPO_DIR}.tmp"

REPO_URL="https://github.com/${GITHUB_REPO}.git"
if [ -n "${GITHUB_TOKEN:-}" ] && [ "${GITHUB_TOKEN}" != "true" ]; then
  log "Cloning private repo using token (via http.extraHeader)"
  # Use http.extraHeader to avoid exposing token in process arguments
  git -c http.extraHeader="AUTHORIZATION: bearer ${GITHUB_TOKEN}" clone --depth 1 --branch "${GITHUB_BRANCH}" "${REPO_URL}" "${REPO_DIR}.tmp" || {
    log "Authenticated clone failed; trying fallback with token in URL"
    git clone --depth 1 --branch "${GITHUB_BRANCH}" "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPO}.git" "${REPO_DIR}.tmp"
  }
else
  log "Cloning public repo ${REPO_URL} (branch ${GITHUB_BRANCH})"
  git clone --depth 1 --branch "${GITHUB_BRANCH}" "${REPO_URL}" "${REPO_DIR}.tmp" || {
    log "Public clone failed; attempting to download minimal files"
    mkdir -p "${REPO_DIR}.tmp"
    curl -fsSL "https://raw.githubusercontent.com/${GITHUB_REPO}/${GITHUB_BRANCH}/docker-compose.yml" -o "${REPO_DIR}.tmp/docker-compose.yml" || true
    curl -fsSL "https://raw.githubusercontent.com/${GITHUB_REPO}/${GITHUB_BRANCH}/.env.example" -o "${REPO_DIR}.tmp/.env.example" || true
    curl -fsSL "https://raw.githubusercontent.com/${GITHUB_REPO}/${GITHUB_BRANCH}/scripts/provision_ubuntu_full.sh" -o "${REPO_DIR}.tmp/scripts_provision_ubuntu_full.sh" || true
  }
fi

# If clone succeeded, atomically move into place
if [ -d "${REPO_DIR}.tmp" ] && [ "$(ls -A "${REPO_DIR}.tmp")" ]; then
  rm -rf "${REPO_DIR}" || true
  mv "${REPO_DIR}.tmp" "${REPO_DIR}"
  log "Repo ready at ${REPO_DIR}"
else
  log "Repo not available in tmp dir; continuing (may use files already present)"
  rm -rf "${REPO_DIR}.tmp" || true
fi

cd "${REPO_DIR}" || {
  log "Repo dir missing; aborting compose startup"
  exit 0
}

# Generate .env from metadata if not present and if .env.example exists or metadata provided
if [ ! -f ".env" ]; then
  if [ -f ".env.example" ] || [ -n "$(get_meta MYSQL_ROOT_PASSWORD)" ]; then
    log "Generating .env from metadata or .env.example"
    # prefer metadata values, fallback to .env.example values if present
    MYSQL_ROOT_PASSWORD="$(get_meta MYSQL_ROOT_PASSWORD || true)"
    MYSQL_DATABASE="$(get_meta MYSQL_DATABASE || true)"
    MYSQL_USER="$(get_meta MYSQL_USER || true)"
    MYSQL_PASSWORD="$(get_meta MYSQL_PASSWORD || true)"
    MONGO_INITDB_ROOT_USERNAME="$(get_meta MONGO_INITDB_ROOT_USERNAME || true)"
    MONGO_INITDB_ROOT_PASSWORD="$(get_meta MONGO_INITDB_ROOT_PASSWORD || true)"
    DATABASE_URL="$(get_meta DATABASE_URL || true)"
    MONGO_URI="$(get_meta MONGO_URI || true)"
    SECRET_KEY="$(get_meta SECRET_KEY || true)"
    ALLOWED_HOSTS="$(get_meta ALLOWED_HOSTS || '*')"
    DJANGO_SETTINGS_MODULE="$(get_meta DJANGO_SETTINGS_MODULE || true)"

    # If .env.example exists, use it as baseline and replace only keys present in metadata
    if [ -f ".env.example" ]; then
      cp .env.example .env
      [ -n "$MYSQL_ROOT_PASSWORD" ] && sed -i "s/^MYSQL_ROOT_PASSWORD=.*/MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}/" .env || true
      [ -n "$MYSQL_DATABASE" ] && sed -i "s/^MYSQL_DATABASE=.*/MYSQL_DATABASE=${MYSQL_DATABASE}/" .env || true
      [ -n "$MYSQL_USER" ] && sed -i "s/^MYSQL_USER=.*/MYSQL_USER=${MYSQL_USER}/" .env || true
      [ -n "$MYSQL_PASSWORD" ] && sed -i "s/^MYSQL_PASSWORD=.*/MYSQL_PASSWORD=${MYSQL_PASSWORD}/" .env || true
      [ -n "$MONGO_INITDB_ROOT_USERNAME" ] && sed -i "s/^MONGO_INITDB_ROOT_USERNAME=.*/MONGO_INITDB_ROOT_USERNAME=${MONGO_INITDB_ROOT_USERNAME}/" .env || true
      [ -n "$MONGO_INITDB_ROOT_PASSWORD" ] && sed -i "s/^MONGO_INITDB_ROOT_PASSWORD=.*/MONGO_INITDB_ROOT_PASSWORD=${MONGO_INITDB_ROOT_PASSWORD}/" .env || true
      [ -n "$DATABASE_URL" ] && sed -i "s#^DATABASE_URL=.*#DATABASE_URL=${DATABASE_URL}#" .env || true
      [ -n "$MONGO_URI" ] && sed -i "s#^MONGO_URI=.*#MONGO_URI=${MONGO_URI}#" .env || true
      [ -n "$SECRET_KEY" ] && sed -i "s/^SECRET_KEY=.*/SECRET_KEY=${SECRET_KEY}/" .env || true
      [ -n "$ALLOWED_HOSTS" ] && sed -i "s/^ALLOWED_HOSTS=.*/ALLOWED_HOSTS=${ALLOWED_HOSTS}/" .env || true
      [ -n "$DJANGO_SETTINGS_MODULE" ] && sed -i "s/^DJANGO_SETTINGS_MODULE=.*/DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE}/" .env || true
    else
      cat > .env <<EOF
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:-ChangeMeRootPass!}
MYSQL_DATABASE=${MYSQL_DATABASE:-mydb}
MYSQL_USER=${MYSQL_USER:-myuser}
MYSQL_PASSWORD=${MYSQL_PASSWORD:-mypassword}

MONGO_INITDB_ROOT_USERNAME=${MONGO_INITDB_ROOT_USERNAME:-mongoroot}
MONGO_INITDB_ROOT_PASSWORD=${MONGO_INITDB_ROOT_PASSWORD:-mongopass}

DATABASE_URL=${DATABASE_URL:-mysql://myuser:mypassword@db:3306/mydb}
MONGO_URI=${MONGO_URI:-mongodb://mongoroot:mongopass@mongo:27017}
SECRET_KEY=${SECRET_KEY:-replace-with-secret}
ALLOWED_HOSTS=${ALLOWED_HOSTS:-*}
DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-myproject.settings.prod}
EOF
    fi
    log ".env written (permissions restricted)"
    chmod 600 .env || true
  else
    log "No .env.example and no metadata provided — expecting .env to be present in repo"
  fi
else
  log ".env already present, will use it"
fi

# If images are in GCR/Artifact Registry and the VM has gcloud, configure docker auth (optional)
if command -v gcloud >/dev/null 2>&1; then
  # configure-docker is safe if gcloud present and VM SA has permission to read registry
  gcloud auth configure-docker --quiet || true
fi

# Pull images and start stack
log "docker compose pull"
docker compose pull --quiet || true

log "docker compose up -d"
docker compose up -d

# If there is a web service, attempt migrations/collectstatic once
if docker compose ps -q web >/dev/null 2>&1; then
  log "Running migrations and collectstatic"
  docker compose run --rm web bash -lc "python manage.py migrate --noinput" || log "migrate failed (continuing)"
  docker compose run --rm web bash -lc "python manage.py collectstatic --noinput" || log "collectstatic failed (continuing)"
fi

# Create systemd unit to ensure the compose stack is started on boot
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

log "Provision finished. Containers:"
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}'