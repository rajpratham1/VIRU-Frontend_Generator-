import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.13.2/firebase-app.js';
import { getAuth, onAuthStateChanged, signOut } from 'https://www.gstatic.com/firebasejs/10.13.2/firebase-auth.js';

const pageState = {
  user: null,
  mode: document.body.dataset.portfolioMode || 'create',
  portfolioId: document.body.dataset.portfolioId || '',
  selectedTemplate: 'classic',
  photoURL: '',
};

const templateCatalog = [
  { id: 'classic', name: 'Classic Professional', image: '/portfolio-assets/templates/classic.png' },
  { id: 'modern', name: 'Modern Minimalist', image: '/portfolio-assets/templates/modern.png' },
  { id: 'creative', name: 'Creative Bold', image: '/portfolio-assets/templates/creative.png' },
  { id: 'corporate', name: 'Corporate', image: '/portfolio-assets/templates/corporate.png' },
  { id: 'minimalist', name: 'Minimalist', image: '/portfolio-assets/templates/minimalist.png' },
  { id: 'tech', name: 'Tech', image: '/portfolio-assets/templates/tech.png' },
];

const authStatusEl = document.getElementById('portfolioAuthStatus');
const logoutBtnEl = document.getElementById('portfolioLogoutBtn');
const templateGridEl = document.getElementById('templateGrid');
const formEl = document.getElementById('portfolioForm');
const projectsListEl = document.getElementById('projectsList');
const experienceListEl = document.getElementById('experienceList');
const addProjectBtnEl = document.getElementById('addProjectBtn');
const addExperienceBtnEl = document.getElementById('addExperienceBtn');
const formStatusEl = document.getElementById('portfolioFormStatus');
const photoInputEl = document.getElementById('portfolioPhoto');
const photoStatusEl = document.getElementById('portfolioPhotoStatus');
const openPortfolioBtnEl = document.getElementById('openPortfolioBtn');
const projectTemplateEl = document.getElementById('projectTemplate');
const experienceTemplateEl = document.getElementById('experienceTemplate');

function setStatus(message, isError = false) {
  formStatusEl.textContent = message;
  formStatusEl.style.color = isError ? '#ffb4b4' : 'var(--muted)';
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
  const token = await pageState.user.getIdToken();
  return { Authorization: `Bearer ${token}` };
}

function makeEntry(templateEl, values = {}) {
  const fragment = templateEl.content.cloneNode(true);
  const card = fragment.querySelector('.portfolio-entry-card');
  card.querySelectorAll('[data-field]').forEach((field) => {
    field.value = values[field.dataset.field] || '';
  });
  card.querySelector('.entry-remove-btn').addEventListener('click', () => card.remove());
  return fragment;
}

function collectEntries(root) {
  return Array.from(root.querySelectorAll('.portfolio-entry-card')).map((card) => {
    const item = {};
    card.querySelectorAll('[data-field]').forEach((field) => {
      item[field.dataset.field] = field.value.trim();
    });
    return item;
  }).filter((item) => Object.values(item).some(Boolean));
}

function renderTemplates() {
  templateGridEl.innerHTML = '';
  templateCatalog.forEach((template) => {
    const card = document.createElement('article');
    card.className = 'portfolio-template-card';
    if (template.id === pageState.selectedTemplate) card.classList.add('active');
    card.innerHTML = `
      <img src="${template.image}" alt="${template.name}" />
      <div class="portfolio-template-copy">
        <strong>${template.name}</strong>
        <div class="portfolio-template-actions">
          <button type="button" class="ghost-btn template-select-btn">Use Template</button>
          <a href="/preview/${template.id}" target="_blank" rel="noopener noreferrer" class="ghost-link">Preview</a>
        </div>
      </div>
    `;
    card.querySelector('.template-select-btn').addEventListener('click', () => {
      pageState.selectedTemplate = template.id;
      renderTemplates();
    });
    templateGridEl.appendChild(card);
  });
}

function payloadFromForm() {
  return {
    name: document.getElementById('portfolioName').value.trim(),
    headline: document.getElementById('portfolioHeadline').value.trim(),
    bio: document.getElementById('portfolioBio').value.trim(),
    skills: document.getElementById('portfolioSkills').value.split(',').map((item) => item.trim()).filter(Boolean),
    contact: {
      email: document.getElementById('portfolioEmail').value.trim(),
      linkedin: document.getElementById('portfolioLinkedin').value.trim(),
      github: document.getElementById('portfolioGithub').value.trim(),
      twitter: document.getElementById('portfolioTwitter').value.trim(),
    },
    projects: collectEntries(projectsListEl),
    experience: collectEntries(experienceListEl),
    template: pageState.selectedTemplate,
    photoURL: pageState.photoURL,
  };
}

