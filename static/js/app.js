'use strict';

// ── formatters ──────────────────────────────────────────────────────────────

function fmtSize(bytes) {
  if (!bytes) return '—';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 ** 2) return (bytes / 1024).toFixed(1) + ' KB';
  if (bytes < 1024 ** 3) return (bytes / 1024 ** 2).toFixed(1) + ' MB';
  if (bytes < 1024 ** 4) return (bytes / 1024 ** 3).toFixed(2) + ' GB';
  return (bytes / 1024 ** 4).toFixed(2) + ' TB';
}

function fmtSpeed(bps) {
  return bps > 0 ? fmtSize(bps) + '/s' : '—';
}

function fmtEta(sec) {
  if (sec < 0) return '—';
  if (sec === 0) return '0s';
  if (sec < 60) return sec + 's';
  if (sec < 3600) return Math.floor(sec / 60) + 'm ' + (sec % 60) + 's';
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  return h + 'h ' + m + 'm';
}

function fmtRatio(r) {
  return r > 0 ? r.toFixed(3) : '—';
}

function badgeClass(state) {
  const map = {
    'Downloading': 'dl',
    'Seeding': 'seed',
    'Paused': 'pause',
    'Finished': 'done',
    'Checking': 'check',
    'Fetching Metadata': 'meta',
    'Allocating': 'check',
  };
  return map[state] || 'pause';
}

function priorityLabel(p) {
  return { high: '▲ High', normal: '→ Normal', low: '▼ Low' }[p] || p;
}

function prioritySortVal(p) {
  return { high: 0, normal: 1, low: 2 }[p] ?? 1;
}

function fillClass(state) {
  const map = {
    'Downloading': 'dl',
    'Seeding': 'seed',
    'Finished': 'done',
    'Paused': 'pause',
  };
  return map[state] || 'check';
}

// ── state ───────────────────────────────────────────────────────────────────

let torrents = [];
let selected = new Set();
let filterCategory = 'all';
let searchQuery = '';
let sortKey = 'name';
let sortAsc = true;
let pollTimer = null;
let selectedFile = null;

// ── API ─────────────────────────────────────────────────────────────────────

async function apiFetch(url, opts = {}) {
  const res = await fetch(url, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `HTTP ${res.status}`);
  }
  return res.json();
}

async function fetchTorrents() {
  try {
    const [list, stats] = await Promise.all([
      apiFetch('/api/torrents'),
      apiFetch('/api/stats'),
    ]);
    torrents = list;
    updateStatusBar(stats);
    renderTable();
    updateSidebar();
  } catch (e) {
    console.error('Poll error:', e);
  }
}

async function setTorrentPriority(id, priority) {
  await apiFetch(`/api/torrents/${id}/priority`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ priority }),
  });
  fetchTorrents();
}

async function pauseTorrent(id) {
  await apiFetch(`/api/torrents/${id}/pause`, { method: 'POST' });
  fetchTorrents();
}

async function resumeTorrent(id) {
  await apiFetch(`/api/torrents/${id}/resume`, { method: 'POST' });
  fetchTorrents();
}

async function removeTorrents(ids, deleteFiles = false) {
  await Promise.all(
    ids.map(id => apiFetch(`/api/torrents/${id}?delete_files=${deleteFiles}`, { method: 'DELETE' }))
  );
  selected.clear();
  fetchTorrents();
}

// ── sidebar ─────────────────────────────────────────────────────────────────

function updateSidebar() {
  const counts = {
    all: torrents.length,
    downloading: torrents.filter(t => t.state === 'Downloading').length,
    seeding: torrents.filter(t => t.state === 'Seeding').length,
    finished: torrents.filter(t => t.state === 'Finished').length,
    paused: torrents.filter(t => t.paused).length,
  };
  for (const [key, count] of Object.entries(counts)) {
    const el = document.querySelector(`.sidebar-item[data-cat="${key}"] .si-count`);
    if (el) el.textContent = count;
  }
}

// ── table rendering ─────────────────────────────────────────────────────────

