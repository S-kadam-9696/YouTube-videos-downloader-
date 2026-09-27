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
