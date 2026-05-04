# Hack the Valley - Agent Context

## Quick Facts

| | |
|---|---|
| **Repo** | mintychochip/rowdyhacks |
| **Frontend URL** | https://rowdyhackin.vercel.app |
| **Backend API** | https://rowdyhackin.duckdns.org/api |
| **Status** | Production (with self-signed SSL) |
| **Branding** | "Hack the Valley" |

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

### Check Logs
```bash
ssh jlo@64.23.185.189
docker logs rowdyhacks-backend-1 --tail 50
docker logs rowdyhacks-nginx-1 --tail 50
```

## Known Issues

1. **SSL Warnings:** Using self-signed certs. Browser shows warning but site works.
2. **API Mixed Content:** Frontend (HTTPS) → Backend (HTTPS with self-signed) shows console errors but functions.
3. **Form Labels:** Email/password inputs on auth page lack explicit `<label>` elements.

## File Locations

| Purpose | Path |
|---------|------|
| Theme colors | `frontend/src/theme.ts` |
| API service | `frontend/src/services/api.ts` |
| Nginx config | `nginx/nginx.conf` |
| Docker compose | `docker-compose.yml` |
| Deploy script | `.github/workflows/deploy.yml` |
| SSL init | `scripts/init-ssl.sh` |

## Backend Health Check
```bash
curl https://rowdyhackin.duckdns.org/api/monitoring/health -k
# Should return: {"status":"healthy", ...}
```
