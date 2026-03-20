import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.13.2/firebase-app.js';
import { getAuth, onAuthStateChanged, signOut } from 'https://www.gstatic.com/firebasejs/10.13.2/firebase-auth.js';

const state = {
  user: null,
  jobs: [],
  filtered: [],
  selected: null,
};

const authStatusEl = document.getElementById('authStatus');
const searchInputEl = document.getElementById('searchInput');
const refreshBtnEl = document.getElementById('refreshBtn');
const jobsGridEl = document.getElementById('jobsGrid');
const emptyStateEl = document.getElementById('emptyState');
const viewerTitleEl = document.getElementById('viewerTitle');
const viewerMetaEl = document.getElementById('viewerMeta');
const viewerNotesEl = document.getElementById('viewerNotes');
const viewerPreviewPaneEl = document.getElementById('viewerPreviewPane');
const previewBtnEl = document.getElementById('previewBtn');
const downloadBtnEl = document.getElementById('downloadBtn');
const deleteBtnEl = document.getElementById('deleteBtn');
const logoutBtnEl = document.getElementById('logoutBtn');

function setStatus(message, isError = false) {
  authStatusEl.textContent = message;
  authStatusEl.style.color = isError ? '#ffb4b4' : 'var(--muted)';
}

function formatTime(value) {
  if (!value) return 'Unknown';
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return 'Unknown';
  return dt.toLocaleString();
}

async function fetchPublicConfig() {
  const response = await fetch('/api/public-config');
  const data = await response.json();
  if (!response.ok) throw new Error('Unable to load public configuration.');
  return data;
}

async function authHeaders() {
  if (!state.user) return {};
  const token = await state.user.getIdToken();
  return { Authorization: `Bearer ${token}` };
}

async function authorizedUrl(url) {
  const headers = await authHeaders();
  const token = headers.Authorization.replace('Bearer ', '');
  return `${url}${url.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}`;
}

async function renderPreview(preview) {
  if (!preview) {
    viewerPreviewPaneEl.innerHTML = '<p class="converter-empty">No preview available.</p>';
    return;
  }
  if (preview.kind === 'image') {
    const src = await authorizedUrl(preview.url);
    const note = preview.note ? `<p class="converter-empty">${preview.note}</p>` : '';
    viewerPreviewPaneEl.innerHTML = `${note}<img src="${src}" alt="Job preview" class="converter-image-preview" />`;
    return;
  }
  if (preview.kind === 'pdf') {
    const image = preview.imageUrl ? `<img src="${await authorizedUrl(preview.imageUrl)}" alt="PDF preview" class="converter-image-preview" />` : '';
    const text = preview.text ? `<pre class="converter-text-preview">${preview.text}</pre>` : '';
    viewerPreviewPaneEl.innerHTML = `${image}${text || '<p class="converter-empty">No PDF text preview available.</p>'}`;
    return;
  }
  if (preview.kind === 'text') {
    viewerPreviewPaneEl.innerHTML = `<pre class="converter-text-preview">${preview.text || 'No text preview available.'}</pre>`;
    return;
  }
  viewerPreviewPaneEl.innerHTML = '<p class="converter-empty">Unsupported preview format.</p>';
}

function renderViewer() {
  const job = state.selected;
  if (!job) {
    viewerTitleEl.textContent = 'Select a conversion job';
    viewerMetaEl.textContent = 'No job selected';
    viewerNotesEl.textContent = 'Select a job to inspect notes, preview, and output metadata.';
    viewerPreviewPaneEl.innerHTML = '<p class="converter-empty">No preview loaded.</p>';
    return;
  }
  viewerTitleEl.textContent = job.fileName || 'Untitled Job';
  viewerMetaEl.textContent = `${job.sourceFormat?.toUpperCase() || '?'} -> ${job.targetFormat?.toUpperCase() || '?'} • ${formatTime(job.createdAt)}`;
  viewerNotesEl.textContent = JSON.stringify(
    {
      status: job.status,
      aiMode: job.aiMode,
      priority: job.priority,
      notes: job.notes || [],
      createdAt: job.createdAt,
    },
    null,
    2
  );
  renderPreview(job.preview);
}