function filteredTorrents() {
  let list = torrents;
  if (filterCategory !== 'all') {
    const map = {
      downloading: t => t.state === 'Downloading',
      seeding:     t => t.state === 'Seeding',
      finished:    t => t.state === 'Finished' || (t.progress === 100 && !t.seeding),
      paused:      t => t.paused,
    };
    const fn = map[filterCategory];
    if (fn) list = list.filter(fn);
  }
  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    list = list.filter(t => t.name.toLowerCase().includes(q));
  }
  return [...list].sort((a, b) => {
    let va = sortKey === 'priority' ? prioritySortVal(a.priority) : a[sortKey];
    let vb = sortKey === 'priority' ? prioritySortVal(b.priority) : b[sortKey];
    if (typeof va === 'string') va = va.toLowerCase();
    if (typeof vb === 'string') vb = vb.toLowerCase();
    if (va < vb) return sortAsc ? -1 : 1;
    if (va > vb) return sortAsc ? 1 : -1;
    return 0;
  });
}

function renderTable() {
  const tbody = document.getElementById('torrent-tbody');
  const list = filteredTorrents();

  if (!list.length) {
    tbody.innerHTML = '<tr class="no-data"><td colspan="10">No torrents in this view</td></tr>';
    updateToolbarButtons();
    return;
  }

  const rows = list.map(t => {
    const sel = selected.has(t.id) ? 'selected' : '';
    const bc = badgeClass(t.state);
    const fc = fillClass(t.state);
    const pct = t.progress.toFixed(1);
    const prio = t.priority || 'normal';

    return `<tr class="${sel}" data-id="${t.id}" onclick="rowClick(event,'${t.id}')" oncontextmenu="rowCtx(event,'${t.id}')">
      <td class="chk"><input type="checkbox" ${selected.has(t.id) ? 'checked' : ''} onclick="chkClick(event,'${t.id}')"></td>
      <td class="name" title="${esc(t.name)}">${esc(t.name)}</td>
      <td><span class="badge prio-${prio}">${priorityLabel(prio)}</span></td>
      <td class="num">${fmtSize(t.size)}</td>
      <td><span class="badge ${bc}">${esc(t.state)}</span></td>
      <td class="prog-cell">
        <div class="prog-wrap">
          <div class="prog-bar"><div class="prog-fill ${fc}" style="width:${pct}%"></div></div>
          <span class="prog-pct">${pct}%</span>
        </div>
      </td>
      <td class="num">${fmtSpeed(t.download_speed)}</td>
      <td class="num">${fmtSpeed(t.upload_speed)}</td>
      <td class="num">${fmtRatio(t.ratio)}</td>
      <td class="num">${fmtEta(t.eta)}</td>
    </tr>`;
  });

  tbody.innerHTML = rows.join('');
  updateToolbarButtons();
  updateHeaderCheckbox();
}

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── selection ────────────────────────────────────────────────────────────────

function rowClick(e, id) {
  if (e.target.type === 'checkbox') return;
  if (e.shiftKey || e.ctrlKey || e.metaKey) {
    if (selected.has(id)) selected.delete(id);
    else selected.add(id);
  } else {
    if (selected.has(id) && selected.size === 1) {
      selected.clear();
    } else {
      selected.clear();
      selected.add(id);
    }
  }
  renderTable();
}

function chkClick(e, id) {
  e.stopPropagation();
  if (e.target.checked) selected.add(id);
  else selected.delete(id);
  renderTable();
}

function toggleSelectAll(e) {
  const visible = filteredTorrents().map(t => t.id);
  if (e.target.checked) visible.forEach(id => selected.add(id));
  else selected.clear();
  renderTable();
}

function updateHeaderCheckbox() {
  const cb = document.getElementById('select-all');
  if (!cb) return;
  const visible = filteredTorrents();
  cb.checked = visible.length > 0 && visible.every(t => selected.has(t.id));
  cb.indeterminate = visible.some(t => selected.has(t.id)) && !cb.checked;
}

