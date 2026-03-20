import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.13.2/firebase-app.js';
import { getAuth, onAuthStateChanged } from 'https://www.gstatic.com/firebasejs/10.13.2/firebase-auth.js';

const ACCEPTED_EXTENSIONS = ['pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg'];
const CONVERSION_MAP = {
  pdf: ['docx', 'txt', 'png'],
  docx: ['pdf', 'txt'],
  txt: ['docx', 'pdf'],
  png: ['pdf', 'txt'],
  jpg: ['pdf', 'txt'],
  jpeg: ['pdf', 'txt'],
};

const state = {
  user: null,
  uploads: [],
  activeUpload: null,
  jobs: [],
  lastJob: null,
  isAdmin: false,
};

const fileInputEl = document.getElementById('fileInput');
const dropZoneEl = document.getElementById('dropZone');
const uploadStatusEl = document.getElementById('uploadStatus');
const fileListEl = document.getElementById('fileList');
const sourceFormatEl = document.getElementById('sourceFormat');
const targetFormatEl = document.getElementById('targetFormat');
const aiModeEl = document.getElementById('aiMode');
const jobPriorityEl = document.getElementById('jobPriority');
const ocrEnabledEl = document.getElementById('ocrEnabled');
const structureFixEl = document.getElementById('structureFix');
const keepLayoutEl = document.getElementById('keepLayout');
const prepareBtnEl = document.getElementById('prepareBtn');
const downloadSummaryBtnEl = document.getElementById('downloadSummaryBtn');
const jobStatusEl = document.getElementById('jobStatus');
const previewMetaEl = document.getElementById('previewMeta');
const previewPaneEl = document.getElementById('previewPane');
const jobHistoryEl = document.getElementById('jobHistory');
const converterAuthStatusEl = document.getElementById('converterAuthStatus');
const converterAdminPanelEl = document.getElementById('converterAdminPanel');
const converterAdminMetricsEl = document.getElementById('converterAdminMetrics');

function extensionOf(name = '') {
  return name.includes('.') ? name.split('.').pop().toLowerCase() : '';
}

