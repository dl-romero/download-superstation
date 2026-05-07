#!/bin/bash
set -euo pipefail

INSTALL_DIR=/opt/torrent-webui
SERVICE=torrent-webui

cd "$INSTALL_DIR"

if [ ! -d ".git" ]; then
    echo "[update] $INSTALL_DIR is not a git repository."
    echo "[update] Re-install via git clone to enable auto-update:"
    echo "[update]   git clone https://github.com/dl-romero/download-superstation.git /opt/torrent-webui"
    exit 1
fi

echo "[update] fetching latest..."
git fetch origin main

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "[update] already up to date."
    exit 0
fi

echo "[update] updating $LOCAL -> $REMOTE..."
git pull origin main

echo "[update] syncing Python dependencies..."
./venv/bin/pip install -q -r requirements.txt

echo "[update] restarting service..."
systemctl restart "$SERVICE"

echo "[update] done."
