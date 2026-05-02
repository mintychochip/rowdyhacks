#!/usr/bin/env bash
# deploy.sh — Deploy RowdyHacks to a Digital Ocean droplet
#
# Usage:
#   ./scripts/deploy.sh                    # deploys to host configured below
#   ./scripts/deploy.sh user@1.2.3.4       # deploys to specific host
#
# First time: set your droplet's host/ip below or pass it as an argument.

set -euo pipefail

# ── Configuration ──────────────────────────────────────────
# Change these to match your droplet, or pass host as argument
SSH_HOST="${1:-user@your-droplet-ip}"
APP_DIR="${APP_DIR:-/opt/rowdyhacks}"
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

# ── 2. Pull on droplet ──────────────────────────────────
say "Fetching and resetting to latest..."
ssh "$SSH_HOST" "cd ${APP_DIR} && git fetch origin master && git checkout -f origin/master -- . && git clean -fd"
ok "Code updated"

# ── 3. Rebuild & restart ────────────────────────────────
say "Rebuilding containers..."
ssh "$SSH_HOST" "cd ${APP_DIR} && docker compose -f ${COMPOSE_FILE} up -d --build && docker compose -f ${COMPOSE_FILE} restart nginx"
ok "Containers restarted"

# ── 4. Cleanup old images ───────────────────────────────
say "Pruning old images..."
ssh "$SSH_HOST" "docker image prune -f"
ok "Done"

# ── 5. Quick health check ───────────────────────────────
say "Running health check..."
sleep 3
if ssh "$SSH_HOST" "curl -sf -o /dev/null http://localhost:8000/health"; then
  ok "Backend healthy"
else
  err "Backend health check failed — check logs: ssh ${SSH_HOST} 'cd ${APP_DIR} && docker compose logs backend'"
fi

say "Deploy complete: https://$(echo "$SSH_HOST" | cut -d@ -f2)"
