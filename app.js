/* ── State ─────────────────────────────────────────────── */
const state = {
  results: [],
  downloads: {},          // download_id -> { id, title, mode, url }
  pollIntervals: {},      // download_id -> intervalId
  pendingDownload: null,  // { url, title, channel, thumb }
};

/* ── Utilities ─────────────────────────────────────────── */
function formatDuration(secs) {
  if (!secs) return null;
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return `${m}:${String(s).padStart(2, '0')}`;
}

function formatViews(n) {
  if (!n) return '';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M views`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K views`;
  return `${n} views`;
}

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str ?? '';
  return d.innerHTML;
}

/* ── Toast ─────────────────────────────────────────────── */
function toast(message, type = 'info', duration = 3500) {
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = message;
  document.getElementById('toast-container').prepend(el);
  setTimeout(() => el.remove(), duration);
}

/* ── Tab Switching ─────────────────────────────────────── */
function showTab(name) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.getElementById(`panel-${name}`).classList.add('active');
  document.getElementById(`tab-${name}`).classList.add('active');
  if (name === 'downloads') renderDownloads();
  if (name === 'settings') loadSettings();
}

/* ── Search ────────────────────────────────────────────── */
async function handleSearch(e) {
  e.preventDefault();
  const query = document.getElementById('search-input').value.trim();
  if (!query) return;

  setSearchLoading(true);
  hideError();
  clearResults();

  try {
    const res = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });
    if (!res.ok) throw new Error(`Server error ${res.status}`);
    const data = await res.json();
    state.results = data;
    renderResults(data);
  } catch (err) {
    showError(`Search failed: ${err.message}`);
  } finally {
    setSearchLoading(false);
  }
}

function setSearchLoading(loading) {
  document.getElementById('search-btn-text').style.display = loading ? 'none' : '';
  document.getElementById('search-spinner').style.display = loading ? '' : 'none';
  document.getElementById('search-btn').disabled = loading;
}

function showError(msg) {
  const el = document.getElementById('search-error');
  el.textContent = msg;
  el.style.display = '';
}

function hideError() {
  document.getElementById('search-error').style.display = 'none';
}

function clearResults() {
  document.getElementById('results-grid').innerHTML = '';
  document.getElementById('empty-state').style.display = 'none';
}

/* ── Render Results ────────────────────────────────────── */
function renderResults(results) {
  const grid = document.getElementById('results-grid');
  if (!results.length) {
    document.getElementById('empty-state').style.display = '';
    document.getElementById('empty-state').querySelector('p').textContent = 'No results found.';
    return;
  }

  grid.innerHTML = results.map((r, i) => {
    const dur = formatDuration(r.duration);
    const views = formatViews(r.view_count);
    const thumb = r.thumbnail ? esc(r.thumbnail) : 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 9"/>';
    return `
      <div class="result-card" style="animation-delay:${i * 40}ms"
           onclick="openModal('${esc(r.url)}','${esc(r.title)}','${esc(r.channel || '')}','${thumb}')">
        <div class="card-thumb-wrap">
          <img class="card-thumb" src="${thumb}" alt="${esc(r.title)}" loading="lazy" />
          ${dur ? `<span class="card-duration">${esc(dur)}</span>` : ''}
          <div class="card-play-overlay"><div class="play-circle">▶</div></div>
        </div>
        <div class="card-body">
          <div class="card-title">${esc(r.title)}</div>
          <div class="card-meta">
            <span class="card-channel">${esc(r.channel || 'Unknown')}</span>
            ${views ? `<span class="card-views">${views}</span>` : ''}
          </div>
        </div>
        <div class="card-actions" onclick="event.stopPropagation()">
          <button class="btn-video" onclick="startDownload('${esc(r.url)}','video','${esc(r.title)}')">🎬 Video</button>
          <button class="btn-audio" onclick="startDownload('${esc(r.url)}','audio','${esc(r.title)}')">🎵 Audio</button>
        </div>
      </div>`;
  }).join('');
}

