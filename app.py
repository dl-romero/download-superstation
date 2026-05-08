import hashlib
import json
import os
import secrets
import signal
import subprocess
import sys
import threading
from datetime import timedelta
from functools import wraps
from pathlib import Path

from flask import (Flask, jsonify, redirect, render_template,
                   request, session)
from torrent_manager import TorrentManager

DOWNLOAD_PATH = os.environ.get('DOWNLOAD_PATH', str(Path.home() / 'Downloads' / 'torrents'))
DATA_PATH     = os.environ.get('DATA_PATH',     str(Path.home() / '.download-superstation'))
HOST          = os.environ.get('HOST', '0.0.0.0')
PORT          = int(os.environ.get('PORT', 8080))

app = Flask(__name__)
app.permanent_session_lifetime = timedelta(days=30)

# Load or generate Flask secret key
Path(DATA_PATH).mkdir(parents=True, exist_ok=True)
_secret_file = Path(DATA_PATH) / 'secret.key'
if _secret_file.exists():
    app.secret_key = _secret_file.read_text().strip()
else:
    app.secret_key = secrets.token_hex(32)
    _secret_file.write_text(app.secret_key)

manager = TorrentManager(DOWNLOAD_PATH, DATA_PATH)


# ── auth helpers ─────────────────────────────────────────────────────────────

_auth_file = Path(DATA_PATH) / 'auth.json'


def _hash_pw(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 200_000).hex()


def _load_auth() -> dict:
    if _auth_file.exists():
        with open(_auth_file) as f:
            return json.load(f)
    salt = secrets.token_hex(16)
    auth = {'username': 'admin', 'salt': salt, 'password_hash': _hash_pw('admin', salt)}
    with open(_auth_file, 'w') as f:
        json.dump(auth, f)
    print('[app] first run — default credentials: admin / admin  ← change in Settings')
    return auth


def _save_auth(username: str, password: str):
    salt = secrets.token_hex(16)
    with open(_auth_file, 'w') as f:
        json.dump({'username': username, 'salt': salt,
                   'password_hash': _hash_pw(password, salt)}, f)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated


def _shutdown(sig, frame):
    print('\n[app] shutting down, saving state…')
    manager.shutdown()
    sys.exit(0)

signal.signal(signal.SIGINT,  _shutdown)
signal.signal(signal.SIGTERM, _shutdown)


# ── auth routes ───────────────────────────────────────────────────────────────

@app.route('/login')
def login_page():
    if session.get('logged_in'):
        return redirect('/')
    return render_template('login.html')


@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    body = request.get_json(silent=True) or {}
    auth = _load_auth()
    if (body.get('username') == auth['username'] and
            _hash_pw(body.get('password', ''), auth['salt']) == auth['password_hash']):
        session['logged_in'] = True
        session.permanent = True
        return jsonify({'ok': True})
    return jsonify({'error': 'Invalid username or password'}), 401


@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    session.clear()
    return jsonify({'ok': True})


@app.route('/api/auth/change-password', methods=['POST'])
@login_required
def change_password():
    body = request.get_json(silent=True) or {}
    auth = _load_auth()
    if _hash_pw(body.get('current_password', ''), auth['salt']) != auth['password_hash']:
        return jsonify({'error': 'Current password is incorrect'}), 400
    new_pw = body.get('new_password', '')
    if len(new_pw) < 4:
        return jsonify({'error': 'Password must be at least 4 characters'}), 400
    new_user = body.get('username', '').strip() or auth['username']
    _save_auth(new_user, new_pw)
    return jsonify({'ok': True})


# ── views ─────────────────────────────────────────────────────────────────────

@app.route('/')
@login_required
def index():
    return render_template('index.html')


# ── API ───────────────────────────────────────────────────────────────────────

@app.route('/api/torrents')
@login_required
def list_torrents():
    return jsonify(manager.get_all_status())


@app.route('/api/stats')
@login_required
def session_stats():
    return jsonify(manager.get_session_stats())


@app.route('/api/settings')
@login_required
def get_settings():
    return jsonify(manager.get_settings())


@app.route('/api/settings', methods=['POST'])
@login_required
def update_settings():
    body = request.get_json(silent=True)
    if not body:
        return jsonify({'error': 'No data provided'}), 400
    try:
        return jsonify(manager.update_settings(body))
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/torrents', methods=['POST'])
@login_required
def add_torrent():
    save_path = request.form.get('save_path') or (request.get_json(silent=True) or {}).get('save_path')

    if request.content_type and 'multipart' in request.content_type:
        file = request.files.get('file')
        if not file:
            return jsonify({'error': 'No file provided'}), 400
        if not file.filename.endswith('.torrent'):
            return jsonify({'error': 'File must be a .torrent file'}), 400
        try:
            return jsonify({'id': manager.add_torrent_file(file.read(), save_path)})
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    body = request.get_json(silent=True) or {}
    magnet = body.get('magnet', '').strip()
    if not magnet:
        return jsonify({'error': 'No magnet link or file provided'}), 400
    if not magnet.startswith('magnet:'):
        return jsonify({'error': 'Invalid magnet link'}), 400
    try:
        return jsonify({'id': manager.add_magnet(magnet, save_path)})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/torrents/<info_hash>/pause', methods=['POST'])
