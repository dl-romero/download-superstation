# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Changed

- Cockpit plugin extracted to its own repository: [cockpit-download-superstation](https://github.com/dl-romero/cockpit-download-superstation).
- `--with-cockpit` flag on all install scripts now clones `cockpit-download-superstation` at install time instead of building from a local `cockpit/` subdirectory. Install path changed from `download-superstation` to `cockpit-download-superstation` under the Cockpit package directory.
- Removed `cockpit/` directory from this repository.

### Added

#### Cockpit Plugin

- New `cockpit/` directory containing a full [Cockpit](https://cockpit-project.org/) package for Download Superstation.
- React 18 + PatternFly 5 UI that mirrors the standalone web UI — same features, same layout, embedded directly in Cockpit's navigation.
- `manifest.json` — Cockpit package descriptor; plugin only appears when the Download Superstation or Torrent WebUI systemd unit file is present on the host.
- `src/App.jsx` — auth state machine (`loading → authenticated → unauthenticated`) with silent session probe on startup.
- `src/LoginPage.jsx` — sign-in card with username, password, and configurable service port fields.
- `src/TorrentManager.jsx` — main page component:
  - Sidebar navigation with live per-category torrent counts (All, Downloading, Seeding, Finished, Paused, Error).
  - Toolbar with Add, Resume, Pause, and Remove buttons; multi-select aware (buttons disable when irrelevant).
  - Sortable table with columns: name, priority, size, state, progress, download speed, upload speed, ratio, ETA.
  - Row click for single selection and side detail panel; Ctrl/Cmd+click for multi-select.
  - Right-click context menu: resume/pause, priority (high/normal/low), file priorities, remove.
  - Side detail panel (General / Peers / Trackers tabs) with live data updated every poll cycle.
  - File priority modal with per-file dropdowns and bulk-set buttons (All High, All Normal, All Low, Skip All).
  - Delete confirmation modal with optional "also delete files" checkbox.
  - Status bar showing aggregate download/upload speed, torrent count, and free disk space.
  - 2-second polling loop that pauses automatically when the Cockpit tab is hidden (`cockpit.visibilitychange`).
- `src/ServiceStatus.jsx` — real-time systemd service banner via `cockpit.dbus('org.freedesktop.systemd1')`:
  - Probes both `download-superstation` and `torrent-webui` service names automatically.
  - Shows running/stopped/unknown state with coloured dot and live sub-state.
  - One-click Start/Stop with `superuser: 'require'` escalation.
- `src/AddModal.jsx` — add-torrent modal with Torrent File (drag-and-drop) and Magnet Link tabs; optional per-torrent save path.
- `src/SettingsModal.jsx` — settings modal with sections: Storage, Speed Limits, Active Torrent Limits, Seeding Limits, Security (change password), About (version + update check), Cockpit Plugin (service port).
- `src/api.js` — all API calls via `cockpit.http()` (bridge proxy to `127.0.0.1:<port>`):
  - Session cookie auth: captures `Set-Cookie` from login response, stores in `localStorage`, injects as `Cookie` header.
  - Multipart file upload constructed as `Uint8Array` (no browser `FormData`) for Cockpit bridge compatibility.
  - Configurable service port stored in `localStorage`; live port changes close and recreate the HTTP client.
- `src/app.css` — ~500 lines of custom CSS using PatternFly 5 CSS variables for full dark/light theme support.
- `build.js` — esbuild build script: ESM format, `cockpit` marked external (resolved via importmap), font/SVG loaders, optional `--watch` flag.
- `package.json` — build dependencies: React 18, PatternFly 5 React components and icons, esbuild.

#### Install scripts

- `install.sh` — added `--with-cockpit` flag: installs Node.js if needed, builds the plugin, copies `dist/` to `/usr/share/cockpit/download-superstation/`.
- `scripts/install-docker-service.sh` — added `--with-cockpit` flag with same behaviour (system-wide install path).
- `scripts/install-podman-service.sh` — added `--with-cockpit` flag; installs to per-user path `~/.local/share/cockpit/download-superstation/` (no root required).

#### Documentation

- `README.md` — added comprehensive **Cockpit Plugin** section covering: requirements, automatic install via `--with-cockpit`, manual install, build-from-source, architecture notes, and uninstall instructions.
- `CHANGELOG.md` — this file.

---

## [1.0.0] — Initial release

### Added

- Flask-based torrent management REST API backed by libtorrent.
- Session authentication with PBKDF2-SHA256 password hashing; 30-day session cookies.
- Torrent operations: add via `.torrent` file or magnet link, pause, resume, remove (with optional file deletion).
- Per-torrent priority (high / normal / low).
- Per-file priority within a torrent (high / normal / low / skip).
- Seeding limits: stop at ratio and/or stop after N minutes.
- Settings API: download path, speed limits (KB/s), active torrent caps, seeding limits.
- Version endpoint and in-app update trigger.
- Resume data flushed every 60 seconds and on clean shutdown (SIGINT/SIGTERM).
- Docker image published to `ghcr.io/dl-romero/download-superstation`.
- `docker-compose.yml` for single-command Docker Compose deployment.
- Systemd unit files for Docker (system service) and Podman (rootless user service) with daily auto-update timer.
- `scripts/install-docker-service.sh` — one-step Docker service setup for Rocky Linux.
- `scripts/install-podman-service.sh` — one-step Podman rootless service setup.
- `install.sh` — bare-metal venv installer for Rocky Linux.
- `run.sh` — development run script.
- Firewall and environment variable documentation in README.
