# AGENTS.md — Hack the Valley Context for AI Agents

## Project Overview

Hack the Valley (HTV) is a hackathon management platform for Toronto's largest student-run hackathon. It handles registration, check-in (QR + Apple/Google Wallet), judging (ELO-based), submission integrity analysis, and a Devpost crawler.

## Deployment Architecture

```
                    ┌──────────────────────┐
                    │   Vercel (Frontend)  │
                    │   React + Vite PWA   │
                    │   Static deploy      │
                    └──────────┬───────────┘
                               │ /api/* proxied
                               ▼
┌──────────────────────────────────────────────────────────┐
│              DigitalOcean VPS (2GB RAM)                   │
│              DuckDNS domain: rowdyhackin.duckdns.org      │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              Nginx (ports 80/443)                    │ │
│  │  SSL termination, rate limiting, reverse proxy       │ │
│  └──────────┬─────────────────────┬────────────────────┘ │
│             │                     │                      │
│  ┌──────────▼──────────┐  ┌──────▼─────────────┐        │
│  │  Backend (8000)     │  │  Frontend (3000)    │        │
│  │  FastAPI + Uvicorn  │  │  nginx serving      │        │
│  │  Python 3.11        │  │  Vite build output  │        │
│  └──────────┬──────────┘  └────────────────────┘        │
│             │                                            │
│  ┌──────────┼────────────────┐                           │
│  │          │                │                           │
│  ▼          ▼                ▼                           │
│  PostgreSQL Redis            Discord Bot                 │
│  (5432)     (6379)           (optional)                  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Frontend Deployment (Vercel)
- Hosted on **Vercel** — auto-deploys from the `master` branch
- Built with React 19, TypeScript, Vite 8, vite-plugin-pwa
- API calls go to `/api/*` which Vercel proxies to the backend VPS
- Source: `frontend/`

### Backend Deployment (DigitalOcean VPS + DuckDNS)
- Hosted on a **DigitalOcean droplet** (Ubuntu 22.04, 2GB RAM)
- Domain: **rowdyhackin.duckdns.org** via DuckDNS dynamic DNS
- Deployed via GitHub Actions (`deploy.yml`) — SSHes into the droplet, pulls latest code, rebuilds Docker containers
- All services run in Docker Compose: PostgreSQL, Redis, FastAPI backend, nginx (SSL termination)
- Backend: Python 3.11, FastAPI, SQLAlchemy 2.0 (async), asyncpg
- Source: `backend/`

## Repository Structure

```
rowdyhacks/
├── AGENTS.md                  # This file — context for AI agents
├── DEPLOY.md                  # Detailed deployment guide
├── README.md                  # Project overview and quick start
├── PROJECT_JOURNAL.md         # Development history and decisions
├── docker-compose.yml         # Production Docker Compose (VPS)
├── hackverify.service         # systemd unit for auto-start on VPS
├── .env.example               # Environment variable template
│
├── .github/workflows/
│   ├── deploy.yml             # CD: auto-deploy backend to VPS on push to master
│   └── ci.yml                 # CI: lint + test on PRs (backend + frontend)
│
├── .pre-commit-config.yaml    # Pre-commit hooks (ruff, eslint)
│
├── backend/
│   ├── Dockerfile             # Python 3.11-slim + Playwright + Chromium
│   ├── requirements.txt       # Pinned Python dependencies
│   ├── ruff.toml              # Ruff linter/formatter config
│   ├── app/
│   │   ├── main.py            # FastAPI entry point, lifespan, router registration
│   │   ├── config.py          # pydantic-settings (HACKVERIFY_ env prefix)
│   │   ├── database.py        # SQLAlchemy async engine + session
│   │   ├── models.py          # All SQLAlchemy ORM models
│   │   ├── cache.py           # Redis + in-memory fallback cache
│   │   ├── analyzer.py        # Submission integrity analysis pipeline
│   │   ├── routes/            # 16 route modules (auth, checks, hackathons, etc.)
│   │   │   ├── monitoring.py  # /api/monitoring/health, /ready, /live, /metrics
│   │   │   ├── auth.py        # JWT auth + OAuth
│   │   │   ├── hackathons.py  # Hackathon CRUD
│   │   │   ├── judging.py     # ELO judging portal
│   │   │   └── ...
│   │   ├── checks/            # 20+ integrity check modules
│   │   ├── crawler/           # Devpost bulk crawler (stealth)
│   │   └── wallet/            # Apple/Google Wallet pass generation
│   └── tests/                 # pytest test suite
│
├── frontend/
│   ├── Dockerfile             # Multi-stage: Node 20 build → nginx serve
│   ├── package.json           # React 19, Chakra UI v3, Vite 8
│   ├── eslint.config.js       # ESLint flat config
│   ├── src/
│   │   ├── pages/             # 25 page components
│   │   ├── components/        # Shared UI components
│   │   └── theme.ts           # Design tokens
│   └── DESIGN.md              # Full design system docs
│
├── nginx/
│   ├── nginx.conf             # SSL, rate limiting, WebSocket, reverse proxy
│   ├── docker-entrypoint.sh   # Auto-generates self-signed certs if missing
│   └── ssl/                   # SSL certificate storage (gitignored)
│
└── scripts/
    ├── deploy.sh              # Manual deploy script (SSH to droplet)
    └── init-ssl.sh            # Let's Encrypt or self-signed cert setup
```

## Key Endpoints

All backend routes are prefixed with `/api/`:

| Endpoint | Description |
|---|---|
| `GET /api/monitoring/health` | Comprehensive health check (DB, Redis, disk) |
| `GET /api/monitoring/ready` | Kubernetes-style readiness probe |
| `GET /api/monitoring/live` | Kubernetes-style liveness probe |
| `GET /api/monitoring/metrics` | Application metrics |
| `POST /api/auth/register` | User registration |
| `POST /api/auth/login` | JWT login |
| `GET /api/hackathons` | List hackathons |
| `POST /api/hackathons` | Create hackathon (organizer) |
| `POST /api/checks/analyze` | Run submission integrity analysis |

## Development

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

### Frontend
```bash
cd frontend
npm install --legacy-peer-deps
npm run dev        # Vite dev server on port 5173
```

### Testing
```bash
cd backend
pytest -q                    # Full test suite
pytest tests/test_health.py  # Health check tests
pytest tests/test_cache.py   # Cache layer tests
```

### Linting
```bash
# Backend (ruff)
cd backend
ruff check --config ruff.toml .
ruff format --config ruff.toml .

# Frontend (eslint)
cd frontend
npm run lint
```

### Pre-commit hooks
Pre-commit is configured with ruff (backend) and eslint (frontend). Install with:
```bash
pip install pre-commit
pre-commit install
```

## Environment Variables

All backend settings use the `HACKVERIFY_` prefix (via pydantic-settings). Key variables:

| Variable | Description | Required |
|---|---|---|
| `SECRET_KEY` | JWT signing key (32+ chars) | Yes |
| `POSTGRES_PASSWORD` | Database password | Yes |
| `HACKVERIFY_REDIS_URL` | Redis connection URL | Auto-set in Docker |
| `BASE_URL` | Public URL for QR codes | Yes |
| `LLM_API_KEY` | Anthropic API key (AI checks) | Optional |
| `GITHUB_TOKEN` | GitHub PAT (rate limits) | Optional |
| `DISCORD_BOT_TOKEN` | Discord bot token | Optional |

## Docker Compose Services

| Service | Image | Port | Healthcheck |
|---|---|---|---|
| `db` | postgres:15-alpine | 127.0.0.1:5433→5432 | `pg_isready` |
| `redis` | redis:7-alpine | internal only | `redis-cli ping` |
| `backend` | custom (Python 3.11) | 127.0.0.1:8000→8000 | `GET /api/monitoring/health` |
| `frontend` | custom (Node→nginx) | 127.0.0.1:3000→3000 | — |
| `nginx` | nginx:alpine | 80, 443 | — |
| `certbot` | certbot/certbot | — | — |

### Service Dependency Chain
```
db (healthy) ──┐
               ├──→ backend (healthy) ──→ nginx
redis (healthy)┘                          ↑
frontend (started) ───────────────────────┘
```

## CI/CD Pipeline

### CI (`.github/workflows/ci.yml`) — runs on PRs and pushes to master
1. **Backend Lint** — ruff check + format verification
2. **Backend Tests** — pytest on Python 3.11
3. **Frontend Lint & Build** — eslint + `npm run build`
4. **Docker Compose Validate** — `docker compose config`

### CD (`.github/workflows/deploy.yml`) — runs on push to master
1. SSH into DigitalOcean droplet
2. Stop host nginx (free port 80)
3. Pull latest code from master
4. Stop all Docker containers (`docker compose down`)
5. Build backend image (heavy — built first to avoid OOM)
6. Build frontend image
7. Start all services (`docker compose up -d`)
8. Health check loop (15 retries × 4s)

## Common Issues

### Deployment failures
- **Port 80 conflict**: Host nginx may conflict with Docker nginx. Deploy script stops/masks host nginx before starting containers.
- **OOM during build**: The 2GB droplet can run out of memory building backend (Playwright+Chromium) and frontend (npm) simultaneously. Builds are staggered sequentially.
- **Health check timeout**: Backend may take up to 30s to start (DB migrations, demo data seeding). The health check retries 15 times.

### Known pre-existing test failures
These tests fail on master and are not regressions:
- `test_judging.py::test_full_judging_flow` — 422 on judging session creation
- `test_oauth.py::test_callback_apple_no_name_fallback` — Apple OAuth callback routing
- `test_routes_dashboard.py::test_dashboard_returns_list` — 422 on dashboard
- `test_routes_dashboard.py::test_create_hackathon_201` — 400 on hackathon creation

## Database

- **Production**: PostgreSQL 15 (via Docker)
- **Tests**: SQLite in-memory (via aiosqlite)
- **ORM**: SQLAlchemy 2.0 async with asyncpg driver
- **Migrations**: Alembic (in `backend/alembic/`)
- Tables auto-create on startup via `Base.metadata.create_all`
