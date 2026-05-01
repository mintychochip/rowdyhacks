# RowdyHacks Deployment Guide

## Digital Ocean Droplet Setup

### One-Time Setup

Start with a fresh Ubuntu droplet (22.04 LTS, 2GB RAM minimum).

```bash
# SSH into the droplet
ssh root@your-droplet-ip

# Install Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker $USER
# Log out and back in for group to take effect

# Clone the repo
mkdir -p /opt
git clone https://github.com/mintychochip/rowdyhacks.git /opt/rowdyhacks
cd /opt/rowdyhacks

# Configure environment
cp .env.example .env
nano .env  # Fill in SECRET_KEY, POSTGRES_PASSWORD, BASE_URL, etc.

# Set up SSL
./scripts/init-ssl.sh your-domain.com admin@your-domain.com
# Or for IP-only / testing:
./scripts/init-ssl.sh

# First start
docker compose up -d

# Auto-start on boot
cp hackverify.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable hackverify
```

### Deploying Updates

**Option A — Deploy script (from your local machine):**

Edit `scripts/deploy.sh` and change `SSH_HOST` to your droplet's address, then:

```bash
./scripts/deploy.sh
```

Or pass the host directly:

```bash
./scripts/deploy.sh root@your-droplet-ip
```

**Option B — GitHub Actions (auto-deploy on push to master):**

Set these secrets in your GitHub repo (Settings > Secrets and variables > Actions):

| Secret | Description |
|---|---|
| `DROPLET_HOST` | Your droplet's IP or hostname |
| `DROPLET_USER` | SSH user (e.g. `root`) |
| `DROPLET_SSH_KEY` | Private SSH key (generate with `ssh-keygen -t ed25519`) |

Then add the corresponding public key to the droplet:

```bash
# On the droplet (as the deploy user):
echo "ssh-ed25519 AAAAC3...your-public-key" >> ~/.ssh/authorized_keys
```

After that, every push to `master` deploys automatically.

### Environment Variables

| Variable | Description | Required |
|---|---|---|
| `SECRET_KEY` | JWT signing key (32+ chars) | Yes |
| `POSTGRES_PASSWORD` | Database password | Yes |
| `LLM_API_KEY` | Anthropic/Poolside API key | Optional |
| `GITHUB_TOKEN` | GitHub PAT for API rate limits | Optional |
| `DISCORD_BOT_TOKEN` | Discord bot token | Optional |
| `BASE_URL` | Public URL (for QR codes) | Yes |

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

- **Port conflicts**: Ensure ports 80, 443 are available (stop any existing nginx/apache)
- **SSL issues**: Check `data/certbot/conf/live/` for certificates
- **Database connection**: Verify `HACKVERIFY_DATABASE_URL` in `.env`
- **Deploy health check fails**: `docker compose logs backend` on the droplet
