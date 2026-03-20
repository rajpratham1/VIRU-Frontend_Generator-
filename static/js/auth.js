import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.13.2/firebase-app.js';
import {
  createUserWithEmailAndPassword,
  getAuth,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  updateProfile,
} from 'https://www.gstatic.com/firebasejs/10.13.2/firebase-auth.js';

const tabLoginEl = document.getElementById('tabLogin');
const tabRegisterEl = document.getElementById('tabRegister');
const loginFormEl = document.getElementById('loginForm');
const registerFormEl = document.getElementById('registerForm');
const authStatusEl = document.getElementById('authStatus');

function setStatus(message, isError = false) {
  authStatusEl.textContent = message;
  authStatusEl.style.color = isError ? '#ffb4b4' : 'var(--muted)';
}

function switchAuthTab(mode) {
  const isLogin = mode === 'login';
  tabLoginEl.classList.toggle('active', isLogin);
  tabRegisterEl.classList.toggle('active', !isLogin);
  tabLoginEl.setAttribute('aria-selected', String(isLogin));
  tabRegisterEl.setAttribute('aria-selected', String(!isLogin));
  loginFormEl.classList.toggle('hidden', !isLogin);
  registerFormEl.classList.toggle('hidden', isLogin);
}

function nextPath() {
  const params = new URLSearchParams(window.location.search);
  const next = (params.get('next') || '').trim();
  return next.startsWith('/') ? next : '/app';
}

async function fetchPublicConfig() {
  const response = await fetch('/api/public-config');
  const data = await response.json();
  if (!response.ok) throw new Error('Unable to load public configuration.');
  return data;
}

async function initAuthPage() {
  try {
    const cfg = await fetchPublicConfig();
    const firebaseCfg = cfg.firebase || {};
    const required = ['apiKey', 'authDomain', 'projectId', 'appId'];
    const missing = required.filter((key) => !firebaseCfg[key]);

    if (missing.length) {
      throw new Error(`Firebase env is incomplete: missing ${missing.join(', ')}`);
    }

    const app = initializeApp(firebaseCfg);
    const auth = getAuth(app);

    tabLoginEl.addEventListener('click', () => switchAuthTab('login'));
    tabRegisterEl.addEventListener('click', () => switchAuthTab('register'));

    loginFormEl.addEventListener('submit', async (event) => {
      event.preventDefault();
      const email = document.getElementById('loginEmail').value.trim();
      const password = document.getElementById('loginPassword').value;

      try {
        await signInWithEmailAndPassword(auth, email, password);
        setStatus('Login successful. Redirecting...');
      } catch (error) {
        setStatus(error.message || 'Login failed.', true);
      }
    });

    registerFormEl.addEventListener('submit', async (event) => {
      event.preventDefault();
      const name = document.getElementById('registerName').value.trim();
      const email = document.getElementById('registerEmail').value.trim();
      const password = document.getElementById('registerPassword').value;

      try {
        const credential = await createUserWithEmailAndPassword(auth, email, password);
        if (name) {
          await updateProfile(credential.user, { displayName: name });
        }
        setStatus('Registration successful. Redirecting...');
      } catch (error) {
        setStatus(error.message || 'Registration failed.', true);
      }
    });

    onAuthStateChanged(auth, (user) => {
      if (user) {
        window.location.href = nextPath();
      } else {
        setStatus('Please login to continue.');
      }
    });
  } catch (error) {
    setStatus(error.message || 'Authentication initialization failed.', true);
  }
}

switchAuthTab('login');
initAuthPage();