function formatBytes(bytes) {
  if (!bytes) return '0 KB';
  const units = ['B', 'KB', 'MB', 'GB'];
  let value = bytes;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function setUploadStatus(message, isError = false) {
  uploadStatusEl.textContent = message;
  uploadStatusEl.style.color = isError ? '#ffb4b4' : 'var(--muted)';
}

function setJobStatus(message, isError = false) {
  jobStatusEl.textContent = message;
  jobStatusEl.style.color = isError ? '#ffb4b4' : 'var(--muted)';
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

function populateTargets(ext) {
  targetFormatEl.innerHTML = '<option value="">Select output format</option>';
  (CONVERSION_MAP[ext] || []).forEach((format) => {
    const option = document.createElement('option');
    option.value = format;
    option.textContent = format.toUpperCase();
    targetFormatEl.appendChild(option);
  });
}

async function authorizedAssetUrl(url) {
  const headers = await authHeaders();
  if (!Object.keys(headers).length) return url;
  const token = headers.Authorization.replace('Bearer ', '');
  return `${url}${url.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}`;
}

async function showPreview(preview) {
  if (!preview) {
    previewPaneEl.innerHTML = '<p class="converter-empty">No preview available.</p>';
    return;
  }

  if (preview.kind === 'image') {
    const note = preview.note ? `<p class="converter-empty">${preview.note}</p>` : '';
    const src = await authorizedAssetUrl(preview.url);
    previewPaneEl.innerHTML = `${note}<img src="${src}" alt="Preview asset" class="converter-image-preview" />`;
    return;
  }

  if (preview.kind === 'pdf') {
    const image = preview.imageUrl ? `<img src="${await authorizedAssetUrl(preview.imageUrl)}" alt="PDF preview" class="converter-image-preview" />` : '';
    const text = preview.text ? `<pre class="converter-text-preview">${preview.text}</pre>` : '<p class="converter-empty">PDF text preview unavailable.</p>';
    previewPaneEl.innerHTML = `${image}${text}`;
    return;
  }

  if (preview.kind === 'text') {
    previewPaneEl.innerHTML = `<pre class="converter-text-preview">${preview.text || 'No text available.'}</pre>`;
    return;
  }

  previewPaneEl.innerHTML = '<p class="converter-empty">Preview format is not supported.</p>';
}

function updatePreviewMeta(upload) {
  const ext = upload ? upload.sourceFormat.toUpperCase() : 'None';
  previewMetaEl.innerHTML = `
    <div><span>Name</span><strong>${upload?.fileName || 'None'}</strong></div>
    <div><span>Type</span><strong>${ext}</strong></div>
    <div><span>Size</span><strong>${upload ? formatBytes(upload.sizeBytes) : '0 KB'}</strong></div>
  `;
}

function renderUploads() {
  fileListEl.innerHTML = '';
  state.uploads.forEach((upload) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `converter-file-chip${state.activeUpload?.id === upload.id ? ' active' : ''}`;
    button.textContent = `${upload.fileName} - ${upload.sourceFormat.toUpperCase()} - ${formatBytes(upload.sizeBytes)}`;
    button.addEventListener('click', () => selectUpload(upload));
    fileListEl.appendChild(button);
  });
}

function currentPayload() {
  if (!state.activeUpload) return null;
  return {
    upload_id: state.activeUpload.id,
    target_format: targetFormatEl.value,
    ai_mode: aiModeEl.value,
    priority: jobPriorityEl.value,
    ocr_enabled: ocrEnabledEl.checked,
    structure_fix: structureFixEl.checked,
    keep_layout: keepLayoutEl.checked,
  };
}

async function selectUpload(upload) {
  state.activeUpload = upload;
  renderUploads();
  sourceFormatEl.value = upload.sourceFormat.toUpperCase();
  populateTargets(upload.sourceFormat);
  targetFormatEl.value = (CONVERSION_MAP[upload.sourceFormat] || [])[0] || '';
  updatePreviewMeta(upload);
  await showPreview(upload.preview);
  setJobStatus('Upload ready. Choose output format and run conversion.');
}

function downloadBlob(name, blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}

async function uploadFiles(files) {
  const list = Array.from(files || []).filter((file) => ACCEPTED_EXTENSIONS.includes(extensionOf(file.name)));
  if (!list.length) {
    setUploadStatus('No supported files selected.', true);
    return;
  }
  const formData = new FormData();
  list.forEach((file) => formData.append('files', file));
  setUploadStatus('Uploading files...');
  try {
    const response = await fetch('/api/converter/upload', {
      method: 'POST',
      headers: await authHeaders(),
      body: formData,
    });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || `Upload failed with status ${response.status}`);
    state.uploads = data.uploads || [];
    renderUploads();
    if (state.uploads.length > 0) await selectUpload(state.uploads[0]);
    setUploadStatus(`${state.uploads.length} file(s) processed. Choose format below.`);
  } catch (error) {
    console.error('[Upload Error]', error);
    setUploadStatus(`Error: ${error.message}`, true);
  }
}

async function loadJobs() {
  try {
    const response = await fetch('/api/converter/jobs', { headers: await authHeaders() });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || 'Failed to load jobs.');
    state.jobs = data.jobs || [];
    renderJobs();
  } catch (error) {
    jobHistoryEl.innerHTML = `<p class="converter-empty">${error.message || 'Failed to load jobs.'}</p>`;
  }
}

