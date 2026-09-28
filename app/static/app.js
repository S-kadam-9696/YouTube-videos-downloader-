/* ── API Configuration ─────────────────────────────────── */
const API_BASE_URL =
  window.API_BASE_URL ||
  localStorage.getItem('api_base_url') ||
  '';

function apiUrl(path) {
  return `${API_BASE_URL.replace(/\/$/, '')}${path}`;
}

/* ── State ─────────────────────────────────────────────── */
const state = {
  results: [],
  downloads: {},
  pollIntervals: {},
  pendingDownload: null,
};

/* ── Utilities ─────────────────────────────────────────── */
function formatDuration(secs) {
  if (!secs) return null;

  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;

  if (h > 0) {
    return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }

  return `${m}:${String(s).padStart(2, '0')}`;
}

function formatViews(n) {
  if (!n) return '';

  if (n >= 1_000_000) {
    return `${(n / 1_000_000).toFixed(1)}M views`;
  }

  if (n >= 1_000) {
    return `${(n / 1_000).toFixed(0)}K views`;
  }

  return `${n} views`;
}

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str ?? '';
  return d.innerHTML;
}

/* ── Toast ─────────────────────────────────────────────── */
function toast(message, type = 'info', duration = 3500) {
  const container = document.getElementById('toast-container');

  if (!container) {
    alert(message);
    return;
  }

  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = message;

  container.prepend(el);

  setTimeout(() => {
    el.remove();
  }, duration);
}

/* ── Tab Switching ─────────────────────────────────────── */
function showTab(name) {
  document.querySelectorAll('.tab-panel').forEach(panel => {
    panel.classList.remove('active');
  });

  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.classList.remove('active');
  });

  const panel = document.getElementById(`panel-${name}`);
  const tab = document.getElementById(`tab-${name}`);

  if (panel) panel.classList.add('active');
  if (tab) tab.classList.add('active');

  if (name === 'downloads') {
    renderDownloads();
  }

  if (name === 'settings') {
    loadSettings();
  }
}

/* ── Search ────────────────────────────────────────────── */
async function handleSearch(e) {
  e.preventDefault();

  const input = document.getElementById('search-input');
  const query = input ? input.value.trim() : '';

  if (!query) {
    toast('Enter something to search.', 'error');
    return;
  }

  setSearchLoading(true);
  hideError();
  clearResults();

  try {
    const res = await fetch(apiUrl('/api/search'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query }),
    });

    if (!res.ok) {
      throw new Error(`Server error ${res.status}`);
    }

    const data = await res.json();

    state.results = Array.isArray(data)
      ? data
      : Array.isArray(data.results)
        ? data.results
        : [];

    renderResults(state.results);
  } catch (err) {
    console.error('Search error:', err);
    showError(`Search failed: ${err.message}`);
  } finally {
    setSearchLoading(false);
  }
}

function setSearchLoading(loading) {
  const text = document.getElementById('search-btn-text');
  const spinner = document.getElementById('search-spinner');
  const button = document.getElementById('search-btn');

  if (text) text.style.display = loading ? 'none' : '';
  if (spinner) spinner.style.display = loading ? '' : 'none';
  if (button) button.disabled = loading;
}

function showError(msg) {
  const el = document.getElementById('search-error');

  if (!el) return;

  el.textContent = msg;
  el.style.display = '';
}

function hideError() {
  const el = document.getElementById('search-error');

  if (el) {
    el.style.display = 'none';
  }
}

function clearResults() {
  const grid = document.getElementById('results-grid');
  const empty = document.getElementById('empty-state');

  if (grid) grid.innerHTML = '';
  if (empty) empty.style.display = 'none';
}

/* ── Render Results ────────────────────────────────────── */
function renderResults(results) {
  const grid = document.getElementById('results-grid');
  const empty = document.getElementById('empty-state');

  if (!grid) return;

  if (!results || !results.length) {
    grid.innerHTML = '';

    if (empty) {
      empty.style.display = '';
      const p = empty.querySelector('p');

      if (p) {
        p.textContent = 'No results found.';
      }
    }

    return;
  }

  if (empty) {
    empty.style.display = 'none';
  }

  grid.innerHTML = results.map((r, i) => {
    const duration = formatDuration(r.duration);
    const views = formatViews(r.view_count);

    const thumbnail = r.thumbnail
      ? esc(r.thumbnail)
      : 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 9"/>';

    return `
      <div
        class="result-card"
        style="animation-delay:${i * 40}ms"
        onclick="openModal(
          '${esc(r.url)}',
          '${esc(r.title)}',
          '${esc(r.channel || '')}',
          '${thumbnail}'
        )"
      >
        <div class="card-thumb-wrap">
          <img
            class="card-thumb"
            src="${thumbnail}"
            alt="${esc(r.title)}"
            loading="lazy"
          />

          ${
            duration
              ? `<span class="card-duration">${esc(duration)}</span>`
              : ''
          }

          <div class="card-play-overlay">
            <div class="play-circle">▶</div>
          </div>
        </div>

        <div class="card-body">
          <div class="card-title">
            ${esc(r.title)}
          </div>

          <div class="card-meta">
            <span class="card-channel">
              ${esc(r.channel || 'Unknown')}
            </span>

            ${
              views
                ? `<span class="card-views">${views}</span>`
                : ''
            }
          </div>
        </div>

        <div
          class="card-actions"
          onclick="event.stopPropagation()"
        >
          <button
            class="btn-video"
            onclick="startDownload(
              '${esc(r.url)}',
              'video',
              '${esc(r.title)}'
            )"
          >
            🎬 Video
          </button>

          <button
            class="btn-audio"
            onclick="startDownload(
              '${esc(r.url)}',
              'audio',
              '${esc(r.title)}'
            )"
          >
            🎵 Audio
          </button>
        </div>
      </div>
    `;
  }).join('');
}

