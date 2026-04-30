# HackVerify Deployment Guide

## Single VPS Deployment (Docker Compose)

### Requirements

- Ubuntu 22.04 LTS (or similar)
- 2GB RAM minimum, 4GB recommended
- Docker & Docker Compose installed
- Domain name (optional, for SSL)

### Quick Start

```bash
# 1. Clone and enter directory
cd /opt
sudo git clone https://github.com/mintychochip/rowdyhacks.git
sudo cd rowdyhacks

# 2. Set environment variables
sudo cp .env.example .env
sudo nano .env  # Edit with your settings

# 3. Initialize SSL (self-signed or Let's Encrypt)
# For local testing:
sudo ./scripts/init-ssl.sh

# For production (replace with your domain):
sudo ./scripts/init-ssl.sh hackverify.example.com admin@example.com

# 4. Start services
sudo docker-compose up -d

# 5. Check status
sudo docker-compose ps
sudo docker-compose logs -f backend
```

### Systemd Service (Auto-start on boot)

```bash
# Copy service file
sudo cp hackverify.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable and start
sudo systemctl enable hackverify
sudo systemctl start hackverify

# Check status
sudo systemctl status hackverify
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | JWT signing key (32+ chars) | Yes |
| `POSTGRES_PASSWORD` | Database password | Yes |
| `LLM_API_KEY` | Anthropic/Poolside API key | Optional |
| `GITHUB_TOKEN` | GitHub PAT for API rate limits | Optional |
| `DISCORD_BOT_TOKEN` | Discord bot token | Optional |
| `BASE_URL` | Public URL (for QR codes) | Yes |

### Maintenance

```bash
# View logs
sudo docker-compose logs -f

# Update
sudo docker-compose pull
sudo docker-compose up -d

# Backup database
sudo docker-compose exec db pg_dump -U hackverify hackverify > backup.sql

# Restore database
sudo docker-compose exec -T db psql -U hackverify hackverify < backup.sql
```

### Troubleshooting

- **Port conflicts**: Ensure ports 80, 443, 5432, 6379 are available
- **SSL issues**: Check `data/certbot/conf/live/` for certificates
- **Database connection**: Verify `HACKVERIFY_DATABASE_URL` in .env