function renderJobs() {
  jobHistoryEl.innerHTML = '';
  if (!state.jobs.length) {
    jobHistoryEl.innerHTML = '<p class="converter-empty">No completed conversion jobs yet.</p>';
    return;
  }
  state.jobs.forEach((job) => {
    const card = document.createElement('article');
    card.className = 'converter-history-card';
    card.innerHTML = `
      <div class="converter-history-head">
        <strong>${job.fileName}</strong>
        <span>${job.status}</span>
      </div>
      <p>${job.sourceFormat.toUpperCase()} -> ${job.targetFormat.toUpperCase()} - ${job.aiMode} AI - ${job.priority}</p>
      <small>${new Date(job.createdAt).toLocaleString()}</small>
    `;
    const actions = document.createElement('div');
    actions.className = 'inline-actions';

    const previewBtn = document.createElement('button');
    previewBtn.type = 'button';
    previewBtn.className = 'ghost-btn';
    previewBtn.textContent = 'Preview';
    previewBtn.addEventListener('click', async () => {
      const response = await fetch(`/api/converter/preview/${encodeURIComponent(job.id)}`, { headers: await authHeaders() });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        setJobStatus(data.error || 'Preview failed.', true);
        return;
      }
      state.lastJob = job;
      await showPreview(data.preview);
      setJobStatus(`Loaded preview for ${job.fileName}.`);
    });

    const downloadBtn = document.createElement('button');
    downloadBtn.type = 'button';
    downloadBtn.className = 'ghost-btn';
    downloadBtn.textContent = 'Download';
    downloadBtn.addEventListener('click', async () => {
      const headers = await authHeaders();
      const token = headers.Authorization.replace('Bearer ', '');
      window.location.href = `/api/converter/download/${encodeURIComponent(job.id)}?token=${encodeURIComponent(token)}`;
    });

    actions.appendChild(previewBtn);
    actions.appendChild(downloadBtn);
    card.appendChild(actions);

    if ((job.notes || []).length) {
      const note = document.createElement('p');
      note.textContent = job.notes.join(' ');
      card.appendChild(note);
    }
    jobHistoryEl.appendChild(card);
  });
}

async function convertActiveUpload() {
  const payload = currentPayload();
  if (!payload) {
    setJobStatus('Upload a file first.', true);
    return;
  }
  if (!payload.target_format) {
    setJobStatus('Select a target format.', true);
    return;
  }
  prepareBtnEl.disabled = true;
  setJobStatus('Running document conversion...');
  try {
    const response = await fetch('/api/converter/convert', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || `Conversion failed (${response.status})`);
    state.lastJob = data.job;
    if (data.job?.preview) await showPreview(data.job.preview);
    setJobStatus(`Success! ${data.job.sourceFormat.toUpperCase()} converted to ${data.job.targetFormat.toUpperCase()}.`);
    await loadJobs();
    if (state.isAdmin) await loadAdminMetrics();
  } catch (error) {
    console.error('[Conversion Error]', error);
    setJobStatus(`Failed: ${error.message}`, true);
  } finally {
    prepareBtnEl.disabled = false;
  }
}

function downloadRequestJson() {
  const payload = currentPayload();
  if (!payload) {
    setJobStatus('Nothing selected to export.', true);
    return;
  }
  const name = `${state.activeUpload.fileName.replace(/[^a-zA-Z0-9._-]+/g, '-')}.request.json`;
  downloadBlob(name, new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }));
  setJobStatus('Conversion request JSON downloaded.');
}

async function loadAdminMetrics() {
  try {
    const response = await fetch('/api/converter/admin/metrics', { headers: await authHeaders() });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || 'Admin metrics unavailable.');
    state.isAdmin = true;
    converterAdminPanelEl.classList.remove('hidden');
    converterAdminMetricsEl.textContent = JSON.stringify(data.metrics, null, 2);
  } catch {
    state.isAdmin = false;
    converterAdminPanelEl.classList.add('hidden');
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
        const next = `${window.location.pathname}${window.location.search}`;
        window.location.href = `/auth?next=${encodeURIComponent(next)}`;
        return;
      }
      state.user = user;
      converterAuthStatusEl.textContent = user.email || user.uid;
      await loadJobs();
      await loadAdminMetrics();
    });
  } catch (error) {
    setJobStatus(error.message || 'Converter initialization failed.', true);
  }
}

fileInputEl.addEventListener('change', async (event) => {
  await uploadFiles(event.target.files);
});

dropZoneEl.addEventListener('dragover', (event) => {
  event.preventDefault();
  dropZoneEl.classList.add('is-dragover');
});

dropZoneEl.addEventListener('dragleave', () => {
  dropZoneEl.classList.remove('is-dragover');
});

dropZoneEl.addEventListener('drop', async (event) => {
  event.preventDefault();
  dropZoneEl.classList.remove('is-dragover');
  await uploadFiles(event.dataTransfer?.files);
});

prepareBtnEl.addEventListener('click', convertActiveUpload);
downloadSummaryBtnEl.addEventListener('click', downloadRequestJson);

init();
