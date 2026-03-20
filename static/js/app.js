import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.13.2/firebase-app.js';
import { getAuth, onAuthStateChanged, signOut } from 'https://www.gstatic.com/firebasejs/10.13.2/firebase-auth.js';

const state = { user: null, result: null, pageIndex: 0, activeCode: 'html', recent: [], shareMode: 'edit', shareId: '', shareOwner: '' };

const promptEl = document.getElementById('prompt');
const styleEl = document.getElementById('style');
const pagesEl = document.getElementById('pages');
const qualityPresetEl = document.getElementById('qualityPreset');
const strictModeEl = document.getElementById('strictMode');
const rewriteModeEl = document.getElementById('rewriteMode');
const autoAssistModeEl = document.getElementById('autoAssistMode');
const enhancePromptBtn = document.getElementById('enhancePromptBtn');
const cloneUrlEl = document.getElementById('cloneUrl');
const pasteUrlBtn = document.getElementById('pasteUrlBtn');
const analyzeUrlBtn = document.getElementById('analyzeUrlBtn');
const cloneStatusEl = document.getElementById('cloneStatus');
const healthBtn = document.getElementById('healthBtn');
const generateBtn = document.getElementById('generateBtn');
const statusEl = document.getElementById('status');
const queueBadgeEl = document.getElementById('queueBadge');
const queueFillEl = document.getElementById('queueFill');
const authStatusEl = document.getElementById('authStatus');
const outputTitleEl = document.getElementById('outputTitle');
const outputSourceEl = document.getElementById('outputSource');
const pageTabsEl = document.getElementById('pageTabs');
const codeViewEl = document.getElementById('codeView');
const logsViewEl = document.getElementById('logsView');
const codeTabEls = document.querySelectorAll('.code-tab');
const previewEl = document.getElementById('preview');
const copyBtn = document.getElementById('copyBtn');
const downloadBtn = document.getElementById('downloadBtn');
const combinedBtn = document.getElementById('combinedBtn');
const exportZipBtn = document.getElementById('exportZipBtn');
const exportReactBtn = document.getElementById('exportReactBtn');
const exportNextBtn = document.getElementById('exportNextBtn');
const createShareBtn = document.getElementById('createShareBtn');
const sharePermissionEl = document.getElementById('sharePermission');
const shareLinkEl = document.getElementById('shareLink');
const publicShareLinkEl = document.getElementById('publicShareLink');
const editShareLinkEl = document.getElementById('editShareLink');
const shareStatusEl = document.getElementById('shareStatus');
const deployNetlifyBtn = document.getElementById('deployNetlifyBtn');
const deployVercelBtn = document.getElementById('deployVercelBtn');
const deployGithubBtn = document.getElementById('deployGithubBtn');
const deployNowBtn = document.getElementById('deployNowBtn');
const deployedUrlEl = document.getElementById('deployedUrl');
const deployStatusEl = document.getElementById('deployStatus');
const logoutBtnEl = document.getElementById('logoutBtn');
const recentListEl = document.getElementById('recentList');
const totalGenerationsEl = document.getElementById('totalGenerations');
const avgLatencyEl = document.getElementById('avgLatency');
const lastQualityEl = document.getElementById('lastQuality');
const qualityScoreEl = document.getElementById('qualityScore');
const validationSummaryEl = document.getElementById('validationSummary');
const latencySummaryEl = document.getElementById('latencySummary');
const promptHintsEl = document.getElementById('promptHints');
const settingsToggleEl = document.getElementById('settingsToggle');
const settingsDrawerEl = document.getElementById('settingsDrawer');
const suggestFormEl = document.getElementById('suggestForm');
const suggestStatusEl = document.getElementById('suggestStatus');
const mobileTabs = document.querySelectorAll('.mobile-tab');
const promptPanelEl = document.getElementById('promptPanel');
const outputPanelEl = document.getElementById('outputPanel');
const logsPanelEl = document.getElementById('logsPanel');
const templateButtons = document.querySelectorAll('.template-btn');
const templateLibraryEl = document.getElementById('templateLibrary');
const templateCategoriesEl = document.getElementById('templateCategories');
const introOverlayEl = document.getElementById('introOverlay');
const skipIntroBtnEl = document.getElementById('skipIntroBtn');
const introVideoEl = document.getElementById('introVideo');
const introMediaWrapEl = document.querySelector('.intro-media-wrap');

