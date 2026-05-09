# Download Superstation

A self-hosted torrent management web UI built with Python and Flask, inspired by the look and feel of QNAP Download Station. Runs anywhere Docker runs, or bare-metal on Rocky Linux.

## Features

- Add torrents via `.torrent` file upload (drag & drop) or magnet link
- Per-torrent priority — High, Normal, Low — controls download queue ordering
- Per-file priority within a torrent — skip individual files you don't want
- Pause, resume, and delete torrents (with optional file deletion)
- Automatic seeding after download completes
- Seeding limits — stop at a target ratio or after a set number of minutes
- Live detail panel — General info, Peers, and Trackers tabs update every 2 seconds
- Live progress bars, download/upload speeds, ETA, and share ratio with visual 1:1 indicator
- Disk free space shown in status bar
- Sidebar categories: All, Downloading, Seeding, Completed, Paused
- Sortable table columns and right-click context menu
- Session-based authentication with username/password
- Settings UI — download path, speed limits, active torrent caps, seeding limits, password change
- State persists across restarts (resume data saved every 60 seconds and on shutdown)

---

## Docker

Docker is the recommended deployment method — no dependency installation required.

### Quick Start

```bash
docker run -d \
  --name download-superstation \
  -p 8080:8080 \
  -p 6881:6881/tcp \
  -p 6881:6881/udp \
  -v $(pwd)/downloads:/downloads \
  -v $(pwd)/data:/data \
  ghcr.io/dl-romero/download-superstation:latest
```

Open `http://<your-server-ip>:8080` and sign in with the default credentials:

- **Username:** `admin`
- **Password:** `admin`

Change these immediately in **Settings → Security**.

---

### Docker Compose

Create a `docker-compose.yml`:

```yaml
services:
  download-superstation:
    image: ghcr.io/dl-romero/download-superstation:latest
    container_name: download-superstation
    ports:
      - "8080:8080"
      - "6881:6881/tcp"
      - "6881:6881/udp"
    volumes:
      - ./downloads:/downloads
      - ./data:/data
    environment:
      DOWNLOAD_PATH: /downloads
      DATA_PATH: /data
      PORT: 8080
    restart: unless-stopped
```

Then start it:

```bash
docker compose up -d
```

Or download the included `docker-compose.yml` directly from this repo:

```bash
curl -O https://raw.githubusercontent.com/dl-romero/download-superstation/main/docker-compose.yml
docker compose up -d
```

---

### Available Image Tags

Images are published to the GitHub Container Registry at `ghcr.io/dl-romero/download-superstation`.

| Tag | Description |
|---|---|
| `latest` | Most recent build from `main` |
| `1.0`, `1.0.0` | Specific release versions |

```bash
# Latest
docker pull ghcr.io/dl-romero/download-superstation:latest

# Specific version
docker pull ghcr.io/dl-romero/download-superstation:1.0.0
```

---

### Building from Source

```bash
git clone https://github.com/dl-romero/download-superstation.git
cd download-superstation
docker build -t download-superstation .
docker run -d \
  --name download-superstation \
  -p 8080:8080 \
  -p 6881:6881/tcp \
  -p 6881:6881/udp \
  -v $(pwd)/downloads:/downloads \
  -v $(pwd)/data:/data \
  download-superstation
```

---

### Volumes

| Container path | Purpose |
|---|---|
| `/downloads` | Where downloaded files are saved |
| `/data` | App state: resume files, settings, credentials |

Both should be mounted as persistent volumes. Losing `/data` means losing all torrent state (resume progress, settings, login credentials). Losing `/downloads` means losing the actual downloaded files.

---

### Ports

| Port | Protocol | Purpose |
|---|---|---|
| `8080` | TCP | Web UI |
| `6881` | TCP | BitTorrent peer connections |
| `6881` | UDP | BitTorrent DHT / peer connections |

---

### Environment Variables

All configuration is done via environment variables passed to the container.

| Variable | Default | Description |
|---|---|---|
| `DOWNLOAD_PATH` | `/downloads` | Where new torrents are saved |
| `DATA_PATH` | `/data` | Where state and credentials are stored |
| `HOST` | `0.0.0.0` | Interface to bind to |
| `PORT` | `8080` | Web UI port |

Example with custom port:

```yaml
environment:
  PORT: 9090
ports:
  - "9090:9090"
```

---

### Updating

```bash
docker compose pull
docker compose down
docker compose up -d
```

Your downloads and settings are safe — they live in the mounted volumes, not in the container.

---

