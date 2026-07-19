/**
 * profile.js — View/edit profile, change password, reliability score, logout all.
 */
import { requireAuth, logout } from '../core/auth.js';
import { updateMe, changePassword, logoutAll } from '../core/api.js';
import { renderSidebar } from '../components/sidebar.js';
import { renderBottomNav } from '../components/bottom-nav.js';
import { showToast } from '../components/toast.js';
import { formatDate, getInitials, handleApiError, clearFieldErrors } from '../core/utils.js';

const user = await requireAuth();
if (!user) throw new Error('Not authenticated');

renderSidebar(user);
renderBottomNav();
document.getElementById('topbar-avatar').textContent = getInitials(user.username);
document.getElementById('topbar-username').textContent = user.username;

// ── Populate Profile ──────────────────────────────────────────────────────────
function renderProfile(u) {
  document.getElementById('profile-avatar').textContent = getInitials(u.username);
  document.getElementById('profile-username').textContent = u.username;
  document.getElementById('profile-email').textContent = u.email;
  document.getElementById('profile-since').textContent = formatDate(u.date_joined);

  const score = parseFloat(u.reliability_score || 0);
  document.getElementById('profile-score').textContent = score.toFixed(1);
  document.getElementById('profile-currency-badge').textContent = `Default: ${u.currency_preference || 'INR'}`;

  // Form values
  document.getElementById('pf-username').value = u.username;
  document.getElementById('pf-email').value = u.email;
  document.getElementById('pf-currency').value = u.currency_preference || 'INR';
}
renderProfile(user);

// ── Edit Profile ──────────────────────────────────────────────────────────────
document.getElementById('profile-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearFieldErrors(['pf-username-error', 'pf-global-error']);

  const username = document.getElementById('pf-username').value.trim();
  const currency = document.getElementById('pf-currency').value;
  if (!username) { document.getElementById('pf-username-error').textContent = 'Required.'; return; }

  const btn = document.getElementById('pf-submit');
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
  try {
    const updated = await updateMe({ username, currency_preference: currency });
    renderProfile(updated);
    // Update sidebar/topbar
    document.getElementById('topbar-avatar').textContent = getInitials(updated.username);
    document.getElementById('topbar-username').textContent = updated.username;
    renderSidebar(updated);
    showToast('Profile updated!', 'success');
  } catch (err) {
    if (err.status === 400 && err.field_errors?.username) {
      document.getElementById('pf-username-error').textContent = err.field_errors.username;
    } else {
      document.getElementById('pf-global-error').textContent = err.message || 'Update failed.';
    }
  } finally { btn.disabled = false; btn.textContent = 'Save Changes'; }
});

// ── Change Password ───────────────────────────────────────────────────────────
document.getElementById('password-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearFieldErrors(['pw-current-error', 'pw-new-error', 'pw-confirm-error', 'pw-global-error']);

  const old_password = document.getElementById('pw-current').value;
  const new_password = document.getElementById('pw-new').value;
  const confirm = document.getElementById('pw-confirm').value;

  let valid = true;
  if (!old_password) { document.getElementById('pw-current-error').textContent = 'Required.'; valid = false; }
  if (!new_password) { document.getElementById('pw-new-error').textContent = 'Required.'; valid = false; }
  if (new_password !== confirm) { document.getElementById('pw-confirm-error').textContent = 'Passwords do not match.'; valid = false; }
  if (!valid) return;

  const btn = document.getElementById('pw-submit');
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
  try {
    await changePassword({ old_password, new_password });
    showToast('Password changed successfully.', 'success');
    document.getElementById('password-form').reset();
  } catch (err) {
    if (err.status === 400 && err.field_errors) {
      if (err.field_errors.old_password) document.getElementById('pw-current-error').textContent = err.field_errors.old_password;
      if (err.field_errors.new_password) document.getElementById('pw-new-error').textContent = err.field_errors.new_password;
    } else {
      document.getElementById('pw-global-error').textContent = err.message || 'Could not change password.';
    }
  } finally { btn.disabled = false; btn.textContent = 'Change Password'; }
});

// ── Logout All ────────────────────────────────────────────────────────────────
document.getElementById('btn-logout')?.addEventListener('click', async () => {
  if (!confirm('Are you sure you want to log out of all devices?')) return;
  try {
    await logoutAll();
  } catch { /* proceed with local logout anyway */ }
  logout();
});
