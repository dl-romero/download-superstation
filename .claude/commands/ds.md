You are an expert developer on the **Download Superstation** project with intimate knowledge of every design decision, bug, and fix in its history. When this skill is invoked, embody that expertise immediately — answer questions, implement features, and debug issues without needing to re-read the codebase from scratch.

---

## Project Identity

**Download Superstation** — a self-hosted torrent management web UI built and maintained by David Romero (dromero.dev).

- **Repo:** https://github.com/dl-romero/download-superstation
- **Primary deployment:** bare-metal on `pikachu.local` (Rocky Linux), port 5005
- **Install path:** `/opt/torrent-webui`, runs as user `dromero`
- **Data path:** `~/.download-superstation/` (auth, settings, resume files, meta.json)
- **Systemd service:** `torrent-webui.service`

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, Flask 3.x (threaded mode) |
| Torrent engine | libtorrent 2.0.x (Python bindings) |
| Frontend | Vanilla JS (ES2020), no build step |
| Auth | Session-based, PBKDF2-SHA256 hashed in `auth.json` |
| Persistence | JSON files + libtorrent `.resume` files (bencoded) |
| Container | Docker / Podman (ghcr.io/dl-romero/download-superstation) |
| CI/CD | GitHub Actions — builds Docker image + bare-metal tarball on version tags |

---

## File Map

```
app.py                  Flask app, all routes, auth, update logic
torrent_manager.py      TorrentManager class — libtorrent wrapper, all persistence
templates/
  index.html            Main UI (table, modals, sidebar)
  login.html            Login page
static/
  css/style.css         All styles, dark-ish theme with CSS vars
  js/app.js             All frontend logic — no frameworks
scripts/
  bare-metal-update.sh  Shell update script used by systemd timer
systemd/
  torrent-webui.service Bare-metal systemd service
  ...                   Docker/Podman variants
install.sh              Bare-metal installer
```

---

## Architecture — Key Design Decisions

### TorrentManager (`torrent_manager.py`)
- Single `lt.session` instance, one libtorrent session for the whole app life.
- **Persistence loop:** background thread flushes resume data + saves `meta.json` every 60 seconds.
- **Shutdown:** `manager.shutdown()` → `_flush_resume_data()` + `_save_meta()`. Must be called before `os.execv` restarts.
- **Orphan recovery:** on startup, scans `*.resume` files not referenced in `meta.json` and loads them. This handles meta.json being wiped after a bad restart.
- **Magnet tracking:** `self._magnets` dict (info_hash → magnet URI) is populated when magnets are added and persisted in `meta.json`.

### Resume data restore priority (`_restore_entry`)
1. `.torrent` file exists → load torrent + resume data (full stats)
2. `magnet` key in meta entry → use full `read_resume_data` if `.resume` exists, else parse magnet URI
3. `.resume` file exists (no torrent file, no magnet) → load directly from resume (handles old entries and orphans)
4. None of the above → skip

### libtorrent state labels (critical — was off-by-one in early versions)
```python
_STATE_LABELS = [
    'Queued',            # 0 queued_for_checking
    'Checking',          # 1 checking_files
    'Fetching Metadata', # 2 downloading_metadata
    'Downloading',       # 3 downloading
    'Finished',          # 4 finished
    'Seeding',           # 5 seeding
    'Allocating',        # 6 allocating
    'Checking',          # 7 checking_resume_data
]
```
The original code was missing index 0, causing every state label to be wrong (Downloading showed as Finished, etc.).

### In-app update (`/api/update` in app.py)
- Bare-metal only (container detection via `Path('/.dockerenv').exists()` or `os.environ.get('container')`)
- Uses `git fetch` → compare local/remote hashes → `git reset --hard origin/main` (NOT `git pull` — pull fails on dirty working trees)
- After pulling: `manager.shutdown()` (saves resume data!) then `os.execv` to replace process in-place
- The `manager.shutdown()` call was added specifically because `os.execv` doesn't trigger signal handlers

### Frontend column system (`app.js`)
- `COLUMNS` array defines all 10 columns with `key`, `label`, and `render(t)` function
- `COL_MAP` is a key → column object lookup
- Column order is stored in `localStorage` as `col-order` (array of keys)
- **Critical design:** headers are static in the HTML template (always visible). JS only reorders existing DOM elements via `applyColumnOrder()` on load and `initColumnDrag()` for drag-and-drop. Never creates/destroys header elements — that was an earlier fragile approach that caused headers to vanish if JS had any error.
- `getColumnOrder()` reads live column order from the DOM (queries `thead th[data-sort]` in order)
- `renderTable()` calls `getColumnOrder()` on every render so rows always match current header order

### Progress bar dual-mode
- **Downloading:** shows download % with colored fill based on state
- **Seeding / Finished:** shows ratio progress toward 1:1 (0.000 → orange fill growing to green at 1.0). Text shows actual ratio (e.g. `0.142`), not a percentage.

### Cache busting
- `_GIT_HASH` and `_GIT_DATE` are read at startup via `git rev-parse` and `git log`
- Passed to templates as `v=_STATIC_VER`
- CSS and JS URLs include `?v={{ v }}` so browsers always fetch fresh assets after a deploy

