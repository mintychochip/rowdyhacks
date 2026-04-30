#!/bin/bash
# Initialize SSL certificates with Let's Encrypt

set -e

DOMAIN=${1:-"localhost"}
EMAIL=${2:-"admin@example.com"}

if [ "$DOMAIN" = "localhost" ]; then
    echo "Creating self-signed certificate for local development..."
    mkdir -p data/certbot/conf/live/localhost
    openssl req -x509 -nodes -newkey rsa:4096 -days 365 \
        -keyout data/certbot/conf/live/localhost/privkey.pem \
        -out data/certbot/conf/live/localhost/fullchain.pem \
        -subj "/CN=localhost"
    echo "Self-signed certificate created."
    exit 0
fi

echo "Obtaining SSL certificate for $DOMAIN..."

# Create directories
mkdir -p data/certbot/conf data/certbot/www

# Stop nginx if running
docker-compose stop nginx 2>/dev/null || true

# Obtain certificate
docker run -it --rm \
    -v "$(pwd)/data/certbot/conf:/etc/letsencrypt" \
    -v "$(pwd)/data/certbot/www:/var/www/certbot" \
    -p 80:80 \
    certbot/certbot certonly \
    --standalone \
    --preferred-challenges http \
    -d "$DOMAIN" \
    --agree-tos \
    --email "$EMAIL" \
    --no-eff-email

echo "SSL certificate obtained for $DOMAIN"