function updateToolbarButtons() {
  const none = selected.size === 0;
  const sel = [...selected].map(id => torrents.find(t => t.id === id)).filter(Boolean);
  const anyPaused = sel.some(t => t.paused);
  const anyRunning = sel.some(t => !t.paused);

  document.getElementById('btn-pause').disabled = none || !anyRunning;
  document.getElementById('btn-resume').disabled = none || !anyPaused;
  document.getElementById('btn-delete').disabled = none;
}

// ── status bar ───────────────────────────────────────────────────────────────

function updateStatusBar(stats) {
  document.getElementById('stat-dl').textContent = fmtSpeed(stats.download_speed);
  document.getElementById('stat-ul').textContent = fmtSpeed(stats.upload_speed);
  document.getElementById('stat-count').textContent = stats.count;
}

// ── toolbar actions ──────────────────────────────────────────────────────────

function onPause() {
  [...selected].forEach(pauseTorrent);
}

function onResume() {
  [...selected].forEach(resumeTorrent);
}

function onDelete() {
  const n = selected.size;
  if (!confirm(`Remove ${n} torrent${n > 1 ? 's' : ''}?\n\nClick OK to remove (keep files), or Cancel to abort.`)) return;
  removeTorrents([...selected], false);
}

// ── search ───────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('search').addEventListener('input', e => {
    searchQuery = e.target.value.trim();
    renderTable();
  });

  document.querySelectorAll('.sidebar-item[data-cat]').forEach(el => {
    el.addEventListener('click', () => {
      document.querySelectorAll('.sidebar-item').forEach(s => s.classList.remove('active'));
      el.classList.add('active');
      filterCategory = el.dataset.cat;
      selected.clear();
      renderTable();
    });
  });

  document.querySelectorAll('thead th[data-sort]').forEach(th => {
    th.addEventListener('click', () => {
      const key = th.dataset.sort;
      if (sortKey === key) sortAsc = !sortAsc;
      else { sortKey = key; sortAsc = true; }
      document.querySelectorAll('thead th').forEach(t => t.classList.remove('active-sort'));
      th.classList.add('active-sort');
      renderTable();
    });
  });

  document.getElementById('select-all').addEventListener('change', toggleSelectAll);

  document.getElementById('btn-add').addEventListener('click', openAddModal);
  document.getElementById('btn-pause').addEventListener('click', onPause);
  document.getElementById('btn-resume').addEventListener('click', onResume);
  document.getElementById('btn-delete').addEventListener('click', onDelete);

  // close context menu on outside click
  document.addEventListener('click', () => closeCtxMenu());

  fetchTorrents();
  pollTimer = setInterval(fetchTorrents, 2000);
});

// ── add modal ────────────────────────────────────────────────────────────────

function openAddModal() {
  selectedFile = null;
  document.getElementById('drop-label').textContent = 'Drop .torrent file here or click to browse';
  document.getElementById('drop-sub').textContent = '.torrent files only';
  document.getElementById('selected-file-name').textContent = '';
  document.getElementById('magnet-input').value = '';
  document.getElementById('save-path-file').value = '';
  document.getElementById('save-path-magnet').value = '';
  document.getElementById('add-error').textContent = '';
  document.getElementById('add-error').classList.remove('show');
  switchTab('file');
  document.getElementById('add-modal').classList.add('open');
}

function closeAddModal() {
  document.getElementById('add-modal').classList.remove('open');
}

function switchTab(tab) {
  document.querySelectorAll('.modal-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.querySelector(`.modal-tab[data-tab="${tab}"]`).classList.add('active');
  document.getElementById(`tab-${tab}`).classList.add('active');
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.modal-tab').forEach(tab => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
  });

  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('file-input');

  dropZone.addEventListener('click', () => fileInput.click());
  dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    handleFileSelect(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener('change', () => handleFileSelect(fileInput.files[0]));

  document.getElementById('add-modal').addEventListener('click', e => {
    if (e.target === e.currentTarget) closeAddModal();
  });

  document.getElementById('btn-submit-add').addEventListener('click', submitAdd);
});

function handleFileSelect(file) {
  if (!file) return;
  if (!file.name.endsWith('.torrent')) {
    showAddError('Please select a .torrent file.');
    return;
  }
  selectedFile = file;
  document.getElementById('selected-file-name').textContent = '✓ ' + file.name;
  document.getElementById('drop-label').textContent = file.name;
  document.getElementById('drop-sub').textContent = fmtSize(file.size);
}