### Firewall (Docker host)

If your host has a firewall, open the required ports:

```bash
# firewalld (Rocky Linux / RHEL)
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --permanent --add-port=6881/tcp
sudo firewall-cmd --permanent --add-port=6881/udp
sudo firewall-cmd --reload
```

---

## Running as a Systemd Service

The `systemd/` directory contains unit files for running and auto-updating the container under systemd — for both Docker (system service) and Podman (rootless user service).

### Docker (system service)

The install script copies the unit files, sets up the data directories, and enables the service and auto-update timer.

```bash
git clone https://github.com/dl-romero/download-superstation.git
cd download-superstation
sudo bash scripts/install-docker-service.sh
```

What it installs:

| Unit | Purpose |
|---|---|
| `download-superstation.service` | Runs the container; restarts on failure |
| `download-superstation-update.service` | Pulls the latest image and restarts if it changed |
| `download-superstation-update.timer` | Runs the update check daily at 4 AM |

Common operations:

```bash
sudo systemctl status download-superstation
sudo systemctl restart download-superstation
sudo systemctl reload download-superstation   # restart container in-place
sudo journalctl -fu download-superstation     # follow logs
```

Trigger a manual update check:

```bash
sudo systemctl start download-superstation-update.service
```

Data lives at `/opt/download-superstation/downloads` and `/opt/download-superstation/data`. Edit the service file to change paths or ports:

```bash
sudo systemctl edit download-superstation
```

---

### Podman (rootless user service)

Runs as your own user — no root required after install. The container uses the `io.containers.autoupdate=registry` label so `podman auto-update` can restart it automatically when a new image is available.

```bash
git clone https://github.com/dl-romero/download-superstation.git
cd download-superstation
bash scripts/install-podman-service.sh
```

What it installs (into `~/.config/systemd/user/`):

| Unit | Purpose |
|---|---|
| `download-superstation.service` | Runs the container; restarts on failure |
| `download-superstation-update.service` | Runs `podman auto-update` for this container |
| `download-superstation-update.timer` | Runs the update check daily at 4 AM |

Common operations:

```bash
systemctl --user status download-superstation
systemctl --user restart download-superstation
systemctl --user reload download-superstation   # restart container in-place
journalctl --user -fu download-superstation     # follow logs
```

Trigger a manual update check:

```bash
systemctl --user start download-superstation-update.service
# or directly:
podman auto-update --filter name=download-superstation
```

Data lives at `~/download-superstation/downloads` and `~/download-superstation/data`.

The install script runs `loginctl enable-linger` so the service starts at boot without requiring a login session.

---

## Cockpit Plugin