@login_required
def pause_torrent(info_hash):
    return jsonify({'ok': manager.pause_torrent(info_hash)})


@app.route('/api/torrents/<info_hash>/resume', methods=['POST'])
@login_required
def resume_torrent(info_hash):
    return jsonify({'ok': manager.resume_torrent(info_hash)})


@app.route('/api/torrents/<info_hash>', methods=['DELETE'])
@login_required
def remove_torrent(info_hash):
    delete_files = request.args.get('delete_files', 'false').lower() == 'true'
    return jsonify({'ok': manager.remove_torrent(info_hash, delete_files)})


@app.route('/api/torrents/<info_hash>/priority', methods=['POST'])
@login_required
def set_priority(info_hash):
    body = request.get_json(silent=True) or {}
    priority = body.get('priority', '').lower()
    if priority not in ('high', 'normal', 'low'):
        return jsonify({'error': 'priority must be high, normal, or low'}), 400
    return jsonify({'ok': manager.set_torrent_priority(info_hash, priority)})


@app.route('/api/torrents/<info_hash>/files')
@login_required
def get_files(info_hash):
    files = manager.get_torrent_files(info_hash)
    if files is None:
        return jsonify({'error': 'Torrent not found or metadata not yet available'}), 404
    return jsonify(files)


@app.route('/api/torrents/<info_hash>/files', methods=['POST'])
@login_required
def set_file_priorities(info_hash):
    body = request.get_json(silent=True) or {}
    priorities = body.get('priorities', {})
    if not priorities:
        return jsonify({'error': 'No priorities provided'}), 400
    return jsonify({'ok': manager.set_file_priorities(info_hash, priorities)})


@app.route('/api/torrents/<info_hash>/detail')
@login_required
def get_detail(info_hash):
    detail = manager.get_torrent_detail(info_hash)
    if detail is None:
        return jsonify({'error': 'Torrent not found'}), 404
    return jsonify(detail)


_APP_DIR = Path(__file__).parent
_IN_CONTAINER = (
    Path('/.dockerenv').exists() or
    os.environ.get('container') in ('oci', 'podman', 'docker')
)

@app.route('/api/update', methods=['POST'])
@login_required
def trigger_update():
    if _IN_CONTAINER:
        return jsonify({
            'status': 'container',
            'message': (
                'Running inside a container — updates are managed by the container runtime. '
                'To apply the latest image, restart the service:\n\n'
                '  systemctl --user restart download-superstation\n\n'
                'The daily auto-update timer will also do this automatically.'
            ),
        })

    if not (_APP_DIR / '.git').exists():
        return jsonify({
            'status': 'error',
            'message': 'Not a git repository. Re-install via git clone to enable in-app updates.',
        })

    try:
        subprocess.run(['git', 'fetch', 'origin', 'main'],
                       cwd=_APP_DIR, check=True, capture_output=True)
        local  = subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                                         cwd=_APP_DIR).decode().strip()
        remote = subprocess.check_output(['git', 'rev-parse', 'origin/main'],
                                         cwd=_APP_DIR).decode().strip()
    except subprocess.CalledProcessError as e:
        return jsonify({'status': 'error', 'message': f'Git error: {e.stderr.decode().strip()}'})

    if local == remote:
        return jsonify({'status': 'up_to_date', 'message': 'Already up to date.'})

    try:
        subprocess.run(['git', 'reset', '--hard', 'origin/main'],
                       cwd=_APP_DIR, check=True, capture_output=True)
        pip = _APP_DIR / 'venv' / 'bin' / 'pip'
        if pip.exists():
            subprocess.run([str(pip), 'install', '-q', '-r', str(_APP_DIR / 'requirements.txt')],
                           check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        return jsonify({'status': 'error', 'message': f'Update failed: {e.stderr.decode().strip()}'})

    def _restart():
        import time
        time.sleep(1.5)
        manager.shutdown()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    threading.Thread(target=_restart, daemon=True).start()
    return jsonify({'status': 'updated', 'message': 'Update applied. Restarting…'})


if __name__ == '__main__':
    auth = _load_auth()
    print('[app] Download Superstation')
    print(f'[app] download path : {DOWNLOAD_PATH}')
    print(f'[app] data path     : {DATA_PATH}')
    print(f'[app] listening on  : http://{HOST}:{PORT}')
    print(f'[app] username      : {auth["username"]}')
    app.run(host=HOST, port=PORT, debug=False, threaded=True)
