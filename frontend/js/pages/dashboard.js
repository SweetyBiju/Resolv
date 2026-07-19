/**
 * dashboard.js — Overview: trust score, balances, pending actions, activity, groups.
 */
import { requireAuth, logout } from '../core/auth.js';
import { getMe, getGroups, getGroupBalances, getSettlements, getActivity, confirmSettlement } from '../core/api.js';
import { renderSidebar } from '../components/sidebar.js';
import { renderBottomNav } from '../components/bottom-nav.js';
import { showToast } from '../components/toast.js';
import { formatCurrency, formatRelativeDate, getInitials, handleApiError, truncate, capitalize, formatActivityDetail } from '../core/utils.js?v=2';

const user = await requireAuth();
if (!user) throw new Error('Not authenticated');

// Render shell
renderSidebar(user);
renderBottomNav();
document.getElementById('topbar-avatar').textContent   = getInitials(user.username);
document.getElementById('topbar-username').textContent = user.username;

// ── Trust Score ──────────────────────────────────────────────────────────────
function renderTrustScore(u) {
  const score = parseFloat(u.reliability_score || 0);
  document.getElementById('trust-score-num').textContent  = score.toFixed(1);
  document.getElementById('trust-tagline').textContent    = `Hey, ${u.username}!`;

  const pill = document.getElementById('trust-pill');
  if (score >= 4.5) {
    pill.innerHTML = '<span class="trust-pill trust-pill-green">✓ Great job! Zero outstanding debts.</span>';
  } else {
    pill.innerHTML = '<span class="trust-pill trust-pill-red">⚠ You have outstanding debts.</span>';
  }
}
renderTrustScore(user);

// ── Balance Breakdown ────────────────────────────────────────────────────────
async function loadBalances(groups) {
  let totalOwed = 0, totalOwes = 0;
  const currency = user.currency_preference || 'INR';

  await Promise.all(groups.map(async (g) => {
    try {
      const balances = await getGroupBalances(g.id);
      const myEntry = balances.find?.(b => b.user_id === user.id || b.user === user.id);
      if (myEntry) {
        const net = parseFloat(myEntry.net_balance || myEntry.net || 0);
        if (net > 0) totalOwed += net;
        else         totalOwes += Math.abs(net);
      }
    } catch { /* ignore per-group errors */ }
  }));

  const net = totalOwed - totalOwes;
  document.getElementById('dash-owed').textContent = formatCurrency(totalOwed, currency);
  document.getElementById('dash-owes').textContent = formatCurrency(totalOwes, currency);
  const netEl = document.getElementById('dash-net');
  netEl.textContent  = formatCurrency(Math.abs(net), currency);
  netEl.className    = `balance-amount ${net >= 0 ? 'text-blue' : 'text-red'}`;

  const actionEl = document.getElementById('dash-balance-action');
  if (net === 0) {
    actionEl.innerHTML = '<span class="badge badge-grey">No Active Debts</span>';
  } else {
    actionEl.innerHTML = `<a href="/settlements.html" class="btn btn-primary btn-sm">View Debts</a>`;
  }
}

// ── Immediate Actions (pending settlements where I am receiver) ───────────────
async function loadActions() {
  const el = document.getElementById('dash-actions-list');
  try {
    const data = await getSettlements();
    const results = data.results || data;
    const pending = results.filter(s => s.status === 'PENDING' && s.receiver === user.id);

    if (!pending.length) {
      el.innerHTML = `<div class="empty-state" style="padding:var(--space-6)">✓ You're all caught up!</div>`;
      return;
    }

    el.innerHTML = pending.map(s => `
      <div class="action-row">
        <div>
          <div class="fw-700 text-sm">${s.payer_username}</div>
          <div class="text-muted text-xs">${formatCurrency(s.amount, s.currency)}</div>
        </div>
        <button class="btn btn-primary btn-sm" data-id="${s.id}" data-action="confirm">Confirm</button>
      </div>`).join('');

    el.querySelectorAll('[data-action="confirm"]').forEach(btn => {
      btn.addEventListener('click', async () => {
        btn.disabled = true;
        try {
          await confirmSettlement(btn.dataset.id);
          showToast('Settlement confirmed!', 'success');
          btn.closest('.action-row').remove();
        } catch (err) {
          handleApiError(err, showToast);
          btn.disabled = false;
        }
      });
    });
  } catch (err) {
    el.innerHTML = `<div class="empty-state" style="padding:var(--space-4)">Could not load actions.</div>`;
  }
}

// ── Recent Activity ──────────────────────────────────────────────────────────
const ACTION_ICONS = {
  EXPENSE_CREATED: '💰', EXPENSE_UPDATED: '✏️', EXPENSE_DELETED: '🗑️',
  SETTLEMENT_CREATED: '💸', SETTLEMENT_CONFIRMED: '✅', SETTLEMENT_CANCELLED: '❌',
  GROUP_CREATED: '👥', MEMBER_ADDED: '➕', MEMBER_REMOVED: '➖',
};

async function loadActivity() {
  const el = document.getElementById('dash-activity-list');
  try {
    const data = await getActivity({ page_size: 5 });
    const results = data.results || data;
    if (!results.length) {
      el.innerHTML = `<div class="empty-state" style="padding:var(--space-4)">No recent activity.</div>`;
      return;
    }
    el.innerHTML = results.slice(0, 5).map(entry => `
      <div class="activity-row">
        <div class="activity-icon">${ACTION_ICONS[entry.action] || '📌'}</div>
        <div style="flex:1">
          <div class="fw-700 text-sm uppercase">${(entry.action || '').replace(/_/g, ' ')}</div>
          <div class="text-muted text-xs">${truncate(formatActivityDetail(entry), 80)}</div>
        </div>
        <div class="text-muted text-xs">${formatRelativeDate(entry.timestamp)}</div>
      </div>`).join('');
  } catch {
    el.innerHTML = `<div class="empty-state" style="padding:var(--space-4)">Could not load activity.</div>`;
  }
}

// ── Groups Quick View ────────────────────────────────────────────────────────
async function loadGroups() {
  const el = document.getElementById('dash-groups-grid');
  try {
    const data = await getGroups();
    const groups = data.results || data;

    if (!groups.length) {
      el.innerHTML = `<div class="empty-state">No groups yet. <a href="/groups.html" class="text-blue">Create one →</a></div>`;
      return;
    }

    // Start balance load in parallel
    loadBalances(groups);

    el.innerHTML = groups.slice(0, 4).map(g => `
      <div class="card card-sm" style="cursor:pointer" onclick="location.href='/group-detail.html?id=${g.id}'">
        <div class="fw-700 text-sm uppercase" style="margin-bottom:var(--space-2)">
          ${g.emoji || ''} ${truncate(g.name, 20)}
        </div>
        <div class="text-muted text-xs">${g.member_count || 0} Members · <span class="badge badge-grey">${g.currency || 'INR'}</span></div>
        <div style="margin-top:var(--space-3)">
          <a href="/group-detail.html?id=${g.id}" class="btn btn-outline btn-sm btn-full">View Group</a>
        </div>
      </div>`).join('');
  } catch (err) {
    el.innerHTML = `<div class="empty-state">Could not load groups.</div>`;
  }
}

// ── Init ─────────────────────────────────────────────────────────────────────
loadActions();
loadActivity();
loadGroups();