const TEMPLATE_LIBRARY = [
  { id: 'saas-pricing', category: 'saas', title: 'SaaS Pricing Funnel', style: 'modern saas', pages: 1, prompt: 'Build a SaaS landing page with hero, feature grid, pricing tiers, FAQ, testimonials, and final CTA.' },
  { id: 'saas-product', category: 'saas', title: 'Product Launch', style: 'clean fintech', pages: 2, prompt: 'Generate product launch website for B2B automation with features, integrations, case studies, and sign-up flow.' },
  { id: 'portfolio-dev', category: 'portfolio', title: 'Developer Portfolio', style: 'editorial bold', pages: 1, prompt: 'Create a senior frontend developer portfolio with hero, selected work, services, testimonials, and contact section.' },
  { id: 'portfolio-creator', category: 'portfolio', title: 'Creator Portfolio', style: 'playful startup', pages: 1, prompt: 'Design a creator portfolio page with case studies, social proof, media kit CTA, and booking section.' },
  { id: 'ecom-d2c', category: 'ecommerce', title: 'D2C Product Page', style: 'playful startup', pages: 2, prompt: 'Build an ecommerce experience for a D2C brand with hero, catalog highlights, reviews, FAQ, and checkout CTA.' },
  { id: 'agency-site', category: 'agency', title: 'Digital Agency', style: 'editorial bold', pages: 2, prompt: 'Create an agency website with services, process, client logos, project stories, and lead generation form.' },
];

const PROMPT_TEMPLATES = {
  saas: 'Build a modern SaaS landing page for an AI analytics platform. Include hero, features, pricing, testimonials, FAQ, and contact. Target product managers. Tone: confident and crisp. CTA: Start free trial.',
  portfolio: 'Create a portfolio website for a senior frontend engineer. Include hero, selected projects, services, testimonials, and contact form. Tone: professional and creative. CTA: Book a call.',
  ecommerce: 'Design a clean ecommerce landing page for a sustainable lifestyle store. Include hero, product highlights, social proof, FAQ, and signup. Tone: warm and trustworthy. CTA: Shop now.',
};

const setStatus = (m, e = false) => { statusEl.textContent = m; statusEl.style.color = e ? '#ffb4b4' : 'var(--muted)'; };
const setShareStatus = (m, e = false) => { shareStatusEl.textContent = m; shareStatusEl.style.color = e ? '#ffb4b4' : 'var(--muted)'; };
const setDeployStatus = (m, e = false) => { deployStatusEl.textContent = m; deployStatusEl.style.color = e ? '#ffb4b4' : 'var(--muted)'; };
const setCloneStatus = (m, e = false) => { cloneStatusEl.textContent = m; cloneStatusEl.style.color = e ? '#ffb4b4' : 'var(--muted)'; };
const setSuggestStatus = (m, e = false) => { suggestStatusEl.textContent = m; suggestStatusEl.style.color = e ? '#ffb4b4' : 'var(--muted)'; };
const sourceLabel = (source) => (source === 'groq' ? 'Groq model output' : source === 'openai' ? 'OpenAI model output' : 'Fallback output');
const currentPage = () => (state.result?.pages || [])[state.pageIndex] || null;
let introTimer = null;
let introEndedBound = false;

function composePreviewDocument(page) {
  return `<!doctype html><html lang="en"><head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /><style>${page.css || ''}</style></head><body>${page.html || ''}<script>${page.js || ''}<' + '/script></body></html>`;
}

function updateQueue(stateName) {
  const map = { idle: 0, queued: 20, running: 60, retrying: 78, done: 100 };
  queueBadgeEl.textContent = `Queue: ${stateName}`;
  queueFillEl.style.width = `${map[stateName] || 0}%`;
}

function renderCode() {
  const page = currentPage();
  if (!page) { codeViewEl.textContent = ''; previewEl.srcdoc = ''; return; }
  codeViewEl.textContent = page[state.activeCode] || '';
  previewEl.srcdoc = composePreviewDocument(page);
  codeTabEls.forEach((b) => b.classList.toggle('active', b.dataset.code === state.activeCode));
}

function renderPageTabs() {
  pageTabsEl.innerHTML = '';
  (state.result?.pages || []).forEach((page, idx) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = page.name || `Page ${idx + 1}`;
    btn.classList.toggle('active', idx === state.pageIndex);
    btn.addEventListener('click', () => { state.pageIndex = idx; renderPageTabs(); renderCode(); });
    pageTabsEl.appendChild(btn);
  });
}