/* ── Download Modal ───────────────────────────────────── */
function openModal(url, title, channel = '', thumb = '') {
  state.pendingDownload = {
    url,
    title,
    channel,
    thumb,
  };

  const modal = document.getElementById('download-modal');

  if (!modal) {
    startDownload(url, 'video', title);
    return;
  }

  const titleEl = document.getElementById('modal-title');
  const channelEl = document.getElementById('modal-channel');
  const thumbEl = document.getElementById('modal-thumb');

  if (titleEl) titleEl.textContent = title || '';
  if (channelEl) channelEl.textContent = channel || '';

  if (thumbEl) {
    thumbEl.src = thumb || '';
    thumbEl.alt = title || 'Video thumbnail';
  }

  modal.classList.add('active');
  modal.style.display = '';
}

function closeModal() {
  const modal = document.getElementById('download-modal');

  if (!modal) return;

  modal.classList.remove('active');
  modal.style.display = 'none';

  state.pendingDownload = null;
}

/* ── Start Download ───────────────────────────────────── */
async function startDownload(url, mode = 'video', title = '') {
  if (!url) {
    toast('Invalid video URL.', 'error');
    return;
  }

  closeModal();

  try {
    const res = await fetch(apiUrl('/api/download'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        url,
        mode,
      }),
    });

    if (!res.ok) {
      let message = `Server error ${res.status}`;

      try {
        const errorData = await res.json();

        if (errorData.detail) {
          message = errorData.detail;
        }
      } catch (_) {}

      throw new Error(message);
    }

    const data = await res.json();

    const downloadId =
      data.id ||
      data.download_id ||
      data.task_id;

    if (!downloadId) {
      throw new Error('Server did not return a download ID.');
    }

    state.downloads[downloadId] = {
      id: downloadId,
      title: title || data.title || 'Download',
      mode,
      url,
    };

    toast(
      `${mode === 'audio' ? 'Audio' : 'Video'} download started.`,
      'success'
    );

    showTab('downloads');

    startPolling(downloadId);
  } catch (err) {
    console.error('Download error:', err);
    toast(`Download failed: ${err.message}`, 'error');
  }
}

/* ── Poll Download Status ─────────────────────────────── */
function startPolling(downloadId) {
  if (state.pollIntervals[downloadId]) {
    clearInterval(state.pollIntervals[downloadId]);
  }

  pollStatus(downloadId);

  state.pollIntervals[downloadId] = setInterval(() => {
    pollStatus(downloadId);
  }, 1000);
}

async function pollStatus(downloadId) {
  try {
    const res = await fetch(
      apiUrl(`/api/status/${encodeURIComponent(downloadId)}`)
    );

    if (!res.ok) {
      throw new Error(`Status error ${res.status}`);
    }

    const status = await res.json();

    state.downloads[downloadId] = {
      ...(state.downloads[downloadId] || {}),
      ...status,
      id: downloadId,
    };

    renderDownloads();

    const currentStatus = String(status.status || '').toLowerCase();

    if (
      currentStatus === 'finished' ||
      currentStatus === 'completed' ||
      currentStatus === 'error' ||
      currentStatus === 'failed'
    ) {
      stopPolling(downloadId);
    }
  } catch (err) {
    console.error('Polling error:', err);
  }
}

function stopPolling(downloadId) {
  if (state.pollIntervals[downloadId]) {
    clearInterval(state.pollIntervals[downloadId]);
    delete state.pollIntervals[downloadId];
  }
}

