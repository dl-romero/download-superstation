#!/usr/bin/env bash
source "$(dirname "$0")/venv/bin/activate"

# Override any of these with environment variables:
#   DOWNLOAD_PATH  — where completed torrents are saved (default: ~/Downloads/torrents)
#   DATA_PATH      — where .torrent / resume files are stored (default: ~/.torrent-webui)
#   HOST           — bind address (default: 0.0.0.0)
#   PORT           — port (default: 8080)

exec python "$(dirname "$0")/app.py"
