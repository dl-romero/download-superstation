# Download Superstation

A self-hosted torrent management web UI built with Python and Flask, inspired by the look and feel of QNAP Download Station. Runs on Rocky Linux (and any modern Linux with Python 3.10+).

## Features

- Add torrents via `.torrent` file upload (drag & drop) or magnet link
- Per-torrent priority — High, Normal, Low — controls download queue ordering
- Per-file priority within a torrent — Skip individual files you don't want
- Pause, resume, and delete torrents (with optional file deletion)
- Automatic seeding after download completes
- Live progress bars, download/upload speeds, ETA, and share ratio — updates every 2 seconds
- Sidebar categories: All, Downloading, Seeding, Completed, Paused
- Sortable table columns
- Right-click context menu for quick actions
- State persists across restarts (resume data saved every 60 seconds and on shutdown)
- Custom download path per torrent (optional)
- systemd unit included for running as a service

---

## Requirements

- Python 3.10+
- Rocky Linux 8/9 (or any Linux with x86_64 / AMD64)
- `libtorrent-rasterbar` (installed via pip)

---

## Installation

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

All configuration is done via environment variables. Set them before running, or export them in your shell.

| Variable | Default | Description |
|---|---|---|
| `DOWNLOAD_PATH` | `~/Downloads/torrents` | Where downloaded files are saved |
| `DATA_PATH` | `~/.torrent-webui` | Where `.torrent` files and resume data are stored |
| `HOST` | `0.0.0.0` | Interface to bind to |
| `PORT` | `8080` | Port to listen on |

**Example — custom paths and port:**

```bash
DOWNLOAD_PATH=/mnt/storage/torrents DATA_PATH=/opt/torrent-data PORT=9090 bash run.sh
```

---

## Running as a systemd Service

A systemd unit file is included. To install it:

### 1. Copy the app to a permanent location

```bash
sudo cp -r . /opt/torrent-webui
```

### 2. Run the installer from the new location

```bash
cd /opt/torrent-webui && sudo bash install.sh
```

### 3. Install and enable the service

```bash
# Edit the unit file first if you need a different user
sudo cp torrent-webui.service /etc/systemd/system/torrent-webui.service

sudo systemctl daemon-reload
sudo systemctl enable torrent-webui
sudo systemctl start torrent-webui
```

### 4. Check status

```bash
sudo systemctl status torrent-webui
sudo journalctl -u torrent-webui -f
```

### Customizing the service

Edit `/etc/systemd/system/torrent-webui.service` to change the user, port, or paths:

```ini
[Service]
User=youruser
Environment=PORT=8080
Environment=DOWNLOAD_PATH=/mnt/storage/torrents
Environment=DATA_PATH=/home/youruser/.torrent-webui
```

After editing, reload and restart:

```bash
sudo systemctl daemon-reload && sudo systemctl restart torrent-webui
```

---

## Usage

### Adding a torrent

Click the **+ Add** button in the toolbar. A modal will appear with two tabs:

**Torrent File tab**
- Drag and drop a `.torrent` file onto the drop zone, or click to browse
- Optionally specify a custom save directory
- Click **Add**

**Magnet Link tab**
- Paste a `magnet:?xt=urn:btih:…` link
- Optionally specify a custom save directory
- Click **Add**

### Torrent actions

| Action | How |
|---|---|
| Pause | Select torrent(s) → **⏸ Pause** button, or right-click → Pause |
| Resume | Select torrent(s) → **▶ Resume** button, or right-click → Resume |
| Delete (keep files) | Select torrent(s) → **✕ Delete** button, or right-click → Remove |
| Delete + files | Right-click → **🗑 Remove + Delete Files** |
| Set priority | Right-click → **▲ High / → Normal / ▼ Low Priority** |
| File priorities | Right-click → **📄 File Priorities…** |

### Setting torrent priority

Right-click any torrent and choose a priority level. Priority affects which torrents libtorrent downloads first when bandwidth is limited.

| Level | Behavior |
|---|---|
| **▲ High** | Downloaded before Normal and Low torrents |
| **→ Normal** | Default |
| **▼ Low** | Downloaded last; Normal and High go first |

The Priority column in the table shows the current level for each torrent and is sortable.

### Setting per-file priority

