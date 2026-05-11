#!/usr/bin/env bash
# update.sh — One-command update for OpenHack
#
# Usage:
#   ./scripts/update.sh                      # update production stack
#   ./scripts/update.sh --dev                # update dev stack
#   ./scripts/update.sh --skip-pull          # skip git pull (use local code)
#   ./scripts/update.sh --no-migrate         # skip database migrations
#
# This script:
#   1. Pulls latest code from git (unless --skip-pull)
#   2. Pulls/builds latest Docker images
#   3. Runs pending database migrations
#   4. Restarts services with minimal downtime

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

MODE="prod"
SKIP_PULL=false
NO_MIGRATE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dev) MODE="dev"; shift ;;
        --skip-pull) SKIP_PULL=true; shift ;;
        --no-migrate) NO_MIGRATE=true; shift ;;
        -h|--help)
            echo "Usage: $0 [--dev] [--skip-pull] [--no-migrate]"
            echo ""
            echo "Options:"
            echo "  --dev          Update the development stack (docker-compose.dev.yml)"
            echo "  --skip-pull    Skip git pull (use local code only)"
            echo "  --no-migrate   Skip database migrations"
            exit 0
            ;;
        *) err "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ "$MODE" == "dev" ]]; then
    COMPOSE_FILE="docker-compose.dev.yml"
    BACKEND_SERVICE="backend"
else
    COMPOSE_FILE="docker-compose.yml"
    BACKEND_SERVICE="backend"
fi

say "OpenHack Update — mode: ${MODE}"
echo ""

# ---------------------------------------------------------------------------
# 1. Preconditions
# ---------------------------------------------------------------------------
if ! command -v docker &> /dev/null; then
    err "Docker is not installed."
    exit 1
fi

if ! docker info &> /dev/null; then
    err "Docker daemon is not running."
    exit 1
fi

if ! command -v git &> /dev/null; then
    err "Git is not installed."
    exit 1
fi

ok "Docker and Git are available"

# ---------------------------------------------------------------------------
# 2. Git pull
# ---------------------------------------------------------------------------
if [[ "$SKIP_PULL" == false ]]; then
    say "Pulling latest code..."
    git pull --ff-only || {
        err "Git pull failed. Resolve conflicts and re-run, or use --skip-pull."
        exit 1
    }
    ok "Code updated to $(git rev-parse --short HEAD)"
else
    say "Skipping git pull (--skip-pull)"
fi

# ---------------------------------------------------------------------------
# 3. Update Docker images / build
# ---------------------------------------------------------------------------
say "Updating Docker images..."
if [[ "$MODE" == "dev" ]]; then
    docker compose -f "$COMPOSE_FILE" build --pull || warn "Some images could not be pulled; using cached layers"
else
    docker compose -f "$COMPOSE_FILE" pull || warn "Some images could not be pulled; using cached layers"
fi
ok "Images updated"

# ---------------------------------------------------------------------------
# 4. Restart services (rolling)
# ---------------------------------------------------------------------------
say "Restarting services..."
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans
ok "Services restarted"

# ---------------------------------------------------------------------------
# 5. Database migrations
# ---------------------------------------------------------------------------
if [[ "$NO_MIGRATE" == false ]]; then
    say "Running database migrations..."
    sleep 3  # give backend a moment to become healthy

    if docker compose -f "$COMPOSE_FILE" ps "$BACKEND_SERVICE" &> /dev/null; then
        docker compose -f "$COMPOSE_FILE" exec -T "$BACKEND_SERVICE" \
            alembic upgrade head || {
                warn "Migration command failed. You may need to run it manually:"
                echo "  docker compose -f $COMPOSE_FILE exec $BACKEND_SERVICE alembic upgrade head"
                exit 1
            }
        ok "Migrations applied"
    else
        warn "Backend service not found in compose. Skipping migrations."
    fi
else
    say "Skipping migrations (--no-migrate)"
fi

# ---------------------------------------------------------------------------
# 6. Health check
# ---------------------------------------------------------------------------
say "Running health check..."
for i in {1..12}; do
    if curl -sf http://localhost:8000/api/monitoring/health &> /dev/null; then
        ok "Backend is healthy"
        break
    fi
    sleep 2
done

if [[ "$MODE" == "dev" ]]; then
    say "Checking frontend..."
    for i in {1..12}; do
        if curl -sf http://localhost:5173 &> /dev/null; then
            ok "Frontend is responding"
            break
        fi
        sleep 2
    done
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
say "Update complete!"
echo ""
echo "  Backend:  http://localhost:8000"
echo "  Health:   http://localhost:8000/api/monitoring/health"
if [[ "$MODE" == "dev" ]]; then
    echo "  Frontend: http://localhost:5173"
    echo "  API Docs: http://localhost:8000/docs"
fi
echo ""
