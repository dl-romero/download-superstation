#!/usr/bin/env bash
set -e

echo "=== Download Superstation installer (Rocky Linux / x86_64) ==="

# System deps (libtorrent has a C extension that needs these)
sudo dnf install -y python3 python3-pip python3-devel gcc-c++ boost-devel openssl-devel

# Create venv
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=== Installation complete ==="
echo "Run with:  ./run.sh"
echo "Or:        source venv/bin/activate && python app.py"