Download Superstation includes an optional plugin for [Cockpit](https://cockpit-project.org/), the Linux server management web UI. When installed, a **Download Superstation** item appears in Cockpit's navigation menu, giving you full torrent management without opening a separate browser tab.

The plugin communicates with the Download Superstation service running on the same host via `cockpit.http()` (the Cockpit bridge proxy), so no additional firewall ports are needed and CORS is not an issue.

### Requirements

- Cockpit installed and running on the server (`cockpit` package)
- Download Superstation service running on the same host
- Node.js (for the one-time build step)

### Automatic install (with service installer)

Pass `--with-cockpit` to any install script:

```bash
# Docker (system service)
sudo bash scripts/install-docker-service.sh --with-cockpit

# Podman (rootless)
bash scripts/install-podman-service.sh --with-cockpit

# Bare metal
bash install.sh --with-cockpit
```

The flag installs Node.js if missing (Docker/bare-metal scripts), runs `npm ci && npm run build` in the `cockpit/` directory, and copies the built files to the appropriate Cockpit package path:

| Install type | Cockpit package path |
|---|---|
| Docker / bare-metal (system) | `/usr/share/cockpit/download-superstation/` |
| Podman (rootless user) | `~/.local/share/cockpit/download-superstation/` |

### Manual install

```bash
cd cockpit
npm ci
npm run build

# System-wide (requires root)
sudo mkdir -p /usr/share/cockpit/download-superstation
sudo cp -r dist/. /usr/share/cockpit/download-superstation/

# Per-user (no root)
mkdir -p ~/.local/share/cockpit/download-superstation
cp -r dist/. ~/.local/share/cockpit/download-superstation/
```

After copying, refresh Cockpit in your browser (no service restart needed) and the **Download Superstation** item will appear in the left navigation.

### Build from source

```bash
cd cockpit
npm ci        # install dependencies
npm run build # production build to dist/
npm run watch # development: rebuild on file change
```

### How it works

- The plugin is a standard Cockpit package — a directory with `manifest.json`, HTML, CSS, and bundled JavaScript served directly by the Cockpit web server.
- UI is built with React 18 and PatternFly 5 (Cockpit's own UI framework, linked from `../base1/patternfly.css` — no extra download).
- API calls use `cockpit.http()` (bridge-proxied HTTP to `127.0.0.1:<port>`) so the browser never makes direct requests to the backend — no CORS configuration required.
- Session cookie authentication is handled transparently: the plugin logs in once and stores the session in `localStorage`, then injects the `Cookie` header on every subsequent request.
- The service status banner (running / stopped) uses `cockpit.dbus()` to read systemd state in real time and provides one-click Start/Stop.
- The plugin auto-discovers whichever service name is in use — `download-superstation` (Docker/Podman installs) or `torrent-webui` (legacy bare-metal installs).
- If the Cockpit plugin condition in `manifest.json` is not met (neither service unit file exists), Cockpit will not show the plugin in the menu.

### Uninstall

```bash
# System-wide
sudo rm -rf /usr/share/cockpit/download-superstation

# Per-user
rm -rf ~/.local/share/cockpit/download-superstation
```

---

## Manual Installation (Rocky Linux / bare metal)

### Requirements

- Python 3.10+
- Rocky Linux 8/9 (x86_64 / AMD64)

### 1. Clone the repository

```bash
git clone https://github.com/dl-romero/download-superstation.git
cd download-superstation
```

### 2. Run the installer

```bash
bash install.sh
```

This will:
- Install system dependencies via `dnf` (`python3-devel`, `gcc-c++`, `boost-devel`, `openssl-devel`)
- Create a Python virtual environment at `./venv`
- Install `Flask` and `libtorrent` into the venv

### 3. Start the server

```bash
bash run.sh
```

Then open `http://<your-server-ip>:8080` in a browser.

---

## Configuration

All configuration is done via environment variables, both for Docker and bare-metal installs.

| Variable | Default | Description |
|---|---|---|
| `DOWNLOAD_PATH` | `~/Downloads/torrents` | Where downloaded files are saved |
| `DATA_PATH` | `~/.download-superstation` | Where state files are stored |
| `HOST` | `0.0.0.0` | Interface to bind to |
| `PORT` | `8080` | Port to listen on |

**Example — custom paths and port (bare metal):**

```bash
DOWNLOAD_PATH=/mnt/storage/torrents DATA_PATH=/opt/torrent-data PORT=9090 bash run.sh
```

---

## Running as a systemd Service (bare metal)

**Install via `git clone`** so the auto-updater can pull changes later:

```bash
sudo git clone https://github.com/dl-romero/download-superstation.git /opt/torrent-webui
cd /opt/torrent-webui && sudo bash install.sh

# Install the service and auto-update timer
sudo cp torrent-webui.service /etc/systemd/system/
sudo cp systemd/bare-metal-download-superstation-update.service /etc/systemd/system/download-superstation-update.service
sudo cp systemd/bare-metal-download-superstation-update.timer   /etc/systemd/system/download-superstation-update.timer
sudo cp scripts/bare-metal-update.sh /opt/torrent-webui/scripts/bare-metal-update.sh
sudo chmod +x /opt/torrent-webui/scripts/bare-metal-update.sh

sudo systemctl daemon-reload
sudo systemctl enable --now torrent-webui
sudo systemctl enable --now download-superstation-update.timer
```

The timer runs the updater daily at 4 AM. It pulls the latest commit, syncs any new Python dependencies, and restarts the service only when something actually changed.

Trigger a manual update at any time:

```bash
sudo systemctl start download-superstation-update.service
# or directly:
sudo bash /opt/torrent-webui/scripts/bare-metal-update.sh
```

Edit `/etc/systemd/system/torrent-webui.service` to customise the user, port, or paths:

```ini
[Service]
User=youruser
Environment=PORT=8080
Environment=DOWNLOAD_PATH=/mnt/storage/torrents
Environment=DATA_PATH=/home/youruser/.torrent-webui
```

After editing:

```bash
sudo systemctl daemon-reload && sudo systemctl restart torrent-webui
```

---

## Authentication

The web UI requires a username and password. On first run, default credentials are created:

- **Username:** `admin`
- **Password:** `admin`

**Change these immediately** — open ⚙ Settings → Security, enter your current password and a new one, then click **Change Password**.

Credentials are stored as PBKDF2-SHA256 hashes in `$DATA_PATH/auth.json`. Sessions last 30 days.

### Resetting a forgotten password

If you lose access and can no longer log in, delete `auth.json` from your data directory and restart the service. The app will recreate it with the default credentials (`admin` / `admin`) on next startup.

**Docker / Podman:**
```bash
# Find your data volume path, then:
rm /path/to/data/auth.json
# Docker
docker restart download-superstation
# Podman (systemd)
systemctl --user restart download-superstation
```

**Bare metal:**
```bash
rm ~/.download-superstation/auth.json
sudo systemctl restart torrent-webui
```

Change the password again immediately after logging back in.

---

## Usage

### Adding a torrent

Click the **+ Add** button in the toolbar. A modal will appear with two tabs:

- **Torrent File** — drag and drop a `.torrent` file, or click to browse. Optionally set a custom save path.
- **Magnet Link** — paste a `magnet:?xt=urn:btih:…` link. Optionally set a custom save path.

### Torrent actions

| Action | How |
|---|---|
| Pause | Select → **⏸ Pause**, or right-click → Pause |
| Resume | Select → **▶ Resume**, or right-click → Resume |
| Delete (keep files) | Select → **✕ Delete**, or right-click → Remove |
| Delete + files | Right-click → **🗑 Remove + Delete Files** |
| Set priority | Right-click → **▲ High / → Normal / ▼ Low Priority** |
| File priorities | Right-click → **📄 File Priorities…** |

### Torrent priority

Controls which torrents libtorrent downloads first when bandwidth is limited.

| Level | Behaviour |
|---|---|
| **▲ High** | Downloaded before Normal and Low torrents |
| **→ Normal** | Default |
| **▼ Low** | Downloaded last |

### Per-file priority

Right-click → **📄 File Priorities…** to open the file list. Each file has a dropdown:

| Priority | Behaviour |
|---|---|
| **Skip** | File is not downloaded |
| **Low** | Downloaded after Normal and High files |
| **Normal** | Default |
| **High** | Downloaded before Normal and Low files |

Use **All High**, **All Normal**, or **Skip All** to bulk-set all files. Click **Apply** to save.

> File priorities are only available once libtorrent has downloaded the torrent metadata. For magnet links this happens shortly after adding.

### Detail panel

Selecting a torrent reveals a live detail panel at the bottom with three tabs:

- **General** — hash, save path, size, progress, ratio, peers/seeds, priority, creation date, comment
- **Peers** — connected peers with IP, client, speeds, progress, and flags (S=seed, I=interested, C=choked)
- **Trackers** — URL, status message, seed and peer counts from scrape

### Seeding

Torrents seed automatically after completing. To limit seeding, open ⚙ Settings → Seeding Limits:

- **Stop at Ratio** — pauses the torrent when upload ÷ download reaches this value (e.g. `2.0`)
- **Stop after (minutes)** — pauses after this many minutes of seeding (e.g. `1440` for 24 hours)

Set either to `0` to disable that limit.

### Ratio tracking

The **Ratio** column shows a progress bar and colour-coded value indicating upload progress toward a 1:1 ratio:

- **Red bar / red value** — below 1:1 (uploaded less than downloaded)
- **Green bar / green value** — at or above 1:1

To automatically stop seeding once you hit 1:1, set **Stop at Ratio** to `1.0` in Settings → Seeding Limits.

### Sidebar categories

| Category | Shows |
|---|---|
| All Tasks | Every torrent |
| Downloading | Actively downloading |
| Seeding | Completed and seeding |
| Completed | Finished (100%) |
| Paused | Paused torrents |

---

## REST API

The server exposes a JSON REST API. All endpoints except `/login` require an active session (obtained via `POST /api/auth/login`).

### Auth

#### Login
```
POST /api/auth/login
Content-Type: application/json

{ "username": "admin", "password": "admin" }
```
Returns a session cookie on success.

#### Logout
```
POST /api/auth/logout
```

#### Change password
```
POST /api/auth/change-password
Content-Type: application/json

{
  "current_password": "admin",
  "new_password": "newpass",
  "username": "admin"
}
```

---

### Torrents

#### List all torrents
```
GET /api/torrents
```

Returns an array:

```json
[
  {
    "id": "dd8255ecdc7ca55fb0bbf81323d87062db1f6d1c",
    "name": "Big Buck Bunny",
    "size": 276445467,
    "downloaded": 276445467,
    "uploaded": 138222733,
    "progress": 100.0,
    "state": "Seeding",
    "download_speed": 0,
    "upload_speed": 524288,
    "peers": 4,
    "seeds": 12,
    "ratio": 0.500,
    "eta": -1,
    "paused": false,
    "save_path": "/downloads",
    "priority": "normal"
  }
]
```

Possible `state` values: `Downloading`, `Seeding`, `Finished`, `Paused`, `Checking`, `Fetching Metadata`, `Allocating`

#### Add — torrent file
```
POST /api/torrents
Content-Type: multipart/form-data

file=<.torrent file>
save_path=<optional>
```

#### Add — magnet link
```
POST /api/torrents
Content-Type: application/json

{ "magnet": "magnet:?xt=urn:btih:...", "save_path": "/optional/path" }
```

Both return `{ "id": "<info_hash>" }`.

#### Pause / Resume
```
POST /api/torrents/<id>/pause
POST /api/torrents/<id>/resume
```

#### Set torrent priority
```
POST /api/torrents/<id>/priority
Content-Type: application/json

{ "priority": "high" }
```
Valid values: `high`, `normal`, `low`

#### Get file list
```
GET /api/torrents/<id>/files
```

```json
[
  { "index": 0, "path": "Big Buck Bunny/Big Buck Bunny.mp4", "size": 276134947, "priority": "normal" },
  { "index": 1, "path": "Big Buck Bunny/poster.jpg", "size": 310380, "priority": "skip" }
]
```

Returns `404` if metadata is not yet available.

#### Set file priorities
```
POST /api/torrents/<id>/files
Content-Type: application/json

{ "priorities": { "0": "high", "1": "skip", "2": "normal" } }
```
Valid values: `skip`, `low`, `normal`, `high`

#### Torrent detail (peers + trackers)
```
GET /api/torrents/<id>/detail
```

```json
{
  "general": {
    "hash": "dd8255ecdc7ca55fb0bbf81323d87062db1f6d1c",
    "comment": "",
    "created_by": "uTorrent/3310",
    "creation_date": 1234567890,
    "piece_length": 262144,
    "num_files": 3
  },
  "peers": [
    { "ip": "1.2.3.4:51413", "client": "qBittorrent", "down_speed": 102400, "up_speed": 0, "progress": 85.2, "flags": "SI" }
  ],
  "trackers": [
    { "url": "udp://tracker.opentrackr.org:1337", "status": "Working", "seeds": 42, "peers": 120 }
  ]
}
```

#### Remove
```
DELETE /api/torrents/<id>
DELETE /api/torrents/<id>?delete_files=true
```

---

### Stats
```
GET /api/stats
```

```json
{
  "download_speed": 1048576,
  "upload_speed": 262144,
  "count": 3,
  "disk_free": 107374182400,
  "disk_total": 994662584320
}
```

---

### Settings
```
GET  /api/settings
POST /api/settings
```

```json
{
  "download_path": "/downloads",
  "max_download_speed": 0,
  "max_upload_speed": 0,
  "max_active_downloads": 0,
  "max_active_seeds": 0,
  "seed_ratio_limit": 0.0,
  "seed_time_limit": 0
}
```

Speed values are in **KB/s** (`0` = unlimited). Active limits are counts (`0` = unlimited). `seed_ratio_limit` is a float (`0` = disabled). `seed_time_limit` is minutes (`0` = disabled).

---

## Data Storage

| Path | Contents |
|---|---|
| `$DATA_PATH/<hash>.torrent` | Original `.torrent` file |
| `$DATA_PATH/<hash>.resume` | libtorrent fast-resume data |
| `$DATA_PATH/meta.json` | Torrent list with save paths and priorities |
| `$DATA_PATH/settings.json` | App settings |
| `$DATA_PATH/auth.json` | Hashed credentials |
| `$DATA_PATH/secret.key` | Flask session signing key |

Resume data is flushed every 60 seconds and on clean shutdown (SIGINT/SIGTERM). If the process is killed hard, libtorrent will re-check files on next startup.

---

## Releasing a New Version

Tag the commit you want to release with a semver tag. The GitHub Actions workflow will automatically build the Docker image, push it to GHCR with the version tag, and create a GitHub Release.

```bash
git tag v1.0.0
git push origin v1.0.0
```

This produces:
- `ghcr.io/dl-romero/download-superstation:1.0.0`
- `ghcr.io/dl-romero/download-superstation:1.0`
- `ghcr.io/dl-romero/download-superstation:latest`
- A GitHub Release at `https://github.com/dl-romero/download-superstation/releases/tag/v1.0.0`

---

## License

MIT
