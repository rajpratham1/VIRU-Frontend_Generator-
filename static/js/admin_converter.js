import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.13.2/firebase-app.js';
import { getAuth, onAuthStateChanged } from 'https://www.gstatic.com/firebasejs/10.13.2/firebase-auth.js';

const state = { user: null };

const adminStatusEl = document.getElementById('adminStatus');
const cleanupDaysEl = document.getElementById('cleanupDays');
const cleanupBtnEl = document.getElementById('cleanupBtn');
const refreshBtnEl = document.getElementById('refreshBtn');
const metricsViewEl = document.getElementById('metricsView');
const recentJobsEl = document.getElementById('recentJobs');

function setStatus(message, isError = false) {
  adminStatusEl.textContent = message;
  adminStatusEl.style.color = isError ? '#ffb4b4' : 'var(--muted)';
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

function renderRecentJobs(jobs = []) {
  recentJobsEl.innerHTML = '';
  if (!jobs.length) {
    recentJobsEl.innerHTML = '<p class="converter-empty">No recent jobs available.</p>';
    return;
  }
  jobs.forEach((job) => {
    const card = document.createElement('article');
    card.className = 'converter-history-card';
    card.innerHTML = `
      <div class="converter-history-head">
        <strong>${job.fileName || 'Untitled Job'}</strong>
        <span>${job.status || 'unknown'}</span>
      </div>
      <p>${job.owner_email || job.owner_uid || 'unknown user'}</p>
      <p>${job.sourceFormat?.toUpperCase() || '?'} -> ${job.targetFormat?.toUpperCase() || '?'} • ${job.aiMode || 'balanced'} AI</p>
      <small>${formatTime(job.createdAt)}</small>
    `;
    recentJobsEl.appendChild(card);
  });
}

async function loadMetrics() {
  setStatus('Loading admin metrics...');
  try {
    const response = await fetch('/api/converter/admin/metrics', { headers: await authHeaders() });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || 'Failed to load admin metrics.');
    metricsViewEl.textContent = JSON.stringify(data.metrics, null, 2);
    renderRecentJobs(data.metrics.recent_jobs || []);
    setStatus('Admin metrics loaded.');
  } catch (error) {
    setStatus(error.message || 'Failed to load admin metrics.', true);
  }
}

async function cleanupOldJobs() {
  const days = Number(cleanupDaysEl.value || 7);
  setStatus(`Cleaning jobs older than ${days} day(s)...`);
  try {
    const response = await fetch('/api/converter/cleanup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
      body: JSON.stringify({ max_age_days: days, scope: 'all' }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || 'Cleanup failed.');
    setStatus(`Cleanup completed. Deleted ${data.cleanup.deleted_jobs} job(s) and ${data.cleanup.deleted_uploads} upload(s).`);
    await loadMetrics();
  } catch (error) {
    setStatus(error.message || 'Cleanup failed.', true);
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
        window.location.href = `/auth?next=${encodeURIComponent('/admin/converter')}`;
        return;
      }
      state.user = user;
      await loadMetrics();
    });
  } catch (error) {
    setStatus(error.message || 'Admin initialization failed.', true);
  }
}

refreshBtnEl.addEventListener('click', loadMetrics);
cleanupBtnEl.addEventListener('click', cleanupOldJobs);

init();
