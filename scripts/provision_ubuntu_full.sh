#!/usr/bin/env bash
# Provision script for a fresh Ubuntu server.
# - installs Docker Engine and docker compose plugin
# - optionally installs Poetry (prompt)
# - creates .env with DJANGO_SUPERUSER_* and DJANGO_ALLOWED_HOSTS
# - runs docker compose build && up -d
#
# Usage:
#   chmod +x scripts/provision_ubuntu_full.sh
#   ./scripts/provision_ubuntu_full.sh
set -euo pipefail

ENV_FILE=".env"
REQUIREMENTS_FILE="requirements.txt"

info(){ echo -e "\033[1;34m[INFO]\033[0m $*"; }
warn(){ echo -e "\033[1;33m[WARN]\033[0m $*"; }
err(){ echo -e "\033[1;31m[ERROR]\033[0m $*" >&2; }

# Ensure running from repo root (script in scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Confirm Ubuntu
if [ -f /etc/os-release ]; then
  . /etc/os-release
  if [[ "${ID,,}" != "ubuntu" && "${ID_LIKE,,}" != *"ubuntu"* && "${NAME,,}" != *"ubuntu"* ]]; then
    warn "This script targets Ubuntu but detected: ${NAME:-unknown}. Continue? [y/N]"
    read -r ok
    [[ "$ok" =~ ^[Yy] ]] || { err "Aborting."; exit 1; }
  fi
fi

# ----- Install Docker Engine and docker compose plugin -----
install_docker() {
  if command -v docker >/dev/null 2>&1; then
    info "Docker already installed."
  else
    info "Installing Docker Engine..."
    sudo apt-get update -y
    sudo apt-get install -y ca-certificates curl gnupg lsb-release apt-transport-https
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io
    info "Docker Engine installed."
  fi

  # docker compose plugin
  if docker compose version >/dev/null 2>&1; then
    info "docker compose plugin available."
  else
    info "Installing docker compose plugin (package docker-compose-plugin) if available..."
    if sudo apt-get install -y docker-compose-plugin >/dev/null 2>&1; then
      info "docker-compose-plugin installed."
    else
      warn "docker-compose-plugin not in apt or failed; attempting pip install docker-compose as fallback."
      sudo apt-get install -y python3-pip
      sudo python3 -m pip install 'docker-compose'
      info "docker-compose (pip) installed as fallback."
    fi
  fi

  # add current user to docker group to allow non-sudo docker (best-effort)
  if ! groups "$USER" | grep -q '\bdocker\b'; then
    read -r -p "Add current user ($USER) to 'docker' group for non-sudo docker usage? [Y/n] " addgrp
    addgrp="${addgrp:-Y}"
    if [[ "$addgrp" =~ ^[Yy] ]]; then
      sudo usermod -aG docker "$USER"
      info "User $USER added to docker group. You may need to log out/in for group membership to apply."
    fi
  fi
}

install_optional_poetry() {
  read -r -p "Install Poetry on host (optional)? [y/N] " do_poetry
  do_poetry="${do_poetry:-N}"
  if [[ "$do_poetry" =~ ^[Yy] ]]; then
    if command -v poetry >/dev/null 2>&1; then
      info "Poetry already installed."
    else
      info "Installing Poetry..."
      curl -sSL https://install.python-poetry.org | python3 -
      export PATH="$HOME/.local/bin:$PATH"
      info "Poetry installed."
    fi
  fi
}

# ----- Compose DJANGO_ALLOWED_HOSTS from local IPs and prompt for superuser -----
compose_env_and_prompt() {
  HOSTS_RAW="$(hostname -I 2>/dev/null || echo "127.0.0.1")"
  HOSTS_COMMA="$(echo "${HOSTS_RAW}" | tr -s ' ' ',' | sed 's/^,//; s/,$//')"
  # ensure localhost and 127.0.0.1 present
  case ",${HOSTS_COMMA}," in
    *,127.0.0.1,*) ;;
    *) HOSTS_COMMA="${HOSTS_COMMA},127.0.0.1" ;;
  esac
  case ",${HOSTS_COMMA}," in
    *,localhost,*) ;;
    *) HOSTS_COMMA="${HOSTS_COMMA},localhost" ;;
  esac
  info "Detected hosts for DJANGO_ALLOWED_HOSTS: ${HOSTS_COMMA}"

  # prompt superuser
  read -r -p "DJANGO_SUPERUSER_USERNAME [admin]: " SU_USER
  SU_USER="${SU_USER:-admin}"
  read -r -p "DJANGO_SUPERUSER_EMAIL [admin@example.com]: " SU_EMAIL
  SU_EMAIL="${SU_EMAIL:-admin@example.com}"
  while true; do
    read -s -r -p "DJANGO_SUPERUSER_PASSWORD (will be stored in .env): " SU_PASS
    echo
    read -s -r -p "Confirm password: " SU_PASS2
    echo
    if [ "$SU_PASS" != "$SU_PASS2" ]; then
      echo "Passwords do not match; try again."
    elif [ -z "$SU_PASS" ]; then
      echo "Password cannot be empty; try again."
    else
      break
    fi
  done

  # create or merge .env
  if [ -f "$ENV_FILE" ]; then
    read -r -p "$ENV_FILE already exists. Overwrite (O) / Merge (M) / Cancel (C)? [O/m/C]: " CHOICE
    CHOICE="${CHOICE:-O}"
    if [[ "$CHOICE" =~ ^[Cc] ]]; then
      err "Cancelled by user."
      exit 1
    fi
  fi

  SECRET="$(python3 - <<PY
