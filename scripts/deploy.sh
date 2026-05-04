#!/usr/bin/env bash
# deploy.sh — Deploy Hack the Valley via GHCR images
#
# Usage:
#   ./scripts/deploy.sh                    # deploys to host configured below
#   ./scripts/deploy.sh user@1.2.3.4       # deploys to specific host
#
# This script now pulls pre-built images from GitHub Container Registry
# instead of building on the VPS (much faster, no OOM issues)

set -euo pipefail

# ── Configuration ──────────────────────────────────────────
# Change these to match your droplet, or pass host as argument
SSH_HOST="${1:-user@your-droplet-ip}"
APP_DIR="${APP_DIR:-/home/jlo/rowdyhacks}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
# ───────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

say() { echo -e "${CYAN}==>${NC} $*"; }
ok()  { echo -e "${GREEN}  ✓${NC} $*"; }
err() { echo -e "${RED}  ✗${NC} $*"; }

say "Deploying to ${SSH_HOST}..."

# ── 1. Push current branch ──────────────────────────────
say "Pushing latest commits..."
git push
ok "Pushed"

# ── 2. Pull latest code and images ─────────────────────
say "Fetching code and pulling images..."
ssh "$SSH_HOST" "cd ${APP_DIR} && git fetch origin master && git checkout -f origin/master -- . && docker compose -f ${COMPOSE_FILE} pull"
ok "Code updated and images pulled"

# ── 3. Stop and restart ─────────────────────────────────
say "Restarting containers..."
ssh "$SSH_HOST" "cd ${APP_DIR} && docker compose -f ${COMPOSE_FILE} down --timeout 30 && docker compose -f ${COMPOSE_FILE} up -d --remove-orphans"
ok "Containers restarted"

# ── 4. Cleanup old images ───────────────────────────────
say "Pruning old images..."
ssh "$SSH_HOST" "docker image prune -f"
ok "Done"

# ── 5. Health check ─────────────────────────────────────
say "Running health check..."
for i in $(seq 1 10); do
  if ssh "$SSH_HOST" "curl -sf -o /dev/null http://localhost:8000/api/monitoring/health"; then
    ok "Backend healthy"
    break
  fi
  echo "  Waiting... ($i/10)"
  sleep 3
done

say "Deploy complete: https://$(echo "$SSH_HOST" | cut -d@ -f2)"
