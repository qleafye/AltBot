#!/usr/bin/env bash
# Simple deployment helper for Timeweb (or any Ubuntu VM)
# Usage on the server:
#   sudo bash scripts/deploy_timeweb.sh /path/to/your/repo
# This script assumes you have the repo cloned at the given path.

set -euo pipefail
REPO_PATH=${1:-/opt/altbot}
COMPOSE_FILE=${2:-docker-compose.prod.yml}

echo "Deploying AltBot from: ${REPO_PATH} using compose file: ${COMPOSE_FILE}"

# Install Docker & Docker Compose plugin on Debian/Ubuntu
if ! command -v docker >/dev/null 2>&1; then
  echo "Installing Docker..."
  apt-get update
  apt-get install -y ca-certificates curl gnupg lsb-release
  mkdir -p /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo "\n""deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable""\n" | tee /etc/apt/sources.list.d/docker.list >/dev/null
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  systemctl enable --now docker
fi

# Ensure repo exists
if [ ! -d "$REPO_PATH" ]; then
  echo "Repository path not found: $REPO_PATH"
  exit 2
fi
cd "$REPO_PATH"

# Ensure .env exists
if [ ! -f .env ]; then
  echo ".env not found in $REPO_PATH — copying from .env.example"
  if [ -f .env.example ]; then
    cp .env.example .env
    echo "Please edit .env file and fill secrets (POSTGRES_PASSWORD, BOT tokens). Exiting." && exit 1
  else
    echo ".env.example not found — create .env manually. Exiting." && exit 1
  fi
fi

# Build and start containers
docker compose -f "$COMPOSE_FILE" pull || true
docker compose -f "$COMPOSE_FILE" build --pull
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

echo "Deployment complete. Run 'docker compose -f $COMPOSE_FILE ps' to check containers."