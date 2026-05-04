#!/usr/bin/env bash
# deploy.sh — Manual deployment trigger for Watchtower
#
# Usage:
#   ./scripts/deploy.sh                    # triggers immediate Watchtower check
#
# Note: In normal operation, Watchtower auto-deploys when new images are pushed
# to GHCR. This script is only for manual/emergency deployments.
#
# For first-time setup on VPS:
#   docker compose up -d
#
# To check deployment status:
#   docker compose ps
#   docker compose logs watchtower -f

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

say() { echo -e "${CYAN}==>${NC} $*"; }
ok()  { echo -e "${GREEN}  ✓${NC} $*"; }
warn() { echo -e "${YELLOW}  !${NC} $*"; }
err() { echo -e "${RED}  ✗${NC} $*"; }

say "Triggering Watchtower for immediate deployment check..."

# Check if running locally or needs SSH
if command -v docker &> /dev/null && docker info &> /dev/null; then
    # Docker available locally - assume we're on the VPS
    docker run --rm \
        -v /var/run/docker.sock:/var/run/docker.sock \
        containrrr/watchtower \
        --run-once \
        backend frontend nginx
    ok "Watchtower check triggered locally"
else
    warn "Docker not available locally. Run this script on the VPS:"
    echo "  cd /home/jlo/rowdyhacks && ./scripts/deploy.sh"
    exit 1
fi

say "Deployment triggered. Monitoring containers..."
sleep 5
docker compose ps

say "To watch deployment progress:"
echo "  docker compose logs watchtower -f"