function renderList() {
  jobsGridEl.innerHTML = '';
  emptyStateEl.classList.toggle('hidden', state.filtered.length > 0);
  state.filtered.forEach((job) => {
    const card = document.createElement('article');
    card.className = 'project-card';
    card.innerHTML = `
      <h4>${job.fileName || 'Untitled Job'}</h4>
      <p>${job.sourceFormat?.toUpperCase() || '?'} -> ${job.targetFormat?.toUpperCase() || '?'} • ${job.aiMode || 'balanced'} AI</p>
      <div class="project-card-meta">
        <span>${job.status || '--'}</span>
        <span>${formatTime(job.createdAt)}</span>
      </div>
    `;
    card.addEventListener('click', () => {
      state.selected = job;
      renderViewer();
    });
    jobsGridEl.appendChild(card);
  });
}

function applySearch() {
  const text = (searchInputEl.value || '').toLowerCase().trim();
  if (!text) {
    state.filtered = [...state.jobs];
    renderList();
    return;
  }
  state.filtered = state.jobs.filter((job) => `${job.fileName || ''} ${job.sourceFormat || ''} ${job.targetFormat || ''}`.toLowerCase().includes(text));
  renderList();
}

async function loadJobs() {
  if (!state.user) return;
  setStatus('Loading conversion history...');
  try {
    const response = await fetch('/api/converter/jobs', { headers: await authHeaders() });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || 'Failed to load jobs.');
    state.jobs = data.jobs || [];
    state.filtered = [...state.jobs];
    state.selected = state.filtered[0] || null;
    renderList();
    renderViewer();
    setStatus(`Loaded ${state.jobs.length} conversion job(s).`);
  } catch (error) {
    setStatus(error.message || 'Failed to load jobs.', true);
  }
}

async function reloadPreview() {
  const job = state.selected;
  if (!job) return;
  try {
    const response = await fetch(`/api/converter/preview/${encodeURIComponent(job.id)}`, { headers: await authHeaders() });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || 'Preview failed.');
    job.preview = data.preview;
    renderViewer();
    setStatus(`Preview refreshed for ${job.fileName}.`);
  } catch (error) {
    setStatus(error.message || 'Preview failed.', true);
  }
}

async function downloadSelected() {
  const job = state.selected;
  if (!job) return;
  const url = await authorizedUrl(`/api/converter/download/${encodeURIComponent(job.id)}`);
  window.location.href = url;
}

async function deleteSelected() {
  const job = state.selected;
  if (!job) return;
  if (!confirm(`Delete conversion job "${job.fileName || 'this job'}"?`)) return;
  try {
    const response = await fetch(`/api/converter/jobs/${encodeURIComponent(job.id)}`, {
      method: 'DELETE',
      headers: await authHeaders(),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || 'Delete failed.');
    state.jobs = state.jobs.filter((item) => item.id !== job.id);
    state.filtered = state.filtered.filter((item) => item.id !== job.id);
    state.selected = state.filtered[0] || null;
    renderList();
    renderViewer();
    setStatus('Conversion job deleted.');
  } catch (error) {
    setStatus(error.message || 'Delete failed.', true);
  }
}

async function init() {
  try {
    const cfg = await fetchPublicConfig();
    const firebaseCfg = cfg.firebase || {};
    const missing = ['apiKey', 'authDomain', 'projectId', 'appId'].filter((k) => !firebaseCfg[k]);
    if (missing.length) throw new Error(`Firebase env is incomplete: missing ${missing.join(', ')}`);
    const app = initializeApp(firebaseCfg);
    const auth = getAuth(app);
    onAuthStateChanged(auth, async (user) => {
      if (!user) {
        window.location.href = `/auth?next=${encodeURIComponent('/conversions')}`;
        return;
      }
      state.user = user;
      setStatus(`Authenticated as ${user.email || user.uid}`);
      await loadJobs();
    });
    logoutBtnEl.addEventListener('click', async () => {
      await signOut(auth);
      window.location.href = '/auth';
    });
  } catch (error) {
    setStatus(error.message || 'Initialization failed.', true);
  }
}

searchInputEl.addEventListener('input', applySearch);
refreshBtnEl.addEventListener('click', loadJobs);
previewBtnEl.addEventListener('click', reloadPreview);
downloadBtnEl.addEventListener('click', downloadSelected);
deleteBtnEl.addEventListener('click', deleteSelected);

init();