function showAddError(msg) {
  const el = document.getElementById('add-error');
  el.textContent = msg;
  el.classList.add('show');
}

async function submitAdd() {
  const activeTab = document.querySelector('.modal-tab.active')?.dataset?.tab;
  document.getElementById('add-error').classList.remove('show');

  const btn = document.getElementById('btn-submit-add');
  btn.disabled = true;
  btn.textContent = 'Adding…';

  try {
    if (activeTab === 'file') {
      if (!selectedFile) { showAddError('Please select a .torrent file.'); return; }
      const fd = new FormData();
      fd.append('file', selectedFile);
      const savePath = document.getElementById('save-path-file').value.trim();
      if (savePath) fd.append('save_path', savePath);
      const res = await fetch('/api/torrents', { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) { showAddError(data.error || 'Failed to add torrent.'); return; }
    } else {
      const magnet = document.getElementById('magnet-input').value.trim();
      if (!magnet) { showAddError('Please enter a magnet link.'); return; }
      const savePath = document.getElementById('save-path-magnet').value.trim();
      const res = await fetch('/api/torrents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ magnet, save_path: savePath || undefined }),
      });
      const data = await res.json();
      if (!res.ok) { showAddError(data.error || 'Failed to add torrent.'); return; }
    }
    closeAddModal();
    fetchTorrents();
  } catch (e) {
    showAddError(e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Add';
  }
}

// ── context menu ─────────────────────────────────────────────────────────────

function rowCtx(e, id) {
  e.preventDefault();
  if (!selected.has(id)) {
    selected.clear();
    selected.add(id);
    renderTable();
  }
  const menu = document.getElementById('ctx-menu');
  const t = torrents.find(t => t.id === id);
  document.getElementById('ctx-pause').style.display = (t && !t.paused) ? '' : 'none';
  document.getElementById('ctx-resume').style.display = (t && t.paused) ? '' : 'none';
  menu.style.left = Math.min(e.clientX, window.innerWidth - 180) + 'px';
  menu.style.top = Math.min(e.clientY, window.innerHeight - 140) + 'px';
  menu.classList.add('open');
}

function closeCtxMenu() {
  document.getElementById('ctx-menu').classList.remove('open');
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('btn-settings').addEventListener('click', openSettingsModal);
  document.getElementById('btn-save-settings').addEventListener('click', saveSettings);
  document.getElementById('settings-modal').addEventListener('click', e => {
    if (e.target === e.currentTarget) closeSettingsModal();
  });
});

// ── settings modal ────────────────────────────────────────────────────────────

async function openSettingsModal() {
  document.getElementById('settings-error').classList.remove('show');
  document.getElementById('btn-save-settings').disabled = false;
  document.getElementById('btn-save-settings').textContent = 'Save';
  try {
    const s = await apiFetch('/api/settings');
    document.getElementById('cfg-download-path').value = s.download_path || '';
    document.getElementById('cfg-dl-speed').value     = s.max_download_speed ?? 0;
    document.getElementById('cfg-ul-speed').value     = s.max_upload_speed   ?? 0;
    document.getElementById('cfg-max-dl').value       = s.max_active_downloads ?? 0;
    document.getElementById('cfg-max-seed').value     = s.max_active_seeds     ?? 0;
  } catch (e) {
    console.error('Failed to load settings:', e);
  }
  document.getElementById('settings-modal').classList.add('open');
}

function closeSettingsModal() {
  document.getElementById('settings-modal').classList.remove('open');
}

