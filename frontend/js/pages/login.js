/**
 * login.js — Authenticate user, store token, redirect to dashboard.
 */
import { setTokens, getAccessToken } from '../core/auth.js';
import { login } from '../core/api.js';
import { validateEmail, clearFieldErrors, mapFieldErrors } from '../core/utils.js';
import { showToast } from '../components/toast.js';

// If already authenticated, skip straight to dashboard
if (getAccessToken()) window.location.href = '/dashboard.html';

const form      = document.getElementById('login-form');
const emailEl   = document.getElementById('login-email');
const passEl    = document.getElementById('login-password');
const submitBtn = document.getElementById('login-submit');
const globalErr = document.getElementById('login-global-error');
const pwToggle  = document.getElementById('login-pw-toggle');

// Show/hide password
pwToggle?.addEventListener('click', () => {
  const isPassword = passEl.type === 'password';
  passEl.type   = isPassword ? 'text' : 'password';
  pwToggle.textContent = isPassword ? '🙈' : '👁';
});

// Clear errors on re-type
emailEl?.addEventListener('input', () => {
  document.getElementById('login-email-error').textContent = '';
  emailEl.classList.remove('error');
  globalErr.textContent = '';
});
passEl?.addEventListener('input', () => {
  document.getElementById('login-password-error').textContent = '';
  passEl.classList.remove('error');
  globalErr.textContent = '';
});

form?.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearFieldErrors(['login-email-error', 'login-password-error']);
  globalErr.textContent = '';

  const email    = emailEl.value.trim();
  const password = passEl.value;

  // Client-side validation
  let valid = true;
  if (!email || !validateEmail(email)) {
    document.getElementById('login-email-error').textContent = 'Please enter a valid email address.';
    emailEl.classList.add('error');
    valid = false;
  }
  if (!password) {
    document.getElementById('login-password-error').textContent = 'Password is required.';
    passEl.classList.add('error');
    valid = false;
  }
  if (!valid) return;

  // Disable button and show spinner
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<span class="spinner"></span> Logging in…';

  try {
    const data = await login(email, password);
    setTokens(data.access);
    window.location.href = '/dashboard.html';
  } catch (err) {
    if (err.status === 401) {
      globalErr.textContent = 'Invalid email or password.';
      emailEl.classList.add('error');
      passEl.classList.add('error');
    } else if (err.status === 429) {
      showToast('Too many attempts. Wait a minute.', 'error');
    } else if (err.status >= 500) {
      showToast('Server error. Try again later.', 'error');
    } else {
      globalErr.textContent = err.message || 'Login failed. Please try again.';
    }
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = 'LOG IN';
  }
});
