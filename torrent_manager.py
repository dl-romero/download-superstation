import libtorrent as lt
import threading
import time
import json
from pathlib import Path


class TorrentManager:
    _STATE_LABELS = [
        'Checking', 'Fetching Metadata', 'Downloading',
        'Finished', 'Seeding', 'Allocating', 'Checking',
    ]

    # Per-torrent queue priority (affects download order between torrents)
    _TORRENT_PRIORITY = {'high': 255, 'normal': 128, 'low': 32}

    # Per-file priority within a torrent
    _FILE_PRIORITY = {'skip': 0, 'low': 1, 'normal': 4, 'high': 7}
    _FILE_PRIORITY_REV = {0: 'skip', 1: 'low', 2: 'low', 3: 'normal',
                          4: 'normal', 5: 'high', 6: 'high', 7: 'high'}

    def __init__(self, download_path: str, data_path: str):
        self.download_path = Path(download_path)
        self.data_path = Path(data_path)
        self.download_path.mkdir(parents=True, exist_ok=True)
        self.data_path.mkdir(parents=True, exist_ok=True)

        settings = {
            'listen_interfaces': '0.0.0.0:6881',
            'enable_dht': True,
            'enable_lsd': True,
            'enable_upnp': True,
            'enable_natpmp': True,
            'alert_mask': lt.alert.category_t.all_categories,
        }
        self.session = lt.session(settings)
        self._lock = threading.Lock()
        self._priorities: dict[str, str] = {}   # info_hash -> 'high'|'normal'|'low'
        self._load_saved_torrents()
        self._start_background_saver()

    # ── persistence helpers ────────────────────────────────────────────────

    def _torrent_file(self, info_hash: str) -> Path:
        return self.data_path / f'{info_hash}.torrent'

    def _resume_file(self, info_hash: str) -> Path:
        return self.data_path / f'{info_hash}.resume'

    def _meta_file(self) -> Path:
        return self.data_path / 'meta.json'

    def _get_id(self, handle) -> str:
        ih = handle.info_hash()
        try:
            return str(ih.v1) if ih.has_v1() else str(ih.v2)
        except AttributeError:
            return str(ih)

    def _load_saved_torrents(self):
        meta_path = self._meta_file()
        if not meta_path.exists():
            return
        try:
            with open(meta_path) as f:
                meta = json.load(f)
        except Exception as e:
            print(f'[torrent] could not read meta: {e}')
            return

        for entry in meta.get('torrents', []):
            try:
                self._restore_entry(entry)
            except Exception as e:
                print(f'[torrent] restore failed for {entry.get("id", "?")}: {e}')

    def _restore_entry(self, entry: dict):
        info_hash = entry['id']
        save_path = entry.get('save_path', str(self.download_path))
        resume_path = self._resume_file(info_hash)
        torrent_path = self._torrent_file(info_hash)

        if torrent_path.exists():
            if resume_path.exists():
                with open(resume_path, 'rb') as f:
                    params = lt.read_resume_data(f.read())
                params.save_path = save_path
                ti = lt.torrent_info(str(torrent_path))
                params.ti = ti
            else:
                params = lt.add_torrent_params()
                params.ti = lt.torrent_info(str(torrent_path))
                params.save_path = save_path
        elif entry.get('magnet'):
            params = lt.parse_magnet_uri(entry['magnet'])
            params.save_path = save_path
            if resume_path.exists():
                with open(resume_path, 'rb') as f:
                    rd = lt.read_resume_data(f.read())
                params.resume_data = rd.resume_data
        else:
            return

        handle = self.session.add_torrent(params)

        priority_name = entry.get('priority', 'normal')
        self._priorities[info_hash] = priority_name
        try:
            handle.set_priority(self._TORRENT_PRIORITY.get(priority_name, 128))
        except Exception:
            pass

    def _save_meta(self):
        entries = []
        for handle in self.session.get_torrents():
            if not handle.is_valid():
                continue
            st = handle.status()
            ih = self._get_id(handle)
            entry = {
                'id': ih,
                'save_path': st.save_path,
                'priority': self._priorities.get(ih, 'normal'),
            }
            if not self._torrent_file(ih).exists() and st.name:
                entry['name'] = st.name
            entries.append(entry)

        with open(self._meta_file(), 'w') as f:
            json.dump({'torrents': entries}, f)

    def _flush_resume_data(self):
        handles = [h for h in self.session.get_torrents() if h.is_valid()]
        if not handles:
            return
        for h in handles:
            try:
                h.save_resume_data(lt.torrent_handle.save_info_dict)
            except Exception:
                pass

        deadline = time.time() + 10
        pending = {self._get_id(h) for h in handles}
        while time.time() < deadline and pending:
            alert = self.session.pop_alert()
            if alert is None:
                time.sleep(0.05)
                continue
            if isinstance(alert, lt.save_resume_data_alert):
                try:
                    ih = self._get_id(alert.handle)
                    data = lt.write_resume_data_buf(alert.params)
                    with open(self._resume_file(ih), 'wb') as f:
                        f.write(data)
                    pending.discard(ih)
                except Exception:
                    pass
            elif isinstance(alert, lt.save_resume_data_failed_alert):
                try:
                    pending.discard(self._get_id(alert.handle))
                except Exception:
                    pass

    def _start_background_saver(self):
        def loop():
            while True:
                time.sleep(60)
                try:
                    self._flush_resume_data()
                    self._save_meta()
                except Exception as e:
                    print(f'[torrent] background save error: {e}')

        threading.Thread(target=loop, daemon=True).start()

    # ── public API ─────────────────────────────────────────────────────────

    def add_torrent_file(self, file_bytes: bytes, save_path: str = None) -> str:
        ti = lt.torrent_info(lt.bdecode(file_bytes))
        info_hash = str(ti.info_hash())

        with self._lock:
            for h in self.session.get_torrents():
                if self._get_id(h) == info_hash:
                    return info_hash

            dst = self._torrent_file(info_hash)
            with open(dst, 'wb') as f:
                f.write(file_bytes)

            params = lt.add_torrent_params()
            params.ti = ti
            params.save_path = save_path or str(self.download_path)
            self.session.add_torrent(params)

        self._priorities.setdefault(info_hash, 'normal')
        self._save_meta()
        return info_hash

    def add_magnet(self, magnet_uri: str, save_path: str = None) -> str:
        params = lt.parse_magnet_uri(magnet_uri)
        params.save_path = save_path or str(self.download_path)

        with self._lock:
            handle = self.session.add_torrent(params)

        info_hash = self._get_id(handle)
        self._priorities.setdefault(info_hash, 'normal')
        self._save_meta()
        return info_hash

    def get_all_status(self) -> list:
        result = []
        for handle in self.session.get_torrents():
            if not handle.is_valid():
                continue
            st = handle.status()
            ih = self._get_id(handle)
            state_idx = int(st.state)
            label = (self._STATE_LABELS[state_idx]
                     if 0 <= state_idx < len(self._STATE_LABELS) else 'Unknown')
            if st.paused and label not in ('Checking',):
                label = 'Paused'

            total = st.total_wanted if st.total_wanted > 0 else 0
            done = st.total_wanted_done
            eta = -1
            if st.download_rate > 0 and done < total:
                eta = int((total - done) / st.download_rate)

            ratio = (st.all_time_upload / st.all_time_download
                     if st.all_time_download > 0 else 0.0)

            result.append({
                'id': ih,
                'name': st.name or f'[{ih[:8]}…]',
                'size': total,
                'downloaded': done,
                'uploaded': st.all_time_upload,
                'progress': round(st.progress * 100, 1),
                'state': label,
                'download_speed': st.download_rate,
                'upload_speed': st.upload_rate,
                'peers': st.num_peers,
                'seeds': st.num_seeds,
                'ratio': round(ratio, 3),
                'eta': eta,
                'paused': bool(st.paused),
                'save_path': st.save_path,
                'priority': self._priorities.get(ih, 'normal'),
            })
        return result

    def pause_torrent(self, info_hash: str) -> bool:
        for h in self.session.get_torrents():
            if self._get_id(h) == info_hash:
                h.pause()
                return True
        return False

    def resume_torrent(self, info_hash: str) -> bool:
        for h in self.session.get_torrents():
            if self._get_id(h) == info_hash:
                h.resume()
                return True
        return False

    def remove_torrent(self, info_hash: str, delete_files: bool = False) -> bool:
        for h in self.session.get_torrents():
            if self._get_id(h) == info_hash:
                flags = lt.remove_flags_t.delete_files if delete_files else 0
                self.session.remove_torrent(h, flags)
                for p in (self._torrent_file(info_hash), self._resume_file(info_hash)):
                    if p.exists():
                        p.unlink()
                self._save_meta()
                return True
        return False

    def set_torrent_priority(self, info_hash: str, priority_name: str) -> bool:
        if priority_name not in self._TORRENT_PRIORITY:
            return False
        for h in self.session.get_torrents():
            if self._get_id(h) == info_hash:
                self._priorities[info_hash] = priority_name
                try:
                    h.set_priority(self._TORRENT_PRIORITY[priority_name])
                except Exception:
                    pass
                self._save_meta()
                return True
        return False

    def get_torrent_files(self, info_hash: str) -> list | None:
        for h in self.session.get_torrents():
            if self._get_id(h) != info_hash:
                continue
            tf = h.torrent_file()
            if not tf:
                return None   # metadata not yet available
            fs = tf.files()
            try:
                file_prios = h.get_file_priorities()
            except Exception:
                file_prios = []
            files = []
            for i in range(fs.num_files()):
                raw_prio = file_prios[i] if i < len(file_prios) else 4
                files.append({
                    'index': i,
                    'path': fs.file_path(i),
                    'size': fs.file_size(i),
                    'priority': self._FILE_PRIORITY_REV.get(raw_prio, 'normal'),
                })
            return files
        return None

    def set_file_priorities(self, info_hash: str, priorities: dict) -> bool:
        """priorities: {file_index (int or str): priority_name}"""
        for h in self.session.get_torrents():
            if self._get_id(h) != info_hash:
                continue
            tf = h.torrent_file()
            if not tf:
                return False
            num_files = tf.files().num_files()
            try:
                current = list(h.get_file_priorities())
            except Exception:
                current = [4] * num_files
            while len(current) < num_files:
                current.append(4)
            for idx, name in priorities.items():
                i = int(idx)
                if 0 <= i < num_files and name in self._FILE_PRIORITY:
                    current[i] = self._FILE_PRIORITY[name]
            h.prioritize_files(current)
            return True
        return False

    def get_session_stats(self) -> dict:
        handles = [h for h in self.session.get_torrents() if h.is_valid()]
        total_dl = sum(h.status().download_rate for h in handles)
        total_ul = sum(h.status().upload_rate for h in handles)
        return {
            'download_speed': total_dl,
            'upload_speed': total_ul,
            'count': len(handles),
        }

    def shutdown(self):
        self._flush_resume_data()
        self._save_meta()
