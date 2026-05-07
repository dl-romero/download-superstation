#!/bin/bash
set -euo pipefail

BASE="$HOME/download-superstation"
SYSTEMD="$HOME/.config/systemd/user"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "[install] creating data directories..."
mkdir -p "$BASE/downloads" "$BASE/data"
mkdir -p "$SYSTEMD"

echo "[install] installing systemd units..."
cp "$REPO_DIR/systemd/podman-download-superstation.service"        "$SYSTEMD/download-superstation.service"
cp "$REPO_DIR/systemd/podman-download-superstation-update.service" "$SYSTEMD/download-superstation-update.service"
cp "$REPO_DIR/systemd/podman-download-superstation-update.timer"   "$SYSTEMD/download-superstation-update.timer"

echo "[install] reloading systemd..."
systemctl --user daemon-reload

echo "[install] enabling linger so the service starts without a login session..."
loginctl enable-linger "$USER"

echo "[install] enabling and starting services..."
systemctl --user enable --now download-superstation.service
systemctl --user enable --now download-superstation-update.timer

IP=$(hostname -I | awk '{print $1}')
echo "[install] done. Web UI: http://${IP}:8080  (default login: admin / admin)"