async function saveSettings() {
  const btn = document.getElementById('btn-save-settings');
  const errEl = document.getElementById('settings-error');
  errEl.classList.remove('show');
  btn.disabled = true;
  btn.textContent = 'Saving…';

  const payload = {
    download_path:        document.getElementById('cfg-download-path').value.trim(),
    max_download_speed:   parseInt(document.getElementById('cfg-dl-speed').value)   || 0,
    max_upload_speed:     parseInt(document.getElementById('cfg-ul-speed').value)   || 0,
    max_active_downloads: parseInt(document.getElementById('cfg-max-dl').value)     || 0,
    max_active_seeds:     parseInt(document.getElementById('cfg-max-seed').value)   || 0,
  };

  try {
    await apiFetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    closeSettingsModal();
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.add('show');
    btn.disabled = false;
    btn.textContent = 'Save';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('ctx-pause').addEventListener('click', () => { onPause(); closeCtxMenu(); });
  document.getElementById('ctx-resume').addEventListener('click', () => { onResume(); closeCtxMenu(); });
  document.getElementById('ctx-delete').addEventListener('click', () => { onDelete(); closeCtxMenu(); });
  document.getElementById('ctx-delete-files').addEventListener('click', () => {
    const n = selected.size;
    if (!confirm(`Permanently delete ${n} torrent${n > 1 ? 's' : ''} AND all downloaded files?`)) return;
    removeTorrents([...selected], true);
    closeCtxMenu();
  });

  for (const p of ['high', 'normal', 'low']) {
    document.getElementById(`ctx-prio-${p}`).addEventListener('click', () => {
      [...selected].forEach(id => setTorrentPriority(id, p));
      closeCtxMenu();
    });
  }

  document.getElementById('ctx-files').addEventListener('click', () => {
    const id = [...selected][0];
    if (id) openFileModal(id);
    closeCtxMenu();
  });

  document.getElementById('btn-apply-files').addEventListener('click', applyFilePriorities);

  document.getElementById('file-modal').addEventListener('click', e => {
    if (e.target === e.currentTarget) closeFileModal();
  });
});

// ── file priority modal ───────────────────────────────────────────────────────

let _fileModalId = null;

async function openFileModal(id) {
  _fileModalId = id;
  const t = torrents.find(t => t.id === id);
  document.getElementById('file-modal-title').textContent =
    'File Priorities' + (t ? ` — ${t.name}` : '');
  document.getElementById('file-list').innerHTML = '<div class="file-loading">Loading…</div>';
  document.getElementById('file-modal').classList.add('open');

  try {
    const files = await apiFetch(`/api/torrents/${id}/files`);
    renderFileList(files);
  } catch (e) {
    document.getElementById('file-list').innerHTML =
      `<div class="file-loading">${e.message}</div>`;
  }
}

function closeFileModal() {
  document.getElementById('file-modal').classList.remove('open');
  _fileModalId = null;
}

function renderFileList(files) {
  if (!files.length) {
    document.getElementById('file-list').innerHTML =
      '<div class="file-loading">No files found.</div>';
    return;
  }
  const rows = files.map(f => `
    <div class="file-item" data-idx="${f.index}">
      <span class="fi-name" title="${esc(f.path)}">${esc(f.path)}</span>
      <span class="fi-size">${fmtSize(f.size)}</span>
      <select class="fi-prio" data-idx="${f.index}">
        <option value="skip"   ${f.priority === 'skip'   ? 'selected' : ''}>Skip</option>
        <option value="low"    ${f.priority === 'low'    ? 'selected' : ''}>Low</option>
        <option value="normal" ${f.priority === 'normal' ? 'selected' : ''}>Normal</option>
        <option value="high"   ${f.priority === 'high'   ? 'selected' : ''}>High</option>
      </select>
    </div>`).join('');
  document.getElementById('file-list').innerHTML = rows;
}

function setAllFilePriority(priority) {
  document.querySelectorAll('#file-list .fi-prio').forEach(sel => {
    sel.value = priority;
  });
}

async function applyFilePriorities() {
  if (!_fileModalId) return;
  const priorities = {};
  document.querySelectorAll('#file-list .fi-prio').forEach(sel => {
    priorities[sel.dataset.idx] = sel.value;
  });
  const btn = document.getElementById('btn-apply-files');
  btn.disabled = true;
  btn.textContent = 'Applying…';
  try {
    await apiFetch(`/api/torrents/${_fileModalId}/files`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ priorities }),
    });
    closeFileModal();
    fetchTorrents();
  } catch (e) {
    alert('Failed to apply priorities: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Apply';
  }
}
