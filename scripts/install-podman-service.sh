#!/bin/bash
set -euo pipefail

COCKPIT=0

for arg in "$@"; do
  case "$arg" in
    --with-cockpit) COCKPIT=1 ;;
  esac
done

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

if [ "$COCKPIT" -eq 1 ]; then
    echo "[install] building and installing Cockpit plugin..."

    if ! command -v node &>/dev/null; then
        echo "[install] Node.js not found — please install it (e.g. sudo dnf install nodejs) and re-run with --with-cockpit"
        exit 1
    fi

    _CTMP=$(mktemp -d)
    git clone --depth 1 https://github.com/dl-romero/cockpit-download-superstation.git "$_CTMP"
    bash "$_CTMP/install.sh" --user
    rm -rf "$_CTMP"
    echo "[install] Cockpit plugin installed to ~/.local/share/cockpit/cockpit-download-superstation"
fi

IP=$(hostname -I | awk '{print $1}')
echo "[install] done. Web UI: http://${IP}:8080  (default login: admin / admin)"
if [ "$COCKPIT" -eq 1 ]; then
    echo "[install] Cockpit plugin: open Cockpit and look for 'Download Superstation' in the menu"
fi