/* ── Downloads ────────────────────────────────────────── */
async function renderDownloads() {
  const container = document.getElementById('downloads-list');

  if (!container) return;

  try {
    const res = await fetch(apiUrl('/api/status'));

    if (res.ok) {
      const data = await res.json();

      const statuses =
        data.downloads ||
        data.statuses ||
        data ||
        {};

      if (statuses && typeof statuses === 'object') {
        Object.entries(statuses).forEach(([id, status]) => {
          state.downloads[id] = {
            ...(state.downloads[id] || {}),
            ...status,
            id,
          };
        });
      }
    }
  } catch (err) {
    console.error('Failed to load downloads:', err);
  }

  const downloads = Object.values(state.downloads);

  if (!downloads.length) {
    container.innerHTML = `
      <div class="empty-downloads">
        <div class="empty-icon">⬇️</div>
        <h3>No downloads yet</h3>
        <p>Your downloads will appear here.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = downloads.map(download => {
    const status = String(download.status || 'queued').toLowerCase();

    const progress = Math.max(
      0,
      Math.min(
        100,
        Number(
          download.progress ??
          download.percent ??
          0
        )
      )
    );

    let statusText = status;

    if (status === 'downloading') {
      statusText = `Downloading ${progress}%`;
    } else if (status === 'finished' || status === 'completed') {
      statusText = 'Completed';
    } else if (status === 'error' || status === 'failed') {
      statusText = 'Failed';
    } else if (status === 'queued' || status === 'pending') {
      statusText = 'Waiting...';
    }

    const title = esc(
      download.title ||
      download.filename ||
      'Download'
    );

    const filename = download.filename
      ? esc(download.filename)
      : '';

    const fileUrl =
      download.file_url ||
      download.download_url ||
      '';

    return `
      <div class="download-item">
        <div class="download-info">
          <div class="download-title">${title}</div>

          <div class="download-status">
            ${esc(statusText)}
          </div>

          ${
            filename
              ? `<div class="download-filename">${filename}</div>`
              : ''
          }

          ${
            status === 'downloading'
              ? `
                <div class="progress-bar">
                  <div
                    class="progress-fill"
                    style="width:${progress}%"
                  ></div>
                </div>
              `
              : ''
          }
        </div>

        <div class="download-actions">
          ${
            (status === 'finished' || status === 'completed') &&
            fileUrl
              ? `
                <a
                  class="btn-download"
                  href="${esc(apiUrl(fileUrl))}"
                  target="_blank"
                  rel="noopener"
                  download
                >
                  ⬇️ Download
                </a>
              `
              : ''
          }

          ${
            status === 'error' || status === 'failed'
              ? `<span class="download-error">Error</span>`
              : ''
          }
        </div>
      </div>
    `;
  }).join('');
}

/* ── Settings ─────────────────────────────────────────── */
function loadSettings() {
  const input =
    document.getElementById('api-base-url') ||
    document.getElementById('api-url');

  if (input) {
    input.value =
      localStorage.getItem('api_base_url') ||
      API_BASE_URL ||
      '';
  }
}

function saveSettings() {
  const input =
    document.getElementById('api-base-url') ||
    document.getElementById('api-url');

  if (!input) {
    toast('Settings field not found.', 'error');
    return;
  }

  const value = input.value.trim().replace(/\/$/, '');

  if (value) {
    localStorage.setItem('api_base_url', value);
  } else {
    localStorage.removeItem('api_base_url');
  }

  toast('Settings saved.', 'success');
}

function clearFinishedDownloads() {
  Object.keys(state.downloads).forEach(id => {
    const status = String(
      state.downloads[id]?.status || ''
    ).toLowerCase();

    if (
      status === 'finished' ||
      status === 'completed' ||
      status === 'error' ||
      status === 'failed'
    ) {
      stopPolling(id);
      delete state.downloads[id];
    }
  });

  renderDownloads();
  toast('Finished downloads cleared.', 'success');
}

/* ── Modal Events ─────────────────────────────────────── */
function setupModal() {
  const modal = document.getElementById('download-modal');

  if (!modal) return;

  modal.addEventListener('click', event => {
    if (event.target === modal) {
      closeModal();
    }
  });

  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      closeModal();
    }
  });
}

/* ── Initialization ───────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  setupModal();

  const searchForm = document.getElementById('search-form');

  if (searchForm) {
    searchForm.addEventListener('submit', handleSearch);
  }

  const saveButton = document.getElementById('save-settings');

  if (saveButton) {
    saveButton.addEventListener('click', saveSettings);
  }

  const clearButton =
    document.getElementById('clear-finished') ||
    document.getElementById('clear-downloads');

  if (clearButton) {
    clearButton.addEventListener(
      'click',
      clearFinishedDownloads
    );
  }

  document.querySelectorAll('[data-tab]').forEach(tab => {
    tab.addEventListener('click', () => {
      showTab(tab.dataset.tab);
    });
  });

  loadSettings();
});

/* ── Global functions for HTML onclick handlers ───────── */
window.showTab = showTab;
window.handleSearch = handleSearch;
window.openModal = openModal;
window.closeModal = closeModal;
window.startDownload = startDownload;
window.saveSettings = saveSettings;
window.clearFinishedDownloads = clearFinishedDownloads;
