/**
 * groups.js — List groups, create group, join via invite code.
 */
import { requireAuth } from '../core/auth.js';
import { getGroups, createGroup, joinGroup, getGroupBalances } from '../core/api.js';
import { renderSidebar } from '../components/sidebar.js';
import { renderBottomNav } from '../components/bottom-nav.js';
import { showToast } from '../components/toast.js';
import { openModal, closeModal, attachModalClose } from '../components/modal.js';
import { showSkeleton, hideSkeleton } from '../components/loader.js';
import { formatCurrency, getInitials, handleApiError, truncate } from '../core/utils.js';

const user = await requireAuth();
if (!user) throw new Error('Not authenticated');

renderSidebar(user);
renderBottomNav();
document.getElementById('topbar-avatar').textContent   = getInitials(user.username);
document.getElementById('topbar-username').textContent = user.username;

attachModalClose('modal-create-group');
attachModalClose('modal-join-group');

// ── Render groups grid ────────────────────────────────────────────────────────
function renderGroupCard(g) {
  return `
    <div class="card" style="display:flex;flex-direction:column;gap:var(--space-3)">
      <div style="display:flex;align-items:center;gap:var(--space-2)">
        <span style="font-size:22px">${g.emoji || '👥'}</span>
        <div class="fw-700 uppercase" style="font-size:var(--text-base)">${truncate(g.name, 24)}</div>
      </div>
      <div style="display:flex;gap:var(--space-2);flex-wrap:wrap">
        <span class="badge">${g.member_count || g.memberships?.length || 0} Members</span>
        <span class="badge badge-grey">${g.currency || 'INR'}</span>
      </div>
      <div id="balance-${g.id}" class="text-muted text-xs fw-600">Loading balance…</div>
      <a href="/group-detail.html?id=${g.id}" class="btn btn-outline btn-sm btn-full">View Group →</a>
    </div>`;
}

async function loadGroups() {
  const grid = document.getElementById('groups-grid');
  showSkeleton('groups-grid', 4);

  try {
    const data = await getGroups();
    const groups = data.results || data;
    hideSkeleton('groups-grid');

    if (!groups.length) {
      grid.innerHTML = `
        <div class="empty-state" style="grid-column:1/-1">
          No groups yet. Create one or join with a code.
        </div>`;
      return;
    }

    grid.innerHTML = groups.map(renderGroupCard).join('');

    // Load balances in background
    groups.forEach(async (g) => {
      try {
        const balances = await getGroupBalances(g.id);
        const myEntry  = (balances || []).find(b => b.user_id === user.id || b.user === user.id);
        const el = document.getElementById(`balance-${g.id}`);
        if (!el) return;
        if (myEntry) {
          const net = parseFloat(myEntry.net_balance ?? myEntry.net ?? 0);
          if (net > 0)       el.innerHTML = `<span class="text-blue fw-700">You are owed ${formatCurrency(net, g.currency)}</span>`;
          else if (net < 0)  el.innerHTML = `<span class="text-red fw-700">You owe ${formatCurrency(Math.abs(net), g.currency)}</span>`;
          else               el.innerHTML = `<span class="badge badge-grey">Settled up</span>`;
        } else {
          el.textContent = 'No balance data';
        }
      } catch { /* silent */ }
    });

  } catch (err) {
    hideSkeleton('groups-grid');
    grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1">Could not load groups.</div>`;
    handleApiError(err, showToast);
  }
}

loadGroups();

// ── Emoji picker ──────────────────────────────────────────────────────────────
document.querySelectorAll('.emoji-opt').forEach(el => {
  el.addEventListener('click', () => {
    document.querySelectorAll('.emoji-opt').forEach(e => e.classList.remove('selected'));
    el.classList.add('selected');
    document.getElementById('cg-emoji').value = el.dataset.emoji;
  });
});

// ── Create Group ──────────────────────────────────────────────────────────────
document.getElementById('btn-create-group').addEventListener('click', () => {
  document.getElementById('cg-name').value  = '';
  document.getElementById('cg-emoji').value = '';
  document.getElementById('cg-description').value = '';
  document.getElementById('cg-name-error').textContent  = '';
  document.getElementById('cg-global-error').textContent = '';
  document.querySelectorAll('.emoji-opt').forEach(e => e.classList.remove('selected'));
  openModal('modal-create-group');
});
document.getElementById('cg-cancel').addEventListener('click', () => closeModal('modal-create-group'));

document.getElementById('cg-submit').addEventListener('click', async () => {
  const name     = document.getElementById('cg-name').value.trim();
  const currency = document.getElementById('cg-currency').value;
  const emoji    = document.getElementById('cg-emoji').value;
  const desc     = document.getElementById('cg-description').value.trim();
  const errEl    = document.getElementById('cg-name-error');
  const globalEl = document.getElementById('cg-global-error');

  errEl.textContent    = '';
  globalEl.textContent = '';

  if (!name) { errEl.textContent = 'Group name is required.'; return; }

  const btn = document.getElementById('cg-submit');
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';

  try {
    const group = await createGroup({ name, currency, emoji, description: desc });
    closeModal('modal-create-group');
    showToast(`Group "${group.name}" created!`, 'success');
    loadGroups();
  } catch (err) {
    globalEl.textContent = err.message || 'Could not create group.';
    handleApiError(err, showToast);
  } finally {
    btn.disabled = false; btn.textContent = 'Create';
  }
});

// ── Join Group ────────────────────────────────────────────────────────────────
document.getElementById('btn-join-group').addEventListener('click', () => {
  document.getElementById('jg-code').value       = '';
  document.getElementById('jg-code-error').textContent = '';
  openModal('modal-join-group');
});
document.getElementById('jg-cancel').addEventListener('click', () => closeModal('modal-join-group'));

// Auto-uppercase invite code
document.getElementById('jg-code').addEventListener('input', e => {
  e.target.value = e.target.value.toUpperCase();
});

document.getElementById('jg-submit').addEventListener('click', async () => {
  const code  = document.getElementById('jg-code').value.trim().toUpperCase();
  const errEl = document.getElementById('jg-code-error');
  errEl.textContent = '';

  if (!code) { errEl.textContent = 'Invite code is required.'; return; }

  const btn = document.getElementById('jg-submit');
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';

  try {
    const res = await joinGroup(code);
    closeModal('modal-join-group');
    showToast(`Joined "${res.group?.name || 'group'}"!`, 'success');
    loadGroups();
  } catch (err) {
    if (err.status === 404) errEl.textContent = 'Invalid invite code.';
    else errEl.textContent = err.message || 'Could not join group.';
  } finally {
    btn.disabled = false; btn.textContent = 'Join';
  }
});
