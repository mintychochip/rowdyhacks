#!/bin/sh
set -e

CERT_DIR="/etc/nginx/ssl"
LE_DIR="/etc/letsencrypt/live/rowdyhackin.duckdns.org"

mkdir -p "$CERT_DIR"

# Prefer Let's Encrypt certs if available, otherwise generate self-signed
if [ -f "$LE_DIR/fullchain.pem" ] && [ -f "$LE_DIR/privkey.pem" ]; then
    echo "Using Let's Encrypt certificates from $LE_DIR"
    cp "$LE_DIR/fullchain.pem" "$CERT_DIR/fullchain.pem"
    cp "$LE_DIR/privkey.pem" "$CERT_DIR/privkey.pem"
elif [ ! -f "$CERT_DIR/fullchain.pem" ] || [ ! -f "$CERT_DIR/privkey.pem" ]; then
    # Install openssl if not present (nginx:alpine doesn't have it)
    if ! command -v openssl >/dev/null 2>&1; then
        echo "Installing openssl..."
        apk add --no-cache openssl
    fi
    echo "Generating self-signed SSL certificates..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$CERT_DIR/privkey.pem" \
        -out "$CERT_DIR/fullchain.pem" \
        -subj "/CN=localhost" \
        -addext "subjectAltName=DNS:rowdyhackin.duckdns.org,DNS:localhost,IP:127.0.0.1"
    echo "Self-signed certificates generated."
fi

# Reload nginx every 6h to pick up renewed certs
while :; do
    sleep 6h &
    wait $!
    # Refresh Let's Encrypt certs if they've been renewed
    if [ -f "$LE_DIR/fullchain.pem" ] && [ -f "$LE_DIR/privkey.pem" ]; then
        cp "$LE_DIR/fullchain.pem" "$CERT_DIR/fullchain.pem"
        cp "$LE_DIR/privkey.pem" "$CERT_DIR/privkey.pem"
    fi
    nginx -s reload
done &

exec nginx -g "daemon off;"
