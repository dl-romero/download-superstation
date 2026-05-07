#!/bin/bash
set -euo pipefail

IMAGE="ghcr.io/dl-romero/download-superstation:latest"

echo "[update] checking for new image..."
OLD_ID=$(docker inspect --format='{{.Id}}' "$IMAGE" 2>/dev/null || echo "none")

docker pull "$IMAGE"

NEW_ID=$(docker inspect --format='{{.Id}}' "$IMAGE")

if [ "$OLD_ID" != "$NEW_ID" ]; then
    echo "[update] new image detected — restarting service..."
    systemctl restart download-superstation.service
    echo "[update] done."
else
    echo "[update] already up to date."
fi
