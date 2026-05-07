import os
import signal
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from torrent_manager import TorrentManager

DOWNLOAD_PATH = os.environ.get('DOWNLOAD_PATH', str(Path.home() / 'Downloads' / 'torrents'))
DATA_PATH = os.environ.get('DATA_PATH', str(Path.home() / '.torrent-webui'))
HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', 8080))

app = Flask(__name__)
manager = TorrentManager(DOWNLOAD_PATH, DATA_PATH)


def _shutdown(sig, frame):
    print('\n[app] shutting down, saving state…')
    manager.shutdown()
    sys.exit(0)

signal.signal(signal.SIGINT, _shutdown)
signal.signal(signal.SIGTERM, _shutdown)


# ── views ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


# ── API ────────────────────────────────────────────────────────────────────

@app.route('/api/torrents')
def list_torrents():
    return jsonify(manager.get_all_status())


@app.route('/api/stats')
def session_stats():
    return jsonify(manager.get_session_stats())


@app.route('/api/torrents', methods=['POST'])
def add_torrent():
    save_path = request.form.get('save_path') or request.json and request.json.get('save_path')

    if request.content_type and 'multipart' in request.content_type:
        file = request.files.get('file')
        if not file:
            return jsonify({'error': 'No file provided'}), 400
        if not file.filename.endswith('.torrent'):
            return jsonify({'error': 'File must be a .torrent file'}), 400
        try:
            info_hash = manager.add_torrent_file(file.read(), save_path)
            return jsonify({'id': info_hash})
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    body = request.get_json(silent=True) or {}
    magnet = body.get('magnet', '').strip()
    if not magnet:
        return jsonify({'error': 'No magnet link or file provided'}), 400
    if not magnet.startswith('magnet:'):
        return jsonify({'error': 'Invalid magnet link'}), 400
    try:
        info_hash = manager.add_magnet(magnet, save_path)
        return jsonify({'id': info_hash})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/torrents/<info_hash>/pause', methods=['POST'])
def pause_torrent(info_hash):
    ok = manager.pause_torrent(info_hash)
    return jsonify({'ok': ok})


@app.route('/api/torrents/<info_hash>/resume', methods=['POST'])
def resume_torrent(info_hash):
    ok = manager.resume_torrent(info_hash)
    return jsonify({'ok': ok})


@app.route('/api/settings')
def get_settings():
    return jsonify(manager.get_settings())


@app.route('/api/settings', methods=['POST'])
def update_settings():
    body = request.get_json(silent=True)
    if not body:
        return jsonify({'error': 'No data provided'}), 400
    try:
        updated = manager.update_settings(body)
        return jsonify(updated)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/torrents/<info_hash>/priority', methods=['POST'])
def set_priority(info_hash):
    body = request.get_json(silent=True) or {}
    priority = body.get('priority', '').lower()
    if priority not in ('high', 'normal', 'low'):
        return jsonify({'error': 'priority must be high, normal, or low'}), 400
    ok = manager.set_torrent_priority(info_hash, priority)
    return jsonify({'ok': ok})


@app.route('/api/torrents/<info_hash>/files')
def get_files(info_hash):
    files = manager.get_torrent_files(info_hash)
    if files is None:
        return jsonify({'error': 'Torrent not found or metadata not yet available'}), 404
    return jsonify(files)


@app.route('/api/torrents/<info_hash>/files', methods=['POST'])
def set_file_priorities(info_hash):
    body = request.get_json(silent=True) or {}
    priorities = body.get('priorities', {})
    if not priorities:
        return jsonify({'error': 'No priorities provided'}), 400
    ok = manager.set_file_priorities(info_hash, priorities)
    return jsonify({'ok': ok})


@app.route('/api/torrents/<info_hash>', methods=['DELETE'])
def remove_torrent(info_hash):
    delete_files = request.args.get('delete_files', 'false').lower() == 'true'
    ok = manager.remove_torrent(info_hash, delete_files)
    return jsonify({'ok': ok})


if __name__ == '__main__':
    print(f'[app] download path : {DOWNLOAD_PATH}')
    print(f'[app] data path     : {DATA_PATH}')
    print(f'[app] listening on  : http://{HOST}:{PORT}')
    app.run(host=HOST, port=PORT, debug=False)