Right-click a torrent → **📄 File Priorities…** to open the file list.

Each file has a priority dropdown:

| Priority | Behavior |
|---|---|
| **Skip** | File is not downloaded at all |
| **Low** | Downloaded after Normal and High files |
| **Normal** | Default |
| **High** | Downloaded before Normal and Low files |

Use **All High**, **All Normal**, or **Skip All** to bulk-set all files at once. Click **Apply** to save.

> **Note:** File priorities are only available once libtorrent has downloaded the torrent metadata. For magnet links, this happens shortly after adding.

### Sidebar categories

| Category | Shows |
|---|---|
| All Tasks | Every torrent |
| Downloading | Torrents actively downloading |
| Seeding | Completed torrents being seeded |
| Completed | Finished torrents (100%) |
| Paused | Paused torrents |

Counts next to each category update live.

### Seeding

Torrents seed automatically after completing — no configuration needed. To stop seeding, pause or remove the torrent. There is no automatic stop-after-ratio limit by default.

---

## REST API

The server exposes a JSON API for automation or integration.

### List all torrents

```
GET /api/torrents
```

Returns an array of torrent objects:

```json
[
  {
    "id": "abc123...",
    "name": "ubuntu-24.04.iso",
    "size": 2147483648,
    "downloaded": 2147483648,
    "uploaded": 1073741824,
    "progress": 100.0,
    "state": "Seeding",
    "download_speed": 0,
    "upload_speed": 524288,
    "peers": 3,
    "seeds": 10,
    "ratio": 0.500,
    "eta": -1,
    "paused": false,
    "save_path": "/home/user/Downloads/torrents",
    "priority": "normal"
  }
]
```

Possible `state` values: `Downloading`, `Seeding`, `Finished`, `Paused`, `Checking`, `Fetching Metadata`, `Allocating`

### Session stats

```
GET /api/stats
```

```json
{
  "download_speed": 1048576,
  "upload_speed": 262144,
  "count": 5
}
```

### Add a torrent — file upload

```
POST /api/torrents
Content-Type: multipart/form-data

file=<torrent file>
save_path=<optional path>
```

### Add a torrent — magnet link

```
POST /api/torrents
Content-Type: application/json

{
  "magnet": "magnet:?xt=urn:btih:...",
  "save_path": "/optional/path"
}
```

Both return:

```json
{ "id": "abc123..." }
```

### Pause a torrent

```
POST /api/torrents/<id>/pause
```

### Resume a torrent

```
POST /api/torrents/<id>/resume
```

### Set torrent priority

```
POST /api/torrents/<id>/priority
Content-Type: application/json

{ "priority": "high" }
```

Valid values: `high`, `normal`, `low`

### Get file list

```
GET /api/torrents/<id>/files
```

Returns `404` if the torrent doesn't exist or metadata hasn't been fetched yet.

```json
[
  {
    "index": 0,
    "path": "ubuntu-24.04/ubuntu-24.04-desktop-amd64.iso",
    "size": 2147483648,
    "priority": "normal"
  }
]
```

### Set file priorities

```
POST /api/torrents/<id>/files
Content-Type: application/json

{
  "priorities": {
    "0": "high",
    "1": "skip",
    "2": "normal"
  }
}
```

Keys are file indexes (as strings), values are `skip`, `low`, `normal`, or `high`.

### Remove a torrent

```
DELETE /api/torrents/<id>
DELETE /api/torrents/<id>?delete_files=true
```

---

## Data storage

| Path | Contents |
|---|---|
| `$DATA_PATH/<hash>.torrent` | Original `.torrent` file |
| `$DATA_PATH/<hash>.resume` | libtorrent fast-resume data |
| `$DATA_PATH/meta.json` | Torrent list with save paths and priorities |

Resume data is flushed every 60 seconds and on clean shutdown (SIGINT / SIGTERM). If the process is killed hard, libtorrent will re-check files on next startup.

---

## Firewall

The web UI runs on port **8080** (TCP). libtorrent listens on port **6881** (TCP + UDP) for peer connections.

On Rocky Linux with firewalld:

```bash
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --permanent --add-port=6881/tcp
sudo firewall-cmd --permanent --add-port=6881/udp
sudo firewall-cmd --reload
```

---

## License

MIT
