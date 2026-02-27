import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.13.2/firebase-app.js';
import { getAuth, onAuthStateChanged, signOut } from 'https://www.gstatic.com/firebasejs/10.13.2/firebase-auth.js';

const state = {
  user: null,
  projects: [],
  filtered: [],
  selected: null,
  code: 'html',
};

const authStatusEl = document.getElementById('authStatus');
const searchInputEl = document.getElementById('searchInput');
const refreshBtnEl = document.getElementById('refreshBtn');
const projectsGridEl = document.getElementById('projectsGrid');
const emptyStateEl = document.getElementById('emptyState');
const viewerTitleEl = document.getElementById('viewerTitle');
const viewerMetaEl = document.getElementById('viewerMeta');
const viewerCodeEl = document.getElementById('viewerCode');
const viewerPreviewEl = document.getElementById('viewerPreview');
const downloadHtmlBtnEl = document.getElementById('downloadHtmlBtn');
const downloadZipBtnEl = document.getElementById('downloadZipBtn');
const deleteProjectBtnEl = document.getElementById('deleteProjectBtn');
const logoutBtnEl = document.getElementById('logoutBtn');
const codeTabs = document.querySelectorAll('.work-code-tab');

function setStatus(message, isError = false) {
  authStatusEl.textContent = message;
  authStatusEl.style.color = isError ? '#ffb4b4' : 'var(--muted)';
}

function composeDocument(page) {
  return `<!doctype html><html lang="en"><head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /><style>${page.css || ''}</style></head><body>${page.html || ''}<script>${page.js || ''}<' + '/script></body></html>`;
}

function formatTime(value) {
  if (!value) return 'Unknown';
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return 'Unknown';
  return dt.toLocaleString();
}

function renderViewer() {
  const project = state.selected;
  if (!project) {
    viewerTitleEl.textContent = 'Select a project';
    viewerMetaEl.textContent = 'No project selected';
    viewerCodeEl.textContent = '';
    viewerPreviewEl.srcdoc = '';
    return;
  }

  const page = (project.result?.pages || [])[0] || { html: '', css: '', js: '' };
  viewerTitleEl.textContent = project.title || 'Untitled Project';
  viewerMetaEl.textContent = `${project.style || 'modern saas'} • ${formatTime(project.createdAt)}`;
  viewerCodeEl.textContent = page[state.code] || '';
  viewerPreviewEl.srcdoc = composeDocument(page);
  codeTabs.forEach((btn) => btn.classList.toggle('active', btn.dataset.code === state.code));
}

function renderList() {
  projectsGridEl.innerHTML = '';
  emptyStateEl.classList.toggle('hidden', state.filtered.length > 0);

  state.filtered.forEach((item) => {
    const card = document.createElement('article');
    card.className = 'project-card';
    card.innerHTML = `
      <h4>${item.title || 'Untitled Project'}</h4>
      <p>${(item.prompt || '').slice(0, 110)}</p>
      <div class="project-card-meta">
        <span>${item.style || '--'}</span>
        <span>${formatTime(item.createdAt)}</span>
      </div>
    `;
    card.addEventListener('click', () => {
      state.selected = item;
      renderViewer();
    });
    projectsGridEl.appendChild(card);
  });
}

function applySearch() {
  const text = (searchInputEl.value || '').toLowerCase().trim();
  if (!text) {
    state.filtered = [...state.projects];
    renderList();
    return;
  }
  state.filtered = state.projects.filter((p) => `${p.title || ''} ${p.style || ''} ${p.prompt || ''}`.toLowerCase().includes(text));
  renderList();
}

function downloadBlob(name, blob) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

function downloadHtml() {
  const project = state.selected;
  if (!project) return;
  const page = (project.result?.pages || [])[0];
  if (!page) return;
  const html = composeDocument(page);
  downloadBlob(`${(project.title || 'project').toLowerCase().replace(/[^a-z0-9]+/g, '-')}.html`, new Blob([html], { type: 'text/html' }));
}

async function downloadZip() {
  const project = state.selected;
  if (!project || !window.JSZip) return;
  const page = (project.result?.pages || [])[0];
  if (!page) return;
  const zip = new window.JSZip();
  zip.file('index.html', page.html || '');
  zip.file('styles.css', page.css || '');
  zip.file('script.js', page.js || '');
  const blob = await zip.generateAsync({ type: 'blob' });
  downloadBlob(`${(project.title || 'project').toLowerCase().replace(/[^a-z0-9]+/g, '-')}.zip`, blob);
}

async function authHeaders() {
  if (!state.user) return {};
  const token = await state.user.getIdToken();
  return { Authorization: `Bearer ${token}` };
}

async function loadProjects() {
  if (!state.user) return;
  setStatus('Loading saved projects...');
  try {
    const response = await fetch('/api/projects', { headers: await authHeaders() });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || 'Failed to load projects.');
    state.projects = (data.projects || []).slice();
    state.filtered = [...state.projects];
    state.selected = state.filtered[0] || null;
    renderList();
    renderViewer();
    setStatus(`Loaded ${state.projects.length} project(s).`);
  } catch (error) {
    setStatus(error.message || 'Failed to load projects.', true);
  }
}

async function deleteSelectedProject() {
  const project = state.selected;
  if (!project) return;
  if (!confirm(`Delete "${project.title || 'this project'}"?`)) return;
  try {
    const response = await fetch(`/api/projects/${encodeURIComponent(project.id)}`, {
      method: 'DELETE',
      headers: await authHeaders(),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || 'Delete failed.');
    state.projects = state.projects.filter((p) => p.id !== project.id);
    state.filtered = state.filtered.filter((p) => p.id !== project.id);
    state.selected = state.filtered[0] || null;
    renderList();
    renderViewer();
    setStatus('Project deleted.');
  } catch (error) {
    setStatus(error.message || 'Delete failed.', true);
  }
}

async function fetchPublicConfig() {
  const response = await fetch('/api/public-config');
  const data = await response.json();
  if (!response.ok) throw new Error('Unable to load public configuration.');
  return data;
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
        window.location.href = '/auth';
        return;
      }
      state.user = user;
      setStatus(`Authenticated as ${user.email || user.uid}`);
      await loadProjects();
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
refreshBtnEl.addEventListener('click', loadProjects);
downloadHtmlBtnEl.addEventListener('click', downloadHtml);
downloadZipBtnEl.addEventListener('click', downloadZip);
deleteProjectBtnEl.addEventListener('click', deleteSelectedProject);
codeTabs.forEach((btn) => btn.addEventListener('click', () => {
  state.code = btn.dataset.code || 'html';
  renderViewer();
}));

init();