const renderLogs = (logs) => { logsViewEl.textContent = logs ? JSON.stringify(logs, null, 2) : 'No logs yet.'; };

function updateQualitySummary(logs) {
  if (!logs) { qualityScoreEl.textContent = '--'; validationSummaryEl.textContent = '--'; latencySummaryEl.textContent = '--'; return; }
  const lastAttempt = (logs.attempts || [])[logs.attempts?.length - 1] || {};
  const score = Math.max(0, 100 - ((lastAttempt.critical_errors || []).length * 20) - ((lastAttempt.soft_errors || []).length * 5));
  qualityScoreEl.textContent = `${score}/100`;
  validationSummaryEl.textContent = (lastAttempt.critical_errors || []).length ? 'Critical issues' : (lastAttempt.soft_errors || []).length ? 'Minor issues' : 'Clean';
  latencySummaryEl.textContent = `${logs.latency_ms || 0} ms`;
}

function getPromptHints(text) {
  const t = text.toLowerCase();
  const hints = [];
  if (t.length < 80) hints.push('Add more detail (goal, audience, tone).');
  if (!/audience|customer|user|buyer|client/.test(t)) hints.push('Mention target audience.');
  if (!/tone|style|brand|voice/.test(t)) hints.push('Add tone/style guidance.');
  if (!/cta|call to action|book|start|subscribe|buy|signup/.test(t)) hints.push('Add CTA intent.');
  if (!/pricing|faq|testimonial|feature|contact|about/.test(t)) hints.push('List required sections.');
  return hints;
}

function updatePromptHints() {
  const hints = getPromptHints(promptEl.value);
  promptHintsEl.textContent = hints.length ? `Prompt quality: ${hints.join(' ')}` : 'Prompt quality: strong. You included audience, tone, sections, and CTA.';
}

function enhancePrompt(text) {
  let out = text.trim();
  const lower = out.toLowerCase();
  if (!/audience|customer|user|buyer|client/.test(lower)) out += ' Target audience: startup founders and product teams.';
  if (!/tone|style|brand|voice/.test(lower)) out += ' Tone: professional, modern, and concise.';
  if (!/cta|call to action|book|start|subscribe|buy|signup/.test(lower)) out += ' Primary CTA: Start free trial now.';
  if (!/hero|features|pricing|faq|testimonial|contact/.test(lower)) out += ' Required sections: hero, features, pricing, testimonials, FAQ, and contact.';
  return out;
}

function renderRecent() {
  const saved = localStorage.getItem('viru_recent');
  if (saved) { try { state.recent = JSON.parse(saved) || []; } catch { state.recent = []; } }
  recentListEl.innerHTML = '';
  state.recent.forEach((item) => { const li = document.createElement('li'); li.innerHTML = `<strong>${item.title}</strong><br /><span>${item.summary}</span>`; recentListEl.appendChild(li); });
  totalGenerationsEl.textContent = state.recent.length;
  avgLatencyEl.textContent = `${Math.round(state.recent.reduce((acc, cur) => acc + cur.latency, 0) / Math.max(1, state.recent.length))} ms`;
  lastQualityEl.textContent = state.recent[0]?.quality || '--';
}

function saveRecentGeneration(record) {
  state.recent.unshift(record);
  state.recent = state.recent.slice(0, 5);
  localStorage.setItem('viru_recent', JSON.stringify(state.recent));
  renderRecent();
}

function setMobileView(view) {
  const map = { prompt: promptPanelEl, output: outputPanelEl, logs: logsPanelEl };
  mobileTabs.forEach((btn) => btn.classList.toggle('active', btn.dataset.view === view));
  Object.entries(map).forEach(([key, el]) => el.classList.toggle('view-active', key === view));
}

function toggleSettingsDrawer() {
  const opened = settingsDrawerEl.classList.toggle('is-open');
  settingsDrawerEl.setAttribute('aria-hidden', String(!opened));
}

function closeIntroOverlay() {
  if (!introOverlayEl) return;
  introOverlayEl.classList.add('hidden');
  introOverlayEl.setAttribute('aria-hidden', 'true');
  document.body.classList.remove('intro-lock');
  if (introVideoEl) {
    introVideoEl.pause();
    introVideoEl.currentTime = 0;
    introVideoEl.muted = true;
  }
  if (introTimer) {
    clearTimeout(introTimer);
    introTimer = null;
  }
}

