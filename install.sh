#!/bin/sh
set -e

REPO="mintychochip/openhack"
VERSION="latest"
ARCH=$(uname -sm | tr '[:upper:]' '[:lower:]' | sed 's/ /-/')
BINARY="openhack-installer-${ARCH}"
URL="https://github.com/${REPO}/releases/${VERSION}/download/${BINARY}"
CHECKSUM_URL="${URL}.sha256"

# Determine writable directory
if [ -d "$HOME" ] && [ -w "$HOME" ]; then
  WORKDIR="$HOME/.openhack/tmp"
  mkdir -p "$WORKDIR"
else
  WORKDIR="/tmp"
fi

# Download binary + checksum
echo "Downloading OpenHack installer for ${ARCH}..."
curl -sSL "$URL" -o "$WORKDIR/openhack-installer"
curl -sSL "$CHECKSUM_URL" -o "$WORKDIR/openhack-installer.sha256"

# Verify checksum
EXPECTED=$(cat "$WORKDIR/openhack-installer.sha256" | awk '{print $1}')
if command -v sha256sum >/dev/null 2>&1; then
  ACTUAL=$(sha256sum "$WORKDIR/openhack-installer" | awk '{print $1}')
elif command -v shasum >/dev/null 2>&1; then
  ACTUAL=$(shasum -a 256 "$WORKDIR/openhack-installer" | awk '{print $1}')
else
  echo "Error: sha256sum or shasum required for checksum verification" >&2
  exit 1
fi
if [ "$EXPECTED" != "$ACTUAL" ]; then
  echo "Error: checksum mismatch — download may be corrupted" >&2
  exit 1
fi

chmod +x "$WORKDIR/openhack-installer"
exec "$WORKDIR/openhack-installer"