/* ── Modal ─────────────────────────────────────────────── */
function openModal(url, title, channel, thumb) {
  state.pendingDownload = { url, title, channel, thumb };
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-channel').textContent = channel;
  document.getElementById('modal-thumb').src = thumb;
  document.getElementById('modal-overlay').style.display = '';
}

function closeModal() {
  document.getElementById('modal-overlay').style.display = 'none';
  state.pendingDownload = null;
}

function confirmDownload(mode) {
  if (!state.pendingDownload) return;
  startDownload(state.pendingDownload.url, mode, state.pendingDownload.title);
  closeModal();
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

/* ── Download ──────────────────────────────────────────── */
async function startDownload(url, mode, title) {
  showTab('downloads');
  toast(`⏳ Starting: ${title.slice(0, 40)}...`, 'info', 2000);

  try {
    const res = await fetch('/api/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, mode }),
    });
    if (!res.ok) throw new Error(`Server error ${res.status}`);
    const { download_id } = await res.json();

    // Register
    state.downloads[download_id] = { id: download_id, title, mode, url };
    updateActiveBadge();

    // Stream via SSE
    startProgressSSE(download_id);

    toast(`⬇ Download started: ${title.slice(0, 40)}`, 'success');
    renderDownloads(); // Make sure the new item shows up immediately
  } catch (err) {
    toast(`Download failed: ${err.message}`, 'error');
  }
}

function startProgressSSE(download_id) {
  const evtSource = new EventSource(`/api/progress/${download_id}`);
  evtSource.onmessage = (e) => {
    const status = JSON.parse(e.data);
    state.downloads[download_id].status = status;
    renderDownloadItem(download_id, status);
    updateActiveBadge();

    if (status.status === 'finished') {
      toast(`✅ Download complete: ${state.downloads[download_id].title.slice(0, 40)}`, 'success');
      evtSource.close();
    }
    if (status.status === 'error') {
      toast(`❌ Download error: ${status.error || 'Unknown'}`, 'error');
      evtSource.close();
    }
  };
  evtSource.onerror = () => evtSource.close();
}

/* ── Render Downloads ──────────────────────────────────── */
function renderDownloads() {
  const list = document.getElementById('downloads-list');
  const ids = Object.keys(state.downloads);
  if (!ids.length) {
    list.innerHTML = `<div class="empty-state"><div class="empty-icon">📥</div><p>No downloads yet</p></div>`;
    return;
  }
  // Re-render each item (only add if missing)
  ids.forEach(id => {
    const status = state.downloads[id].status || { status: 'queued', percent: '0%' };
    if (!document.getElementById(`dl-${id}`)) {
      renderDownloadItem(id, status);
    }
  });
}

function renderDownloadItem(download_id, status) {
  const meta = state.downloads[download_id];
  const list = document.getElementById('downloads-list');

  // Clear empty state if present
  const empty = list.querySelector('.empty-state');
  if (empty) empty.remove();

  let el = document.getElementById(`dl-${download_id}`);
  if (!el) {
    el = document.createElement('div');
    el.className = 'download-item';
    el.id = `dl-${download_id}`;
    list.prepend(el);
  }

  const pct = parseFloat(status.percent) || 0;
  const chip = chipClass(status.status);
  const badge = meta.mode === 'video'
    ? '<span class="download-mode-badge badge-video">Video</span>'
    : '<span class="download-mode-badge badge-audio">Audio</span>';

  el.innerHTML = `
    <div class="download-item-header">
      ${badge}
      <span class="download-title">${esc(meta.title)}</span>
      <span class="dl-status-chip ${chip}">${capitalize(status.status)}</span>
    </div>
    <div class="progress-bar-track">
      <div class="progress-bar-fill" style="width:${pct}%"></div>
    </div>
    <div class="download-stats">
      <span class="dl-percent">${status.percent || '0%'}</span>
      ${status.speed ? `<span>⚡ ${status.speed}</span>` : ''}
      ${status.eta ? `<span>⏱ ${status.eta}</span>` : ''}
      ${status.filename ? `<span style="color:var(--text-3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:300px;">📄 ${esc(status.filename)}</span>` : ''}
    </div>
    ${status.error ? `
      <div class="error-msg" style="display:flex;align-items:center;">
        <span style="flex:1;">⚠ ${esc(status.error)}</span>
        <button class="btn-outline" style="padding:4px 10px;font-size:0.7rem;" onclick="retryDownload('${download_id}')">Retry</button>
      </div>
    ` : ''}
  `;
}

