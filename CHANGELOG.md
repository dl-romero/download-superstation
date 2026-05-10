# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [1.3.1] — 2026-05-10

### Added

- `POST /api/torrents` now accepts a `{ file_b64, filename, save_path }` JSON body as an alternative to multipart upload. Used by the Cockpit plugin, which cannot send raw binary through `cockpit.http()` without corruption. The existing multipart path for the standalone web UI is unchanged.
- `systemd/bare-metal-user-download-superstation.service` — systemd user service unit for bare-metal installs; runs as a user service in `~/download-superstation` with no root required.
- `systemd/bare-metal-user-download-superstation-update.service` and `.timer` — daily auto-update timer for bare-metal user installs.
- `scripts/bare-metal-user-update.sh` — update script for bare-metal user installs; fetches latest from git, syncs pip dependencies, and restarts the user service.

### Changed

- `install.sh` no longer requires C extension build tools (`python3-devel`, `gcc-c++`, `boost-devel`, `openssl-devel`). `libtorrent` now installs from a pre-built manylinux wheel on PyPI.
- `install.sh` gained a `--with-cockpit-user` flag for per-user Cockpit plugin install (no root required).

---

## [1.3.0] — 2026-05-09

### Added

- **Cockpit plugin support** — the backend now writes a bearer-token key file at startup so the [cockpit-download-superstation](https://github.com/dl-romero/cockpit-download-superstation) plugin can authenticate without a login prompt.
  - `cockpit-api-key` JSON file written to `COCKPIT_AUTH_PATH` on first run containing the bearer token and host-side port. All API requests from the Cockpit plugin are validated against this token.
  - `COCKPIT_PORT` environment variable — records the host-side port that `cockpit.http()` should connect to. Set this when the container's internal port differs from the mapped host port (e.g. `-p 5005:8080` → `COCKPIT_PORT=5005`).
  - `COCKPIT_AUTH_PATH` environment variable — directory where `cockpit-api-key` is written. For container installs, mount a host-readable volume here (e.g. `-v ~/.download-superstation:/cockpit-auth:z -e COCKPIT_AUTH_PATH=/cockpit-auth`) so `cockpit-bridge` can read the file without entering the container.
- Startup log now prints `cockpit auth path` and `cockpit port` alongside the existing download and data paths.

### Changed

- Cockpit plugin extracted to its own repository: [cockpit-download-superstation](https://github.com/dl-romero/cockpit-download-superstation). The `cockpit/` subdirectory has been removed from this repo.
- `login_required` decorator now trusts requests arriving from loopback (`127.0.0.1` / `::1`) without requiring a session cookie or bearer token. This covers bare-metal installs where `cockpit-bridge` connects directly on the same host.
- Systemd unit templates (Podman and Docker) updated to mount `~/.download-superstation` into the container and pass `COCKPIT_AUTH_PATH` and `COCKPIT_PORT` so the Cockpit plugin works out of the box.

### Fixed

- `login_required` was rejecting Cockpit plugin requests on bare-metal installs because `cockpit-bridge` always connects from the loopback address — now correctly trusted.

---

## [1.2.1] — 2025-12-14

### Fixed

- In-app update (`/api/update`) now uses `git reset --hard origin/main` instead of `git pull` to handle dirty working trees cleanly.

---

## [1.2.0] — 2025-12-13

### Added

- Ratio progress bar in the Progress column with colour coding toward the 1:1 seeding target.

### Changed

- Flask server runs in threaded mode to prevent request queuing when multiple clients poll simultaneously.

---

## [1.1.0] — 2025-12-09

### Added

- About modal with author, website, and repository links.
- Manual update trigger button in the About modal — checks for a newer git commit and applies it in-place with a service restart.
- Systemd service units for Docker (system service) and Podman (rootless user service), each with a daily auto-update timer.
- `scripts/install-docker-service.sh` and `scripts/install-podman-service.sh` — one-step service setup scripts for Rocky Linux.
- `install.sh` — bare-metal venv installer for Rocky Linux.
- `run.sh` — development run script.
- `--userns=keep-id` added to the Podman unit so rootless volume permissions work correctly.

### Fixed

- State label array was off-by-one, causing torrents to display the wrong status string.
- Update button in About modal was calling `.json()` on an already-parsed response.
- Settings modal footer was hidden on short viewports; modal height capped and body made scrollable.
- Login page now centers vertically and horizontally.
- `install.sh` branding corrected to Download Superstation.

### Changed

- UI and startup output rebranded from Torrent WebUI to Download Superstation.
- Password reset instructions added to README and login page.

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
