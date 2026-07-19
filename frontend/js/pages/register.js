/**
 * register.js — Create account, auto-login, redirect to dashboard.
 */
import { setTokens, getAccessToken } from '../core/auth.js';
import { register, login } from '../core/api.js';
import { validateEmail, clearFieldErrors } from '../core/utils.js';
import { showToast } from '../components/toast.js';

// Already logged in → skip
if (getAccessToken()) window.location.href = '/dashboard.html';

const form       = document.getElementById('register-form');
const submitBtn  = document.getElementById('reg-submit');
const globalErr  = document.getElementById('reg-global-error');

// Password toggles
[['reg-password', 'reg-pw-toggle'], ['reg-confirm', 'reg-confirm-toggle']].forEach(([inputId, btnId]) => {
  const input = document.getElementById(inputId);
  const btn   = document.getElementById(btnId);
  btn?.addEventListener('click', () => {
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    btn.textContent = show ? '🙈' : '👁';
  });
});

// Clear errors on re-type
['reg-username', 'reg-email', 'reg-password', 'reg-confirm'].forEach(id => {
  document.getElementById(id)?.addEventListener('input', () => {
    document.getElementById(`${id}-error`).textContent = '';
    document.getElementById(id).classList.remove('error');
    globalErr.textContent = '';
  });
});

form?.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearFieldErrors(['reg-username-error', 'reg-email-error', 'reg-password-error', 'reg-confirm-error']);
  globalErr.textContent = '';

  const username  = document.getElementById('reg-username').value.trim();
  const email     = document.getElementById('reg-email').value.trim();
  const password  = document.getElementById('reg-password').value;
  const confirm   = document.getElementById('reg-confirm').value;

  // Client-side validation
  let valid = true;
  const setErr = (id, msg) => {
    document.getElementById(`${id}-error`).textContent = msg;
    document.getElementById(id).classList.add('error');
    valid = false;
  };

  if (!username)                    setErr('reg-username', 'Username is required.');
  if (!email || !validateEmail(email)) setErr('reg-email', 'Enter a valid email address.');
  if (!password)                    setErr('reg-password', 'Password is required.');
  if (password !== confirm)         setErr('reg-confirm', 'Passwords do not match.');
  if (!valid) return;

  submitBtn.disabled = true;
  submitBtn.innerHTML = '<span class="spinner"></span> Creating Account…';

  try {
    await register({ username, email, password });

    // Auto-login after registration
    const loginData = await login(email, password);
    setTokens(loginData.access);
    window.location.href = '/dashboard.html';
  } catch (err) {
    if (err.status === 400 && err.field_errors) {
      const fieldMap = {
        username: 'reg-username',
        email:    'reg-email',
        password: 'reg-password',
      };
      for (const [field, val] of Object.entries(err.field_errors)) {
        const elId = fieldMap[field];
        if (elId) {
          document.getElementById(`${elId}-error`).textContent = val;
          document.getElementById(elId)?.classList.add('error');
        }
      }
      globalErr.textContent = err.message || 'Please fix the errors above.';
    } else if (err.status >= 500) {
      showToast('Server error. Try again.', 'error');
    } else {
      globalErr.textContent = err.message || 'Registration failed.';
    }
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = 'CREATE ACCOUNT';
  }
});