function chipClass(s) {
  return { queued: 'chip-queued', downloading: 'chip-downloading', processing: 'chip-processing', finished: 'chip-finished', error: 'chip-error' }[s] || 'chip-queued';
}
function capitalize(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : ''; }

function updateActiveBadge() {
  const active = Object.values(state.downloads).filter(d => d.status && ['queued', 'downloading', 'processing'].includes(d.status.status)).length;
  const badge = document.getElementById('active-badge');
  badge.textContent = active;
  badge.style.display = active > 0 ? '' : 'none';
}

function retryDownload(id) {
  const meta = state.downloads[id];
  if (!meta) return;

  const title = meta.title;
  const url = meta.url;
  const mode = meta.mode;

  // Cleanup old download
  const el = document.getElementById(`dl-${id}`);
  if (el) el.remove();
  delete state.downloads[id];
  updateActiveBadge();

  // Retry
  startDownload(url, mode, title);
}

function clearFinishedDownloads() {
  Object.keys(state.downloads).forEach(id => {
    const s = state.downloads[id].status;
    if (s && (s.status === 'finished' || s.status === 'error')) {
      delete state.downloads[id];
      const el = document.getElementById(`dl-${id}`);
      if (el) el.remove();
    }
  });
  if (!Object.keys(state.downloads).length) {
    document.getElementById('downloads-list').innerHTML =
      `<div class="empty-state"><div class="empty-icon">📥</div><p>No downloads yet</p></div>`;
  }
  updateActiveBadge();
}

/* ── Settings ──────────────────────────────────────────── */
async function loadSettings() {
  try {
    const res = await fetch('/api/config');
    const cfg = await res.json();
    document.getElementById('cfg-video-path').value = cfg.video_save_path || '';
    document.getElementById('cfg-audio-path').value = cfg.audio_save_path || '';
    document.getElementById('cfg-video-format').value = cfg.video_format || 'bestvideo+bestaudio/best';
    document.getElementById('cfg-video-container').value = cfg.video_container || 'mp4';
    document.getElementById('cfg-audio-format').value = cfg.audio_format || 'mp3';
    document.getElementById('cfg-audio-quality').value = cfg.audio_quality || '192';
    document.getElementById('cfg-max-results').value = cfg.max_results || 10;
    document.getElementById('cfg-parallel').value = cfg.parallel_downloads || 2;
    document.getElementById('cfg-embed-metadata').value = cfg.embed_metadata === false ? 'false' : 'true';
  } catch (err) {
    showSettingsAlert('Failed to load settings: ' + err.message, 'error');
  }
}

async function saveSettings() {
  const payload = {
    video_save_path: document.getElementById('cfg-video-path').value.trim(),
    audio_save_path: document.getElementById('cfg-audio-path').value.trim(),
    video_format: document.getElementById('cfg-video-format').value,
    video_container: document.getElementById('cfg-video-container').value,
    audio_format: document.getElementById('cfg-audio-format').value,
    audio_quality: document.getElementById('cfg-audio-quality').value,
    max_results: parseInt(document.getElementById('cfg-max-results').value) || 10,
    parallel_downloads: parseInt(document.getElementById('cfg-parallel').value) || 2,
    embed_metadata: document.getElementById('cfg-embed-metadata').value === 'true',
  };

  try {
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`Server error ${res.status}`);
    showSettingsAlert('Settings saved successfully!', 'success');
    toast('✅ Settings saved', 'success');
  } catch (err) {
    showSettingsAlert('Failed to save: ' + err.message, 'error');
  }
}

function showSettingsAlert(msg, type) {
  const el = document.getElementById('settings-alert');
  el.className = `alert alert-${type}`;
  el.textContent = msg;
  el.style.display = '';
  setTimeout(() => { el.style.display = 'none'; }, 4000);
}

/* ── Init ──────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('empty-state').style.display = '';
});