function fillForm(portfolio) {
  document.getElementById('portfolioName').value = portfolio.name || '';
  document.getElementById('portfolioHeadline').value = portfolio.headline || '';
  document.getElementById('portfolioBio').value = portfolio.bio || '';
  document.getElementById('portfolioSkills').value = (portfolio.skills || []).join(', ');
  document.getElementById('portfolioEmail').value = portfolio.contact?.email || '';
  document.getElementById('portfolioLinkedin').value = portfolio.contact?.linkedin || '';
  document.getElementById('portfolioGithub').value = portfolio.contact?.github || '';
  document.getElementById('portfolioTwitter').value = portfolio.contact?.twitter || '';
  pageState.selectedTemplate = portfolio.template || 'classic';
  pageState.photoURL = portfolio.photoURL || '';
  photoStatusEl.textContent = pageState.photoURL ? 'Existing photo connected.' : 'No photo uploaded.';
  projectsListEl.innerHTML = '';
  experienceListEl.innerHTML = '';
  (portfolio.projects || []).forEach((item) => projectsListEl.appendChild(makeEntry(projectTemplateEl, item)));
  (portfolio.experience || []).forEach((item) => experienceListEl.appendChild(makeEntry(experienceTemplateEl, item)));
  if (!projectsListEl.children.length) projectsListEl.appendChild(makeEntry(projectTemplateEl));
  if (!experienceListEl.children.length) experienceListEl.appendChild(makeEntry(experienceTemplateEl));
  renderTemplates();
  openPortfolioBtnEl.href = `/u/${portfolio.id}`;
  openPortfolioBtnEl.classList.remove('hidden');
}

async function uploadPhotoIfNeeded() {
  const file = photoInputEl.files?.[0];
  if (!file) return;
  const body = new FormData();
  body.append('photo', file);
  photoStatusEl.textContent = 'Uploading photo...';
  const response = await fetch('/api/portfolios/photo', {
    method: 'POST',
    headers: await authHeaders(),
    body,
  });
  const data = await response.json();
  if (!response.ok || !data.ok) throw new Error(data.error || 'Photo upload failed.');
  pageState.photoURL = data.photoURL;
  photoStatusEl.textContent = 'Photo uploaded successfully.';
}

async function loadExistingPortfolio() {
  if (pageState.mode !== 'edit' || !pageState.portfolioId) return;
  const response = await fetch(`/api/portfolios/${encodeURIComponent(pageState.portfolioId)}`, {
    headers: await authHeaders(),
  });
  const data = await response.json();
  if (!response.ok || !data.ok) throw new Error(data.error || 'Failed to load portfolio.');
  fillForm(data.portfolio);
  setStatus('Portfolio loaded for editing.');
}

async function savePortfolio(event) {
  event.preventDefault();
  try {
    await uploadPhotoIfNeeded();
    const payload = payloadFromForm();
    if (!payload.name || !payload.bio) {
      throw new Error('Name and bio are required.');
    }
    setStatus(pageState.mode === 'edit' ? 'Updating portfolio...' : 'Saving portfolio...');
    const response = await fetch(
      pageState.mode === 'edit' ? `/api/portfolios/${encodeURIComponent(pageState.portfolioId)}` : '/api/portfolios',
      {
        method: pageState.mode === 'edit' ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
        body: JSON.stringify(payload),
      }
    );
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || 'Failed to save portfolio.');
    pageState.portfolioId = data.portfolio.id;
    pageState.mode = 'edit';
    openPortfolioBtnEl.href = `/u/${data.portfolio.id}`;
    openPortfolioBtnEl.classList.remove('hidden');
    setStatus('Portfolio saved successfully.');
  } catch (error) {
    setStatus(error.message || 'Save failed.', true);
  }
}

async function init() {
  renderTemplates();
  projectsListEl.appendChild(makeEntry(projectTemplateEl));
  experienceListEl.appendChild(makeEntry(experienceTemplateEl));

  try {
    const cfg = await fetchPublicConfig();
    const firebaseCfg = cfg.firebase || {};
    const missing = ['apiKey', 'authDomain', 'projectId', 'appId'].filter((k) => !firebaseCfg[k]);
    if (missing.length) throw new Error(`Firebase env is incomplete: missing ${missing.join(', ')}`);
    const app = initializeApp(firebaseCfg);
    const auth = getAuth(app);
    onAuthStateChanged(auth, async (user) => {
      if (!user) {
        window.location.href = `/auth?next=${encodeURIComponent(window.location.pathname)}`;
        return;
      }
      pageState.user = user;
      setAuthStatus(`Signed in as ${user.email || user.uid}`);
      await loadExistingPortfolio();
    });
    logoutBtnEl.addEventListener('click', async () => {
      await signOut(auth);
      window.location.href = '/auth';
    });
  } catch (error) {
    setAuthStatus(error.message || 'Portfolio initialization failed.', true);
    setStatus(error.message || 'Portfolio initialization failed.', true);
  }
}

formEl.addEventListener('submit', savePortfolio);
addProjectBtnEl.addEventListener('click', () => projectsListEl.appendChild(makeEntry(projectTemplateEl)));
addExperienceBtnEl.addEventListener('click', () => experienceListEl.appendChild(makeEntry(experienceTemplateEl)));

init();
