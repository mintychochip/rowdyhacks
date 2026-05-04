# Hack the Valley Deployment Guide

## Architecture Overview

Hack the Valley uses a **split deployment**:

| Component | Platform | URL |
|---|---|---|
| **Frontend** | Vercel (auto-deploy from `master`) | Your Vercel project URL |
| **Backend + DB** | DigitalOcean VPS (Docker Compose) | `rowdyhackin.duckdns.org` |

The frontend on Vercel proxies `/api/*` requests to the backend VPS. The backend runs behind nginx with SSL termination on the droplet.

```
User → Vercel (frontend) → /api/* proxy → DO VPS (nginx → FastAPI backend)
                                                        → PostgreSQL
                                                        → Redis
```

---

## Frontend Deployment (Vercel)

The frontend auto-deploys from `master` via Vercel's GitHub integration. No manual steps needed after initial setup.

### Initial Vercel Setup
1. Import the repo on [vercel.com](https://vercel.com)
2. Set the **Root Directory** to `frontend`
3. Set the **Install Command** to `npm install --legacy-peer-deps`
4. Add environment variable: `VITE_API_URL=/api`
5. Configure rewrites/proxy in `vercel.json` to forward `/api/*` to `https://rowdyhackin.duckdns.org/api/*`

### Manual frontend build (local)
```bash
cd frontend
npm install --legacy-peer-deps
npm run build      # output in frontend/dist/
```

---

## Backend Deployment (DigitalOcean VPS)

Ubuntu 22.04 LTS, 2GB RAM minimum. Domain via DuckDNS: `rowdyhackin.duckdns.org`.

### One-Time Setup

```bash
ssh root@your-droplet-ip
```

#### 1. Install Docker (skip if already installed)

```bash
curl -fsSL https://get.docker.com | sh
usermod -aG docker $USER
# Log out and back in for group to take effect
```

#### 2. DuckDNS Setup

Update DuckDNS to point to your droplet IP. Add a cron job to keep it updated:

```bash
# Add to crontab -e:
*/5 * * * * curl -s "https://www.duckdns.org/update?domains=rowdyhackin&token=YOUR_DUCKDNS_TOKEN&ip=" > /dev/null
```

#### 3. Check for port conflicts

Before deploying, check what's using ports 80 and 443 (the nginx container binds to both):

```bash
ss -tlnp | grep -E ':80 |:443 '
```

If something shows up, you have three options:

**A. Stop the existing service** (if you don't need it):
```bash
systemctl stop nginx   # or apache2, caddy, etc.
systemctl disable nginx
systemctl mask nginx   # prevent accidental restart
```

**B. Run Hack the Valley on different ports** — in `docker-compose.yml`, change nginx ports from `"80:80"` / `"443:443"` to something like `"8080:80"` / `"8443:443"`, then use your existing nginx as a reverse proxy.

**C. Skip Hack the Valley's nginx and route through your existing one** — remove the `nginx` and `certbot` services from docker-compose, then add a server block in your existing nginx pointing at `localhost:3000` (frontend) and `localhost:8000` (backend).

#### Reverse proxy with existing nginx (Option C example)

```
# In your existing nginx config (/etc/nginx/sites-enabled/your-domain):
server {
    listen 80;
    server_name hackathon.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

#### 4. Clone and configure

```bash
git clone https://github.com/mintychochip/rowdyhacks.git /home/jlo/rowdyhacks
cd /home/jlo/rowdyhacks

cp .env.example .env
# Generate a real secret key:
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
nano .env  # Fill in SECRET_KEY, POSTGRES_PASSWORD, BASE_URL, etc.
```

#### 5. SSL (skip if using your own reverse proxy)

```bash
./scripts/init-ssl.sh rowdyhackin.duckdns.org admin@your-email.com
# Or for testing / IP-only (self-signed):
./scripts/init-ssl.sh
```

If no certificates exist, the nginx container will auto-generate self-signed certs on startup.

#### 6. Start

```bash
docker compose up -d
docker compose ps        # confirm all services are up
docker compose logs -f backend  # watch for startup errors
```

#### 7. Auto-start on boot

```bash
cp hackverify.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable hackverify
```

### Deploying Updates

**Option A — GitHub Actions (auto-deploy on push to master):**

This is the primary deployment method. On every push to `master`, the `deploy.yml` workflow SSHes into the droplet and redeploys.

Required GitHub secrets (`Settings > Secrets and variables > Actions`):

| Secret | Description |
|---|---|
| `DROPLET_HOST` | Droplet IP or `rowdyhackin.duckdns.org` |
| `DROPLET_USER` | SSH user (e.g. `jlo`) |
| `DROPLET_SSH_KEY` | Private SSH key for the deploy user |
| `SUDO_PASSWORD` | Password for sudo commands (stopping host nginx) |

Generate a deploy key:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/rowdyhacks-deploy -N ""
cat ~/.ssh/rowdyhacks-deploy.pub   # add this to ~/.ssh/authorized_keys on the droplet
cat ~/.ssh/rowdyhacks-deploy       # put this in the DROPLET_SSH_KEY secret
```

**Option B — Manual deploy script (from your local machine):**

```bash
./scripts/deploy.sh jlo@rowdyhackin.duckdns.org
```

### Docker Compose Services

| Service | Image | Port | Depends On |
|---|---|---|---|
| `db` | postgres:15-alpine | 127.0.0.1:5433→5432 | — |
| `redis` | redis:7-alpine | internal | — |
| `backend` | custom (Python 3.11) | 127.0.0.1:8000→8000 | db (healthy), redis (healthy) |
| `frontend` | custom (Node→nginx) | 127.0.0.1:3000→3000 | — |
| `nginx` | nginx:alpine | 80, 443 | backend (healthy), frontend (started) |
| `certbot` | certbot/certbot | — | — |

### Environment Variables

| Variable | Description | Required |
|---|---|---|
| `SECRET_KEY` | JWT signing key (32+ chars) | Yes |
| `POSTGRES_PASSWORD` | Database password | Yes |
| `POSTGRES_USER` | Database user (default: `hackverify`) | No |
| `POSTGRES_DB` | Database name (default: `hackverify`) | No |
| `BASE_URL` | Public URL, e.g. `https://rowdyhackin.duckdns.org` | Yes |
| `LLM_API_KEY` | Anthropic/Poolside API key | Optional |
| `GITHUB_TOKEN` | GitHub PAT for API rate limits | Optional |
| `DISCORD_BOT_TOKEN` | Discord bot token | Optional |

All backend settings use the `HACKVERIFY_` prefix (loaded via pydantic-settings).

### Maintenance

```bash
# View logs
docker compose logs -f

# View specific service
docker compose logs -f backend

# Restart a service
docker compose restart backend

# Backup database
docker compose exec db pg_dump -U hackverify hackverify > backup.sql

# Restore database
docker compose exec -T db psql -U hackverify hackverify < backup.sql

# Check status
docker compose ps

# Health check
curl -s http://localhost:8000/api/monitoring/health | python3 -m json.tool
```

### Troubleshooting

- **Port 80/443 already in use**: See step 3 above — stop existing service, change ports, or use existing nginx as reverse proxy. The deploy workflow automatically stops/masks host nginx.
- **Port 5433 already in use**: Change the host port in docker-compose (`"127.0.0.1:5433:5432"` → `"127.0.0.1:5434:5432"`)
- **SSL certificate errors**: Check `data/certbot/conf/live/` exists; regenerate with `./scripts/init-ssl.sh`. Nginx auto-generates self-signed certs as fallback.
- **Database connection refused**: Wait 10-30s for PostgreSQL to finish initializing, verify `POSTGRES_PASSWORD` matches
- **Backend can't connect to DB**: The `HACKVERIFY_DATABASE_URL` in docker-compose uses host `db` (the compose service name) — don't change it
- **OOM during Docker build**: The 2GB droplet can run out of memory. Builds are staggered (backend first, then frontend) to avoid this. If still failing, add swap: `fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile`
- **Deploy health check times out**: Backend may take up to 60s to start (DB migrations, demo seeding). Check `docker compose logs backend` for errors.
- **DuckDNS not resolving**: Verify the cron job is running (`crontab -l`) and the token is correct. Test with `curl "https://www.duckdns.org/update?domains=rowdyhackin&token=YOUR_TOKEN&ip=&verbose=true"`.