### About modal — version display
- `/api/version` (GET, login required) returns `{commit: "<short hash>", date: "YYYY-MM-DD"}`
- When the ℹ button is clicked, JS immediately opens the modal then fires `apiFetch('/api/version')` and fills `#info-version` and `#info-date` spans
- The modal shows: Author, Website, Repository, **Version** (short git hash), **Released** (commit date)
- Values display as `—` until the fetch resolves, so the modal opens instantly without waiting

---

## Data Files (`~/.download-superstation/`)

| File | Purpose |
|---|---|
| `meta.json` | List of torrent entries: id, save_path, priority, magnet (optional) |
| `{hash}.resume` | libtorrent resume data (bencoded) — includes `all_time_upload`, `all_time_download`, piece map |
| `{hash}.torrent` | Original torrent file (only for file-upload additions, not magnets) |
| `auth.json` | `{username, salt, password_hash}` — PBKDF2-SHA256, 200k iterations |
| `settings.json` | Speed limits, active download/seed limits, ratio/time seeding limits, download path |
| `secret.key` | Flask session secret, generated once on first run |

---

## Known History of Bugs Fixed

### State labels off-by-one
Early versions had `_STATE_LABELS` starting at index 1 (no 'Queued'). Every state showed one slot wrong — downloading torrents showed "Finished", etc. Fixed by adding 'Queued' at index 0.

### Settings modal Save button hidden
Modal had no `max-height`. On small screens the footer was off-screen. Fixed with `max-height: 90vh` on `.modal` and `overflow-y: auto` on `.modal-body`.

### Update button "Could not reach server"
`apiFetch()` returns parsed JSON directly. The update handler was calling `.json()` on the already-parsed result, causing a TypeError caught as a network error.

### Bare-metal update failing on dirty working tree
Files deployed via rsync created uncommitted changes. `git pull` refuses to merge dirty trees. Fixed: both the shell script and the `/api/update` endpoint now use `git reset --hard origin/main`.

### Resume data lost on update restart
`os.execv` replaces the process without triggering signal handlers. `manager.shutdown()` was never called, so up to 60 seconds of upload stats were lost on every in-app update. Fixed by calling `manager.shutdown()` in the `_restart()` thread before `os.execv`.

### Magnet torrents vanished on restart
Magnet URIs were never saved to `meta.json`. On restart, torrents added via magnet had no `.torrent` file and no `magnet` key, so `_restore_entry` skipped them. Then `_save_meta()` overwrote `meta.json` with an empty list. Fixed: `_magnets` dict persists URIs; `_save_meta` writes them; orphan `.resume` scanner recovers any that slipped through.

### Column headers vanished after column-reorder feature
Original implementation created `<th>` elements dynamically in `renderHeaders()`. If that function failed for any reason (including being called before critical event listeners were registered), zero headers appeared. Fixed: headers are static in the HTML template, JS only reorders existing elements.

### Add button stopped working
`renderHeaders()` was called before `btn-add` got its click listener in the same `DOMContentLoaded` block. Any exception in `renderHeaders()` silently aborted the rest of init. Fixed: all critical event listeners now registered before any dynamic setup code runs.

### Ratio bar showing 100% when seeding hadn't reached 1:1
The download progress bar shows 100% when a torrent is seeding (download complete). Users expected the "progress" to reflect seeding toward 1:1 ratio. Fixed: when state is Seeding or Finished, the progress cell switches to show ratio progress (orange → green bar) instead of download %.

---

## Development Workflow

### Local dev
```bash
cd /Users/dromero/torrent-webui
source venv/bin/activate
python app.py
# → http://localhost:8080, default creds admin/admin
```

### Deploy to pikachu
The preferred flow is commit → push → use in-app "Check for Updates" on pikachu.

For emergency direct deploys (avoid — dirties the working tree):
```bash
rsync -av --exclude='.git' --exclude='venv' --exclude='__pycache__' \
  /Users/dromero/torrent-webui/ dromero@pikachu.local:/opt/torrent-webui/
ssh dromero@pikachu.local "sudo systemctl restart torrent-webui"
```
If you rsync, always follow with `git reset --hard origin/main` on pikachu to clean the tree.

### Release process
```bash
git tag vX.Y.Z
git push origin vX.Y.Z
# GitHub Actions builds Docker image → ghcr.io/dl-romero/download-superstation:vX.Y.Z
# and a bare-metal tarball attached to the GitHub release
```

### Password reset (bare-metal)
```bash
ssh dromero@pikachu.local
rm ~/.download-superstation/auth.json
sudo systemctl restart torrent-webui
# Default creds restored: admin / admin
```

---

## Updating This Skill

After significant changes to the codebase (new features, bug fixes, architectural changes), update this file to reflect the current state. Key sections to keep current:
- **Bug history** — add new bugs found and fixed
- **Architecture** — update if data flow or key design changes
- **File map** — add new files
- **Data files** — add new persistence files

To update, run `/ds` and ask Claude to revise the skill file based on what changed in this session.
