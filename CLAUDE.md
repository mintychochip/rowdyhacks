# OpenHack - Agent Context

## Quick Facts

| | |
|---|---|
| **Repo** | mintychochip/openhack |
| **Frontend URL** | https://localhost:5173 |
| **Backend API** | https://localhost/api |
| **Status** | Production (Let's Encrypt SSL) |
| **Branding** | "OpenHack" |

## Tech Stack

- **Frontend:** React + Vite + TypeScript, deployed on Vercel
- **Backend:** FastAPI + SQLAlchemy + PostgreSQL, deployed on DigitalOcean droplet (64.23.185.189)
- **Auth:** OAuth (Google, GitHub, Discord) + JWT
- **Infra:** Docker Compose (nginx, backend, frontend container, PostgreSQL, Redis)

## Design System

```typescript
// Primary colors
PAGE_BG = '#0f172a'      // Deep Navy background
PRIMARY = '#2563eb'       // Electric Blue (buttons, accents)
CYAN = '#06b6d4'          // Cyan for gradients
TEXT_PRIMARY = '#f1f5f9' // White text

// Typography
Font: Inter (body), JetBrains Mono (monospace/data)
```

## Common Tasks

### Deploy Frontend
```bash
cd frontend
vercel --prod
```

### Deploy Backend
Push to master triggers GitHub Actions deploy to DigitalOcean droplet.

### Update Server (Self-Hosted)
```bash
./scripts/update.sh           # production
./scripts/update.sh --dev     # development stack
```

### Check Logs
```bash
ssh jlo@64.23.185.189
docker logs openhack-backend-1 --tail 50
docker logs openhack-nginx-1 --tail 50
```

## Known Issues

1. **Form Labels:** Email/password inputs on auth page lack explicit `<label>` elements.

## File Locations

| Purpose | Path |
|---------|------|
| Theme colors | `frontend/src/theme.ts` |
| API service | `frontend/src/services/api.ts` |
| Nginx config | `nginx/nginx.conf` |
| Docker compose | `docker-compose.yml` |
| Deploy script | `.github/workflows/deploy.yml` |
| SSL setup | `nginx/docker-entrypoint.sh` |
| Update script | `scripts/update.sh` |
| Dev start script | `scripts/dev.sh` |

## Backend API Modules

| Feature | Service | Routes | Tests |
|---------|---------|--------|-------|
| Teams | `app/services/team_service.py` | `app/routes/teams.py` | `tests/routes/test_teams.py` |
| Workshops | `app/services/workshop_service.py` | `app/routes/workshops.py` | `tests/routes/test_workshops.py` |
| Sponsors | `app/services/sponsor_service.py` | `app/routes/sponsors.py` | `tests/routes/test_sponsors.py` |
| Prizes | `app/services/prize_service.py` | `app/routes/prizes.py` | `tests/routes/test_prizes.py` |
| Help Queue | `app/services/help_request_service.py` | `app/routes/help_requests.py` | `tests/routes/test_help_requests.py` |
| Backup/Restore | `app/services/backup_service.py` | `app/routes/backup.py` | `tests/routes/test_backup.py` |
| Plugin Registry | `app/services/plugin_service.py` | `app/routes/plugins.py` | `tests/routes/test_plugins.py` |
| Monitoring | — | `app/routes/monitoring.py` | `tests/routes/test_monitoring.py` |

## Backend Health Check
```bash
curl https://localhost/api/monitoring/health
# Should return: {"status":"healthy", ...}
```