import secrets
print(secrets.token_urlsafe(50))
PY
)"

  if [ -f "$ENV_FILE" ] && [[ ! "$CHOICE" =~ ^[Oo] ]]; then
    info "Merging values into existing $ENV_FILE (backup created)."
    cp "$ENV_FILE" "${ENV_FILE}.bak.$(date +%s)"
    replace_or_add() {
      key="$1"; value="$2"
      if grep -qE "^${key}=" "$ENV_FILE"; then
        sed -i -E "s#^${key}=.*#${key}=${value}#g" "$ENV_FILE"
      else
        echo "${key}=${value}" >> "$ENV_FILE"
      fi
    }
    replace_or_add "DJANGO_SECRET_KEY" "${SECRET}"
    replace_or_add "DJANGO_DEBUG" "1"
    replace_or_add "DJANGO_ALLOWED_HOSTS" "${HOSTS_COMMA}"
    replace_or_add "DJANGO_SUPERUSER_USERNAME" "${SU_USER}"
    replace_or_add "DJANGO_SUPERUSER_EMAIL" "${SU_EMAIL}"
    replace_or_add "DJANGO_SUPERUSER_PASSWORD" "${SU_PASS}"
    info "$ENV_FILE updated (backup at ${ENV_FILE}.bak.*)."
  else
    info "Creating $ENV_FILE..."
    cat > "$ENV_FILE" <<ENV
# Generated by provision_ubuntu_full.sh
DJANGO_SECRET_KEY=${SECRET}
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=${HOSTS_COMMA}

DJANGO_SUPERUSER_USERNAME=${SU_USER}
DJANGO_SUPERUSER_EMAIL=${SU_EMAIL}
DJANGO_SUPERUSER_PASSWORD=${SU_PASS}

# MySQL defaults (adjust if needed)
MYSQL_DATABASE=${MYSQL_DATABASE:-provision_db}
MYSQL_USER=${MYSQL_USER:-provision_user}
MYSQL_PASSWORD=${MYSQL_PASSWORD:-provision_pass}
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:-root_pass}
MYSQL_PORT=${MYSQL_PORT:-3306}

# Mongo defaults
MONGODB_PORT=${MONGODB_PORT:-27017}

PROVISION_API_KEY=${PROVISION_API_KEY:-}

OAUTH_ACCESS_TOKEN_EXPIRE=${OAUTH_ACCESS_TOKEN_EXPIRE:-3600}
OAUTH_REFRESH_TOKEN_EXPIRE=${OAUTH_REFRESH_TOKEN_EXPIRE:-2592000}

# Email (dev)
DJANGO_EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=webmaster@localhost
ENV
    info "$ENV_FILE created."
  fi
}

# ----- Detect docker compose command -----
detect_compose() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    echo "docker compose"
  elif command -v docker-compose >/dev/null 2>&1; then
    echo "docker-compose"
  else
    echo ""
  fi
}

# ----- Build and run compose -----
build_and_up() {
  COMPOSE_CMD="$(detect_compose)"
  if [ -z "$COMPOSE_CMD" ]; then
    err "docker compose not found. Aborting."
    exit 1
  fi
  info "Running: $COMPOSE_CMD up -d --build"
  $COMPOSE_CMD up -d --build
}

# ----- Main -----
install_docker
install_optional_poetry
compose_env_and_prompt
build_and_up

info "Done. Run '$COMPOSE_CMD logs -f web' to watch container output and check entrypoint migration/superuser creation."
info "If you added user to 'docker' group, log out/in to apply group membership."