function handleIntroMediaFail() {
  if (introMediaWrapEl) {
    introMediaWrapEl.classList.add('media-failed');
  }
  if (introTimer) {
    clearTimeout(introTimer);
    introTimer = null;
  }
  introTimer = setTimeout(closeIntroOverlay, 1200);
}

function openIntroOverlay() {
  if (!introOverlayEl) return;
  introOverlayEl.classList.remove('hidden');
  introOverlayEl.setAttribute('aria-hidden', 'false');
  document.body.classList.add('intro-lock');
  if (introVideoEl) {
    introVideoEl.muted = true;
    introVideoEl.loop = false;
    introVideoEl.currentTime = 0;
    if (!introEndedBound) {
      introVideoEl.addEventListener('ended', closeIntroOverlay);
      introVideoEl.addEventListener('error', handleIntroMediaFail);
      introEndedBound = true;
    }
    introVideoEl.play().catch(handleIntroMediaFail);
    const durationMs =
      Number.isFinite(introVideoEl.duration) && introVideoEl.duration > 0
        ? Math.min(12000, Math.max(3500, Math.round(introVideoEl.duration * 1000) + 300))
        : 5500;
    introTimer = setTimeout(closeIntroOverlay, durationMs);
    return;
  }
  introTimer = setTimeout(closeIntroOverlay, 5500);
}

function renderTemplateLibrary(category = 'all') {
  templateLibraryEl.innerHTML = '';
  const list = category === 'all' ? TEMPLATE_LIBRARY : TEMPLATE_LIBRARY.filter((item) => item.category === category);
  list.forEach((item) => {
    const card = document.createElement('article');
    card.className = 'template-card';
    card.innerHTML = `<h5>${item.title}</h5><p>${item.category.toUpperCase()} • ${item.style}</p>`;
    const remixBtn = document.createElement('button');
    remixBtn.type = 'button';
    remixBtn.className = 'ghost-btn';
    remixBtn.textContent = 'Remix';
    remixBtn.addEventListener('click', () => { promptEl.value = item.prompt; styleEl.value = item.style; pagesEl.value = item.pages; updatePromptHints(); setStatus(`Template loaded: ${item.title}`); });
    card.appendChild(remixBtn);
    templateLibraryEl.appendChild(card);
  });
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

async function runHealthCheck() {
  healthBtn.disabled = true;
  setStatus('Checking provider health...');
  try {
    const response = await fetch('/api/health', { headers: await authHeaders() });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || 'Health check failed');
    renderLogs({ health: data });
    setStatus(data.ok ? `Health check passed. Provider=${data.provider}, Model=${data.model}` : `Health check failed: ${data.message}`, !data.ok);
  } catch (error) {
    setStatus(error.message || 'Health check failed.', true);
  } finally {
    healthBtn.disabled = false;
  }
}

