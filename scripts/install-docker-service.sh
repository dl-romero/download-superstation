#!/bin/bash
set -euo pipefail

if [ "$EUID" -ne 0 ]; then
    echo "Run as root: sudo bash install-docker-service.sh"
    exit 1
fi

BASE=/opt/download-superstation
SYSTEMD=/etc/systemd/system
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "[install] creating data directories..."
mkdir -p "$BASE/downloads" "$BASE/data" "$BASE/scripts"

echo "[install] copying update script..."
cp "$REPO_DIR/scripts/docker-update.sh" "$BASE/scripts/docker-update.sh"
chmod +x "$BASE/scripts/docker-update.sh"

echo "[install] installing systemd units..."
cp "$REPO_DIR/systemd/docker-download-superstation.service"        "$SYSTEMD/download-superstation.service"
cp "$REPO_DIR/systemd/docker-download-superstation-update.service" "$SYSTEMD/download-superstation-update.service"
cp "$REPO_DIR/systemd/docker-download-superstation-update.timer"   "$SYSTEMD/download-superstation-update.timer"

echo "[install] reloading systemd..."
systemctl daemon-reload

echo "[install] enabling and starting services..."
systemctl enable --now download-superstation.service
systemctl enable --now download-superstation-update.timer

IP=$(hostname -I | awk '{print $1}')
echo "[install] done. Web UI: http://${IP}:8080  (default login: admin / admin)"
