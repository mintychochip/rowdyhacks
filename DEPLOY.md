# RowdyHacks Deployment Guide

## Digital Ocean Droplet Setup

Ubuntu 22.04 LTS, 2GB RAM minimum.

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

#### 2. Check for conflicts with what's already running

Before deploying, check what's using ports 80 and 443 (the nginx container binds to both):

```bash
# See if anything is already on ports 80 or 443
ss -tlnp | grep -E ':80 |:443 '
```

If something shows up, you have three options:

**A. Stop the existing service** (if you don't need it):
```bash
systemctl stop nginx   # or apache2, caddy, etc.
systemctl disable nginx
```

**B. Run RowdyHacks on different ports** — in `docker-compose.yml`, change nginx ports from `"80:80"` / `"443:443"` to something like `"8080:80"` / `"8443:443"`, then use your existing nginx as a reverse proxy (see below).

**C. Skip RowdyHacks' nginx and route through your existing one** — remove the `nginx` and `certbot` services from docker-compose, then add a server block in your existing nginx pointing at `localhost:3000` (frontend) and `localhost:8000` (backend).

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

You'll also need to remove the `nginx` and `certbot` services from `docker-compose.yml` (or comment them out), then let your existing nginx handle SSL via certbot.

#### 3. Clone and configure

```bash
mkdir -p /opt
git clone https://github.com/mintychochip/rowdyhacks.git /opt/rowdyhacks
cd /opt/rowdyhacks

cp .env.example .env
# Generate a real secret key:
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
nano .env  # Fill in SECRET_KEY, POSTGRES_PASSWORD, BASE_URL, etc.
```

#### 4. SSL (skip if using your own reverse proxy)

```bash
./scripts/init-ssl.sh your-domain.com admin@your-domain.com
# Or for testing / IP-only:
./scripts/init-ssl.sh
```

#### 5. Start

```bash
docker compose up -d
docker compose ps        # confirm all services are up
docker compose logs -f backend  # watch for startup errors
```

#### 6. Auto-start on boot

```bash
cp hackverify.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable hackverify
```

### Deploying Updates

**Option A — Deploy script (from your local machine):**

Edit `scripts/deploy.sh` with your droplet address, then:

```bash
./scripts/deploy.sh
```

Or pass the host directly:

```bash
./scripts/deploy.sh root@your-droplet-ip
```

**Option B — GitHub Actions (auto-deploy on push to master):**

Set these secrets in your GitHub repo (`Settings > Secrets and variables > Actions`):

| Secret | Description |
|---|---|
| `DROPLET_HOST` | Your droplet's IP or hostname |
| `DROPLET_USER` | SSH user (e.g. `root`) |
| `DROPLET_SSH_KEY` | Private SSH key |

Generate a deploy key:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/rowdyhacks-deploy -N ""
cat ~/.ssh/rowdyhacks-deploy.pub   # add this to ~/.ssh/authorized_keys on the droplet
cat ~/.ssh/rowdyhacks-deploy       # put this in the DROPLET_SSH_KEY secret
```

### Environment Variables

| Variable | Description | Required |
|---|---|---|
| `SECRET_KEY` | JWT signing key (32+ chars) | Yes |
| `POSTGRES_PASSWORD` | Database password | Yes |
| `POSTGRES_USER` | Database user (default: `hackverify`) | No |
| `POSTGRES_DB` | Database name (default: `hackverify`) | No |
| `LLM_API_KEY` | Anthropic/Poolside API key | Optional |
| `GITHUB_TOKEN` | GitHub PAT for API rate limits | Optional |
| `DISCORD_BOT_TOKEN` | Discord bot token | Optional |
| `BASE_URL` | Public URL (for QR codes) | Yes |

All backend settings use the `HACKVERIFY_` prefix.

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
```

### Troubleshooting

- **Port 80/443 already in use**: See step 2 above — stop existing service, change ports, or use existing nginx as reverse proxy
- **Port 5433 already in use**: Change the host port in docker-compose (`"127.0.0.1:5433:5432"` → `"127.0.0.1:5434:5432"`)
- **SSL certificate errors**: Check `data/certbot/conf/live/` exists; regenerate with `./scripts/init-ssl.sh`
- **Database connection refused**: Wait 10s for PostgreSQL to finish initializing, verify `POSTGRES_PASSWORD` matches
- **Backend can't connect to DB**: The `HACKVERIFY_DATABASE_URL` in docker-compose uses host `db` (the compose service name) — don't change it
