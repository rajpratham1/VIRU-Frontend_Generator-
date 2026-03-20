import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.13.2/firebase-app.js';
import { getAuth, onAuthStateChanged, signOut } from 'https://www.gstatic.com/firebasejs/10.13.2/firebase-auth.js';

const state = { user: null };

const authStatusEl = document.getElementById('portfolioDashboardAuthStatus');
const statusEl = document.getElementById('portfolioDashboardStatus');
const listEl = document.getElementById('portfolioDashboardList');
const refreshBtnEl = document.getElementById('portfolioDashboardRefreshBtn');
const logoutBtnEl = document.getElementById('portfolioDashboardLogoutBtn');

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.style.color = isError ? '#ffb4b4' : 'var(--muted)';
}

function setAuthStatus(message, isError = false) {
  authStatusEl.textContent = message;
  authStatusEl.style.color = isError ? '#ffb4b4' : 'var(--muted)';
}

async function fetchPublicConfig() {
  const response = await fetch('/api/public-config');
  const data = await response.json();
  if (!response.ok) throw new Error('Unable to load public configuration.');
  return data;
}

async function authHeaders() {
  const token = await state.user.getIdToken();
  return { Authorization: `Bearer ${token}` };
}

function renderPortfolios(portfolios) {
  listEl.innerHTML = '';
  if (!portfolios.length) {
    listEl.innerHTML = '<article class="portfolio-dashboard-card"><h4>No portfolios yet</h4><p>Create your first portfolio from the builder.</p><a href="/generate" class="ghost-link">Open Builder</a></article>';
    return;
  }

  portfolios.forEach((item) => {
    const card = document.createElement('article');
    card.className = 'portfolio-dashboard-card';
    card.innerHTML = `
      <h4>${item.name || 'Untitled Portfolio'}</h4>
      <p>${item.headline || 'No headline added.'}</p>
      <span>${item.template || 'classic'} • ${new Date(item.updatedAt || item.createdAt || Date.now()).toLocaleString()}</span>
      <div class="portfolio-template-actions">
        <a href="/u/${item.id}" target="_blank" rel="noopener noreferrer" class="ghost-link">Open</a>
        <a href="/edit/${item.id}" class="ghost-link">Edit</a>
        <button type="button" class="ghost-btn delete-btn">Delete</button>
      </div>
    `;
    card.querySelector('.delete-btn').addEventListener('click', async () => {
      if (!confirm(`Delete "${item.name || 'this portfolio'}"?`)) return;
      const response = await fetch(`/api/portfolios/${encodeURIComponent(item.id)}`, {
        method: 'DELETE',
        headers: await authHeaders(),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        setStatus(data.error || 'Failed to delete portfolio.', true);
        return;
      }
      await loadPortfolios();
    });
    listEl.appendChild(card);
  });
}

async function loadPortfolios() {
  try {
    setStatus('Loading portfolios...');
    const response = await fetch('/api/portfolios', { headers: await authHeaders() });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || 'Failed to load portfolios.');
    renderPortfolios(data.portfolios || []);
    setStatus(`Loaded ${data.portfolios.length} portfolio(s).`);
  } catch (error) {
    setStatus(error.message || 'Failed to load portfolios.', true);
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
        window.location.href = '/auth?next=/dashboard';
        return;
      }
      state.user = user;
      setAuthStatus(`Signed in as ${user.email || user.uid}`);
      await loadPortfolios();
    });
    refreshBtnEl.addEventListener('click', loadPortfolios);
    logoutBtnEl.addEventListener('click', async () => {
      await signOut(auth);
      window.location.href = '/auth';
    });
  } catch (error) {
    setAuthStatus(error.message || 'Dashboard initialization failed.', true);
    setStatus(error.message || 'Dashboard initialization failed.', true);
  }
}

init();
