#!/bin/sh
set -e

# Generate self-signed SSL certificates if they don't exist
if [ ! -f /etc/nginx/ssl/fullchain.pem ] || [ ! -f /etc/nginx/ssl/privkey.pem ]; then
    echo "Generating self-signed SSL certificates..."
    mkdir -p /etc/nginx/ssl
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/privkey.pem \
        -out /etc/nginx/ssl/fullchain.pem \
        -subj "/CN=localhost" \
        -addext "subjectAltName=DNS:rowdyhackin.duckdns.org,DNS:localhost,IP:127.0.0.1"
    echo "Self-signed certificates generated."
fi

# Start nginx with auto-reload
while :; do
    sleep 6h &
    wait $!
    nginx -s reload
done &

exec nginx -g "daemon off;"
