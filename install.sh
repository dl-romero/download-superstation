#!/usr/bin/env bash
set -e

COCKPIT=0

for arg in "$@"; do
  case "$arg" in
    --with-cockpit) COCKPIT=1 ;;
  esac
done

echo "=== Download Superstation installer (Rocky Linux / x86_64) ==="

# System deps (libtorrent has a C extension that needs these)
sudo dnf install -y python3 python3-pip python3-devel gcc-c++ boost-devel openssl-devel

# Create venv
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

if [ "$COCKPIT" -eq 1 ]; then
  echo ""
  echo "=== Installing Cockpit plugin ==="

  # Install Node.js if not present
  if ! command -v node &>/dev/null; then
    sudo dnf install -y nodejs
  fi

  _CTMP=$(mktemp -d)
  git clone --depth 1 https://github.com/dl-romero/cockpit-download-superstation.git "$_CTMP"
  sudo bash "$_CTMP/install.sh"
  rm -rf "$_CTMP"
  echo "=== Cockpit plugin installed to /usr/share/cockpit/cockpit-download-superstation ==="
fi

echo ""
echo "=== Installation complete ==="
echo "Run with:  ./run.sh"
echo "Or:        source venv/bin/activate && python app.py"
if [ "$COCKPIT" -eq 1 ]; then
  echo "Cockpit:   open Cockpit and look for 'Download Superstation' in the menu"
fi
