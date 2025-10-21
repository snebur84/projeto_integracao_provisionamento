#!/bin/bash
# install SSM agent (cloud-init style) for Ubuntu Jammy
set -euo pipefail

REGION="${region:-us-east-1}"

apt-get update -y
apt-get install -y curl jq ca-certificates gnupg

SSM_DEB_URL="https://s3.${REGION}.amazonaws.com/amazon-ssm-${REGION}/latest/debian_amd64/amazon-ssm-agent.deb"
curl -fsSL "${SSM_DEB_URL}" -o /tmp/amazon-ssm-agent.deb || true

if [ -f /tmp/amazon-ssm-agent.deb ]; then
  dpkg -i /tmp/amazon-ssm-agent.deb || apt-get -f install -y
  systemctl enable --now amazon-ssm-agent || true
else
  apt-get install -y snapd || true
  if command -v snap >/dev/null 2>&1; then
    snap install amazon-ssm-agent --classic || true
    systemctl enable --now snap.amazon-ssm-agent.amazon-ssm-agent.service || true
  fi
fi

exit 0