async function analyzeUrl() {
  const target = cloneUrlEl.value.trim();
  if (!target) { setCloneStatus('Enter a URL to analyze.', true); return; }
  analyzeUrlBtn.disabled = true;
  setCloneStatus('Analyzing URL...');
  try {
    const response = await fetch('/api/analyze-url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
      body: JSON.stringify({ url: target }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || 'Analysis failed.');
    const analysis = data.analysis || {};
    promptEl.value = analysis.prompt || promptEl.value;
    styleEl.value = analysis.style || styleEl.value;
    pagesEl.value = analysis.recommended_pages || pagesEl.value;
    updatePromptHints();
    setCloneStatus(`Analyzed: ${analysis.title || analysis.url}. Prompt remixed.`);
  } catch (error) {
    setCloneStatus(error.message || 'Clone analysis failed.', true);
  } finally {
    analyzeUrlBtn.disabled = false;
  }
}

async function pasteCloneUrl() {
  if (!cloneUrlEl) return;
  try {
    const text = (await navigator.clipboard.readText()).trim();
    if (!text) {
      setCloneStatus('Clipboard is empty.', true);
      return;
    }
    cloneUrlEl.value = text;
    cloneUrlEl.focus();
    setCloneStatus('URL pasted. Click Analyze & Remix.');
  } catch {
    setCloneStatus('Clipboard permission blocked. Paste manually or allow clipboard access.', true);
  }
}

function applyResult(data) {
  state.result = data;
  state.pageIndex = 0;
  state.activeCode = 'html';
  outputTitleEl.textContent = data.title || 'Generated Output';
  outputSourceEl.textContent = sourceLabel(data.source);
  renderPageTabs();
  renderCode();
  renderLogs(data.logs || null);
  updateQualitySummary(data.logs || null);
}

function applyWorkspaceMeta(workspace = {}) {
  if (typeof workspace.prompt === 'string' && workspace.prompt.trim()) {
    promptEl.value = workspace.prompt;
  }
  if (typeof workspace.style === 'string' && workspace.style.trim()) {
    styleEl.value = workspace.style;
  }
  if (workspace.pages) {
    pagesEl.value = String(workspace.pages);
  }
  updatePromptHints();
}

async function saveSharedWorkspace(result, promptText) {
  if (!state.shareId || state.shareMode !== 'edit' || !result) return;
  const response = await fetch(`/api/share/${encodeURIComponent(state.shareId)}/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
    body: JSON.stringify({
      title: result.title || outputTitleEl.textContent || 'Generated Output',
      prompt: promptText,
      style: styleEl.value,
      pages: Number(pagesEl.value || 1),
      result,
    }),
  });
  const data = await response.json();
  if (!response.ok || !data.ok) {
    throw new Error(data.error || 'Failed to save shared edits.');
  }
  if (publicShareLinkEl) publicShareLinkEl.value = data.share?.public_share_link || publicShareLinkEl.value;
  if (editShareLinkEl) editShareLinkEl.value = data.share?.edit_share_link || editShareLinkEl.value;
}

async function saveProjectToCloud(result, promptText) {
  if (!state.user || !result) return;
  try {
    const response = await fetch('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
      body: JSON.stringify({
        title: result.title || 'Generated Output',
        prompt: promptText,
        style: styleEl.value,
        pages: Number(pagesEl.value || 1),
        source: result.source || 'unknown',
        qualityScore: qualityScoreEl.textContent || '--',
        latencyMs: result.logs?.latency_ms || 0,
        result,
      }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || 'Failed to save project.');
    }
  } catch (error) {
    setStatus(`Generated, but cloud save failed: ${error.message || 'Unknown error'}`, true);
  }
}

async function generateWebsite() {
  if (state.shareMode === 'view') { setStatus('This shared project is view-only.', true); return; }
  let prompt = promptEl.value.trim();
  if (!prompt) { setStatus('Prompt is required.', true); return; }
  if (autoAssistModeEl.checked) { prompt = enhancePrompt(prompt); promptEl.value = prompt; updatePromptHints(); }

  generateBtn.disabled = true;
  setStatus('Generation queued...');
  updateQueue('queued');

  let attempt = 0;
  while (attempt < 2) {
    try {
      await new Promise((r) => setTimeout(r, 250));
      updateQueue(attempt === 0 ? 'running' : 'retrying');
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
        body: JSON.stringify({ prompt, style: styleEl.value, pages: Number(pagesEl.value || 1), quality_preset: qualityPresetEl.value, strict_mode: strictModeEl.checked, rewrite_mode: rewriteModeEl.checked }),
      });
      const data = await response.json();
      if (!response.ok || data.ok === false) throw new Error(data.error || 'Generation failed');
      applyResult(data);
      updateQueue('done');
      setStatus('Website generated successfully.');
      saveRecentGeneration({ title: data.title || 'Generated Output', summary: (data.summary || '').slice(0, 120), latency: data.logs?.latency_ms || 0, quality: qualityScoreEl.textContent });
      await saveProjectToCloud(data, prompt);
      if (state.shareMode === 'edit' && state.shareId) {
        await saveSharedWorkspace(data, prompt);
        setShareStatus(`Shared editor updated${state.shareOwner ? ` for ${state.shareOwner}` : ''}.`);
      }
      generateBtn.disabled = false;
      return;
    } catch (error) {
      attempt += 1;
      if (attempt >= 2) { updateQueue('done'); setStatus(error.message || 'Generation failed.', true); break; }
      setStatus('Retrying generation...');
      renderLogs({ retry: attempt, message: error.message || 'Retrying' });
    }
  }
  generateBtn.disabled = false;
}

function downloadBlob(name, blob) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

async function exportZipBundle() {
  const page = currentPage();
  if (!page || !window.JSZip) { setStatus('Generate output before exporting.', true); return; }
  const zip = new window.JSZip();
  zip.file('index.html', page.html || '');
  zip.file('styles.css', page.css || '');
  zip.file('script.js', page.js || '');
  downloadBlob('viru-export.zip', await zip.generateAsync({ type: 'blob' }));
  setStatus('ZIP exported (index.html, styles.css, script.js).');
}

async function exportReactStarter() {
  const page = currentPage();
  if (!page || !window.JSZip) { setStatus('Generate output before exporting.', true); return; }
  const zip = new window.JSZip();
  const appJsx = `import { useEffect } from 'react';\\nimport './styles.css';\\nconst html = ${JSON.stringify(page.html || '')};\\nconst jsCode = ${JSON.stringify(page.js || '')};\\nexport default function App(){useEffect(()=>{if(!jsCode)return;const s=document.createElement('script');s.textContent=jsCode;document.body.appendChild(s);return ()=>document.body.removeChild(s);},[]);return <div dangerouslySetInnerHTML={{ __html: html }} />;}`;
  zip.file('package.json', JSON.stringify({ name: 'viru-react-starter', private: true, version: '1.0.0', scripts: { dev: 'vite' }, dependencies: { react: '^18.3.1', 'react-dom': '^18.3.1' }, devDependencies: { vite: '^5.4.0' } }, null, 2));
  zip.file('index.html', '<!doctype html><html><body><div id=\"root\"></div><script type=\"module\" src=\"/src/main.jsx\"></script></body></html>');
  zip.file('src/main.jsx', "import React from 'react';\\nimport ReactDOM from 'react-dom/client';\\nimport App from './App.jsx';\\nReactDOM.createRoot(document.getElementById('root')).render(<App />);\\n");
  zip.file('src/App.jsx', appJsx);
  zip.file('src/styles.css', page.css || '');
  downloadBlob('viru-react-starter.zip', await zip.generateAsync({ type: 'blob' }));
  setStatus('React starter exported.');
}

async function exportNextStarter() {
  const page = currentPage();
  if (!page || !window.JSZip) { setStatus('Generate output before exporting.', true); return; }
  const zip = new window.JSZip();
  zip.file('package.json', JSON.stringify({ name: 'viru-next-starter', private: true, version: '1.0.0', scripts: { dev: 'next dev' }, dependencies: { next: '14.2.5', react: '^18.3.1', 'react-dom': '^18.3.1' } }, null, 2));
  zip.file('app/page.jsx', `export default function Page(){return <main dangerouslySetInnerHTML={{ __html: ${JSON.stringify(page.html || '')} }} />;}`);
  zip.file('app/globals.css', page.css || '');
  zip.file('README.md', `Place custom JS from generated output manually in component hooks.\\n\\nGenerated JS:\\n\\n${page.js || ''}`);
  downloadBlob('viru-next-starter.zip', await zip.generateAsync({ type: 'blob' }));
  setStatus('Next starter exported.');
}

async function createShareLink() {
  if (!state.result) { setShareStatus('Generate a project first.', true); return; }
  try {
    const response = await fetch('/api/share', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
      body: JSON.stringify({
        title: state.result?.title || outputTitleEl.textContent || 'Generated Output',
        prompt: promptEl.value.trim(),
        style: styleEl.value,
        pages: Number(pagesEl.value || 1),
        result: state.result,
        permission: sharePermissionEl.value,
      }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || 'Share link creation failed.');
    shareLinkEl.value = data.share_link;
    if (publicShareLinkEl) publicShareLinkEl.value = data.public_share_link || '';
    if (editShareLinkEl) editShareLinkEl.value = data.edit_share_link || '';
    await navigator.clipboard.writeText(data.share_link);
    setShareStatus(
      data.permission === 'edit'
        ? 'Editor link created and copied. Public website link is also ready below.'
        : 'Public website link created and copied. It opens directly without login.'
    );
  } catch (error) {
    setShareStatus(error.message || 'Share link creation failed.', true);
  }
}

async function loadSharedProjectIfPresent() {
  const params = new URLSearchParams(window.location.search);
  const shareId = params.get('share');
  const perm = params.get('perm') || 'view';
  if (!shareId) return;
  try {
    const response = await fetch(`/api/share/${encodeURIComponent(shareId)}?perm=${encodeURIComponent(perm)}`, { headers: await authHeaders() });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || 'Failed to load shared project.');
    state.shareId = shareId;
    state.shareMode = data.mode || 'view';
    state.shareOwner = data.share?.owner_email || '';
    applyResult(data.result || {});
    applyWorkspaceMeta(data.workspace || {});
    if (publicShareLinkEl) publicShareLinkEl.value = data.share?.public_share_link || '';
    if (editShareLinkEl) editShareLinkEl.value = data.share?.edit_share_link || '';
    if (shareLinkEl) shareLinkEl.value = state.shareMode === 'edit' ? (data.share?.edit_share_link || '') : (data.share?.public_share_link || '');
    setShareStatus(`Loaded shared project by ${data.share?.owner_email || 'team'} in ${state.shareMode} mode.`);
    if (state.shareMode === 'view') {
      [promptEl, styleEl, pagesEl, qualityPresetEl, strictModeEl, rewriteModeEl, generateBtn, analyzeUrlBtn, enhancePromptBtn, cloneUrlEl, pasteUrlBtn].forEach((el) => {
        if (el) el.disabled = true;
      });
      setStatus('View-only share mode enabled.');
    } else {
      setStatus('Edit share loaded. Regenerate to publish updated changes to this shared workspace.');
    }
  } catch (error) {
    setShareStatus(error.message || 'Failed to load shared project.', true);
  }
}

const openDeploy = (url, label) => { window.open(url, '_blank', 'noopener,noreferrer'); setDeployStatus(`Opened ${label}. Use exported ZIP to complete deployment.`); };

async function deployCurrentPage() {
  if (!state.result) {
    setDeployStatus('Generate a website first, then deploy.', true);
    return;
  }

  deployNowBtn.disabled = true;
  setDeployStatus('Publishing on VIRU server...');

  try {
    let response = await fetch('/api/deploy/local', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
      body: JSON.stringify({ result: state.result, page_index: state.pageIndex }),
    });
    let data = await response.json();

    // Fallback to Netlify deploy endpoint if local publish is unavailable.
    if (!response.ok || !data.ok) {
      response = await fetch('/api/deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
        body: JSON.stringify({ result: state.result, page_index: state.pageIndex }),
      });
      data = await response.json();
    }

    if (!response.ok || !data.ok) throw new Error(data.error || 'Deploy failed.');

    deployedUrlEl.value = data.deploy_url || '';
    if (data.deploy_url) {
      await navigator.clipboard.writeText(data.deploy_url).catch(() => {});
      const provider = data.provider === 'viru-local' ? 'VIRU server' : 'Netlify';
      setDeployStatus(`Deploy successful via ${provider}. Live URL ready and copied.`);
    } else {
      setDeployStatus('Deploy completed but live URL was not returned.', true);
    }
  } catch (error) {
    setDeployStatus(error.message || 'Deploy failed.', true);
  } finally {
    deployNowBtn.disabled = false;
  }
}

async function submitSuggestion(event) {
  event.preventDefault();
  const name = document.getElementById('suggestName').value.trim();
  const email = document.getElementById('suggestEmail').value.trim();
  const message = document.getElementById('suggestMessage').value.trim();
  if (!name || !email || !message) { setSuggestStatus('Please fill name, email, and message.', true); return; }
  setSuggestStatus('Sending suggestion...');
  try {
    const response = await fetch(suggestFormEl.action, { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify({ name, email, message, auth_user: state.user?.email || '' }) });
    const data = await response.json();
    const isSuccess = data?.success === true || data?.success === 'true';
    const responseMessage = String(data?.message || '').trim();
    if (!response.ok) throw new Error(responseMessage || 'Failed to send suggestion.');

    if (isSuccess) {
      suggestFormEl.reset();
      setSuggestStatus('Suggestion sent successfully to shrivastavapratham40@gmail.com.');
      return;
    }

    if (responseMessage.toLowerCase().includes('activate')) {
      setSuggestStatus('FormSubmit activation is pending. Open shrivastavapratham40@gmail.com inbox/spam and click the activation link first.', true);
      return;
    }

    throw new Error(responseMessage || 'Failed to send suggestion.');
  } catch (error) {
    setSuggestStatus(error.message || 'Failed to send suggestion.', true);
  }
}

async function initApp() {
  try {
    const cfg = await fetchPublicConfig();
    const firebaseCfg = cfg.firebase || {};
    const missing = ['apiKey', 'authDomain', 'projectId', 'appId'].filter((k) => !firebaseCfg[k]);
    if (missing.length) throw new Error(`Firebase env is incomplete: missing ${missing.join(', ')}`);
    const app = initializeApp(firebaseCfg);
    const auth = getAuth(app);
    onAuthStateChanged(auth, async (user) => {
      if (!user) {
        const next = `${window.location.pathname}${window.location.search}`;
        window.location.href = `/auth?next=${encodeURIComponent(next)}`;
        return;
      }
      const isNewLogin = !state.user;
      state.user = user;
      authStatusEl.textContent = `Authenticated as ${user.email || user.uid}`;
      const suggestEmailEl = document.getElementById('suggestEmail');
      if (suggestEmailEl && !suggestEmailEl.value && user.email) suggestEmailEl.value = user.email;
      renderRecent();
      if (isNewLogin) openIntroOverlay();
      await loadSharedProjectIfPresent();
    });
    logoutBtnEl.addEventListener('click', async () => { try { await signOut(auth); window.location.href = '/auth'; } catch (error) { setStatus(error.message || 'Logout failed.', true); } });
  } catch (error) {
    setStatus(error.message || 'App initialization failed.', true);
  }
}

codeTabEls.forEach((btn) => btn.addEventListener('click', () => { state.activeCode = btn.dataset.code; renderCode(); }));
copyBtn.addEventListener('click', async () => { const page = currentPage(); if (!page) return; try { await navigator.clipboard.writeText(page[state.activeCode] || ''); setStatus(`${state.activeCode.toUpperCase()} copied to clipboard.`); } catch { setStatus('Clipboard copy failed.', true); } });
downloadBtn.addEventListener('click', () => { const page = currentPage(); if (!page) return; const filename = (page.name || 'generated-page').toLowerCase().replace(/[^a-z0-9]+/g, '-'); downloadBlob(`${filename}.html`, new Blob([composePreviewDocument(page)], { type: 'text/html' })); setStatus('Downloaded single-file HTML.'); });
combinedBtn.addEventListener('click', () => { const page = currentPage(); if (!page) return; codeViewEl.textContent = composePreviewDocument(page); setStatus('Combined HTML shown in code view.'); });

exportZipBtn.addEventListener('click', exportZipBundle);
exportReactBtn.addEventListener('click', exportReactStarter);
exportNextBtn.addEventListener('click', exportNextStarter);
createShareBtn.addEventListener('click', createShareLink);
deployNetlifyBtn.addEventListener('click', () => openDeploy('https://app.netlify.com/drop', 'Netlify'));
deployVercelBtn.addEventListener('click', () => openDeploy('https://vercel.com/new', 'Vercel'));
deployGithubBtn.addEventListener('click', () => openDeploy('https://github.com/new', 'GitHub Pages'));
deployNowBtn.addEventListener('click', deployCurrentPage);
generateBtn.addEventListener('click', generateWebsite);
healthBtn.addEventListener('click', runHealthCheck);
settingsToggleEl.addEventListener('click', toggleSettingsDrawer);
suggestFormEl.addEventListener('submit', submitSuggestion);
analyzeUrlBtn.addEventListener('click', analyzeUrl);
pasteUrlBtn?.addEventListener('click', pasteCloneUrl);
enhancePromptBtn.addEventListener('click', () => { promptEl.value = enhancePrompt(promptEl.value); updatePromptHints(); setStatus('Prompt enhanced with audience, tone, and CTA.'); });
skipIntroBtnEl?.addEventListener('click', closeIntroOverlay);

promptEl.addEventListener('input', updatePromptHints);
templateButtons.forEach((btn) => btn.addEventListener('click', () => { promptEl.value = PROMPT_TEMPLATES[btn.dataset.template] || ''; updatePromptHints(); }));
if (templateCategoriesEl) {
  templateCategoriesEl.querySelectorAll('.chip-btn').forEach((btn) => btn.addEventListener('click', () => {
    templateCategoriesEl.querySelectorAll('.chip-btn').forEach((el) => el.classList.remove('active'));
    btn.classList.add('active');
    renderTemplateLibrary(btn.dataset.category || 'all');
  }));
}
mobileTabs.forEach((btn) => btn.addEventListener('click', () => setMobileView(btn.dataset.view)));

promptEl.value = PROMPT_TEMPLATES.saas;
updatePromptHints();
setMobileView('prompt');
updateQueue('idle');
renderTemplateLibrary('all');
renderRecent();
initApp();
