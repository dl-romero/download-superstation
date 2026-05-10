#!/usr/bin/env bash
set -e

COCKPIT=0
COCKPIT_USER=0

for arg in "$@"; do
  case "$arg" in
    --with-cockpit)      COCKPIT=1 ;;
    --with-cockpit-user) COCKPIT=1; COCKPIT_USER=1 ;;
  esac
done

echo "=== Download Superstation installer ==="

if ! command -v python3 &>/dev/null; then
  echo "python3 not found. Install it first (e.g. sudo dnf install -y python3 python3-pip)"
  exit 1
fi

# Create venv and install dependencies.
# libtorrent ships a manylinux wheel on PyPI — no C extension build tools required.
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

if [ "$COCKPIT" -eq 1 ]; then
  echo ""
  echo "=== Installing Cockpit plugin ==="

  if ! command -v node &>/dev/null; then
    echo "Node.js not found. Install it first (e.g. sudo dnf install -y nodejs)"
    exit 1
  fi

  _CTMP=$(mktemp -d)
  git clone --depth 1 https://github.com/dl-romero/cockpit-download-superstation.git "$_CTMP"
  if [ "$COCKPIT_USER" -eq 1 ]; then
    bash "$_CTMP/install.sh" --user
    echo "=== Cockpit plugin installed to ~/.local/share/cockpit/cockpit-download-superstation ==="
  else
    sudo bash "$_CTMP/install.sh"
    echo "=== Cockpit plugin installed to /usr/share/cockpit/cockpit-download-superstation ==="
  fi
  rm -rf "$_CTMP"
fi

echo ""
echo "=== Installation complete ==="
echo "Run with:  ./run.sh"
echo "Or:        source venv/bin/activate && python app.py"
if [ "$COCKPIT" -eq 1 ]; then
  echo "Cockpit:   open Cockpit and look for 'Download Superstation' in the menu"
fi
