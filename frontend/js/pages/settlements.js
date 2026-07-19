/**
 * settlements.js — View/create/confirm/cancel settlements. Suggested settlements.
 */
import { requireAuth } from '../core/auth.js';
import { getSettlements, getGroups, createSettlement, confirmSettlement, cancelSettlement, getSuggestedSettlements, getGroupBalances } from '../core/api.js';
import { renderSidebar } from '../components/sidebar.js';
import { renderBottomNav } from '../components/bottom-nav.js';
import { showToast } from '../components/toast.js';
import { openModal, closeModal, attachModalClose } from '../components/modal.js';
import { showSkeleton, hideSkeleton } from '../components/loader.js';
import { formatCurrency, formatDate, getInitials, settlementStatusBadge, handleApiError, debounce } from '../core/utils.js';

const user = await requireAuth();
if (!user) throw new Error('Not authenticated');

renderSidebar(user);
renderBottomNav();
document.getElementById('topbar-avatar').textContent   = getInitials(user.username);
document.getElementById('topbar-username').textContent = user.username;

attachModalClose('modal-settlement');

let _activeStatus = 'ALL';
let _groups = [];
let _lastSettlement = null; // duplicate detection

// ── Load groups ───────────────────────────────────────────────────────────────
async function loadGroups() {
  try {
    const data = await getGroups();
    _groups = data.results || data;
    const grpSel  = document.getElementById('ns-group');
    const sugSel  = document.getElementById('suggested-group-select');
    const opts    = _groups.map(g => `<option value="${g.id}">${g.name}</option>`).join('');
    grpSel.innerHTML = `<option value="">Select Group</option>` + opts;
    sugSel.innerHTML = `<option value="">Select Group</option>` + opts;
  } catch { /* silent */ }
}

// ── Load settlements ──────────────────────────────────────────────────────────
async function loadSettlements() {
  const listEl  = document.getElementById('settlements-list');
  const emptyEl = document.getElementById('settlements-empty');
  showSkeleton('settlements-list', 3, 'card');

  const params = _activeStatus === 'ALL' ? {} : { status: _activeStatus };
  try {
    const data = await getSettlements(params);
    const settlements = data.results || data;
    hideSkeleton('settlements-list');
    emptyEl.classList.toggle('hidden', !!settlements.length);
    listEl.innerHTML = '';

    settlements.forEach(s => {
      const card = document.createElement('div');
      card.className = 'card card-sm';
      card.style.marginBottom = 'var(--space-3)';
      card.innerHTML = `
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:var(--space-3)">
          <div>
            <div style="display:flex;align-items:center;gap:var(--space-2)">
              <span class="fw-700 text-sm">${s.payer_username}</span>
              <span class="text-muted">→</span>
              <span class="fw-700 text-sm">${s.receiver_username}</span>
            </div>
            <div class="text-muted text-xs" style="margin-top:2px">
              ${formatCurrency(s.amount, s.currency)} · ${s.group_name || '—'} · ${formatDate(s.created_at)}
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:var(--space-2)">
            <span class="badge ${settlementStatusBadge(s.status)}">${s.status}</span>
            ${s.status === 'PENDING' && s.receiver === user.id
              ? `<button class="btn btn-green btn-sm" data-id="${s.id}" data-action="confirm">Confirm Payment</button>` : ''}
            ${s.status === 'PENDING' && s.payer === user.id
              ? `<button class="btn btn-ghost btn-sm text-red" data-id="${s.id}" data-action="cancel">Cancel</button>` : ''}
            ${s.status === 'CONFIRMED' ? `<span class="text-muted text-xs">✓ ${formatDate(s.updated_at)}</span>` : ''}
          </div>
        </div>`;
      listEl.appendChild(card);
    });

    listEl.querySelectorAll('[data-action="confirm"]').forEach(btn => {
      btn.addEventListener('click', async () => {
        btn.disabled = true;
        try { await confirmSettlement(btn.dataset.id); showToast('Settlement confirmed!', 'success'); loadSettlements(); }
        catch (err) { handleApiError(err, showToast); btn.disabled = false; }
      });
    });
    listEl.querySelectorAll('[data-action="cancel"]').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('Cancel this settlement?')) return;
        try { await cancelSettlement(btn.dataset.id); showToast('Settlement cancelled.', 'info'); loadSettlements(); }
        catch (err) { handleApiError(err, showToast); }
      });
    });
  } catch (err) {
    hideSkeleton('settlements-list');
    handleApiError(err, showToast);
  }
}

// ── Status filter tabs ────────────────────────────────────────────────────────
['stab-all','stab-pending','stab-confirmed','stab-cancelled'].forEach(id => {
  document.getElementById(id)?.addEventListener('click', (e) => {
    document.querySelectorAll('[id^="stab-"]').forEach(b => b.classList.remove('active'));
    e.target.classList.add('active');
    _activeStatus = e.target.dataset.status;
    loadSettlements();
  });
});

// ── Suggested Settlements ─────────────────────────────────────────────────────
let _suggestedOpen = true;
document.getElementById('suggested-toggle')?.addEventListener('click', () => {
  _suggestedOpen = !_suggestedOpen;
  document.getElementById('suggested-body').style.display = _suggestedOpen ? '' : 'none';
  document.getElementById('suggested-chevron').textContent = _suggestedOpen ? '▼' : '▶';
});

document.getElementById('suggested-group-select')?.addEventListener('change', async (e) => {
  const groupId = e.target.value;
  const listEl  = document.getElementById('suggested-list');
  if (!groupId) { listEl.innerHTML = ''; return; }

  listEl.innerHTML = '<div class="text-muted text-sm">Loading…</div>';
  try {
    const data     = await getSuggestedSettlements(groupId);
    const payments = data.suggested_payments || [];
    if (!payments.length) {
      listEl.innerHTML = '<div class="empty-state" style="padding:var(--space-4)">✓ All settled up in this group!</div>';
      return;
    }
    listEl.innerHTML = payments.map(p => `
      <div class="action-row">
        <div class="text-sm">
          <span class="fw-700">${p.from_user || `User ${p.from_user_id}`}</span>
          <span class="text-muted"> → </span>
          <span class="fw-700">${p.to_user || `User ${p.to_user_id}`}</span>
          <span class="text-muted"> · ${formatCurrency(p.amount, data.currency)}</span>
        </div>
        <button class="btn btn-outline btn-sm" data-from="${p.from_user_id}" data-to="${p.to_user_id}" data-amount="${p.amount}" data-group="${groupId}" data-action="record-sug">Record This</button>
      </div>`).join('');

    listEl.querySelectorAll('[data-action="record-sug"]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.getElementById('ns-group').value  = btn.dataset.group;
        document.getElementById('ns-amount').value = btn.dataset.amount;
        _updateReceiverOptions(btn.dataset.group, btn.dataset.to);
        openModal('modal-settlement');
      });
    });
  } catch (err) { handleApiError(err, showToast); }
});

async function _updateReceiverOptions(groupId, preselectId = null) {
  const g   = _groups.find(x => x.id == groupId);
  const sel = document.getElementById('ns-receiver');
  const members = (g?.memberships || []).map(m => m.user).filter(m => m.id !== user.id);
  sel.innerHTML = members.map(m => `<option value="${m.id}" ${preselectId && m.id == preselectId ? 'selected' : ''}>${m.username}</option>`).join('');
  _updateDebtInfo();
}

// ── Dynamic debt computation ──────────────────────────────────────────────────
let _cachedBalances = {};

async function _updateDebtInfo() {
  const debtInfoEl = document.getElementById('ns-debt-info');
  const warnEl     = document.getElementById('ns-over-settlement-warn');
  const warnText   = document.getElementById('ns-warn-text');
  const checkboxEl = document.getElementById('ns-allow-over');

  // Elements may not exist if called outside modal context — bail early
  if (!debtInfoEl || !warnEl) return;

  // Reset
  debtInfoEl.style.display = 'none';
  warnEl.style.display     = 'none';
  if (checkboxEl) checkboxEl.checked = false;

  const groupId  = document.getElementById('ns-group').value;
  const receiver = parseInt(document.getElementById('ns-receiver').value);
  if (!groupId || !receiver) return;

  try {
    const data     = await getGroupBalances(groupId);
    const balances = data.balances || data;
    _cachedBalances = {};
    balances.forEach(b => { _cachedBalances[b.user_id] = b; });

    const myBalance       = _cachedBalances[user.id];
    const receiverBalance = _cachedBalances[receiver];
    const receiverName    = receiverBalance?.username || `User ${receiver}`;

    if (!myBalance || !receiverBalance) return;

    const myNet       = parseFloat(myBalance.net_balance || 0);
    const receiverNet = parseFloat(receiverBalance.net_balance || 0);

    if (myNet >= 0 || receiverNet <= 0) {
      // User owes nothing to this person
      debtInfoEl.innerHTML = `<span style="color:var(--text-muted)">You don't currently owe <strong>${receiverName}</strong> anything in this group.</span>`;
      debtInfoEl.style.display = 'block';
      debtInfoEl.style.background = 'var(--bg-page)';

      warnText.textContent = `⚠️ Recording this settlement will act as lending money (an advance payment) to ${receiverName}.`;
      warnEl.style.display = 'block';
    } else {
      const actualDebt = Math.min(Math.abs(myNet), receiverNet).toFixed(2);
      debtInfoEl.innerHTML = `You owe <strong>${receiverName}</strong>: <strong>${formatCurrency(actualDebt)}</strong>`;
      debtInfoEl.style.display = 'block';
      debtInfoEl.style.background = 'var(--bg-page)';

      // Check if entered amount exceeds debt
      const amount = parseFloat(document.getElementById('ns-amount').value) || 0;
      if (amount > parseFloat(actualDebt) + 0.05) {
        warnText.textContent = `⚠️ The amount exceeds your debt of ${formatCurrency(actualDebt)}. The extra will be recorded as lending money to ${receiverName}.`;
        warnEl.style.display = 'block';
      }
    }
  } catch { /* silent — debt info is enhancement, not critical */ }
}

document.getElementById('ns-group')?.addEventListener('change', (e) => _updateReceiverOptions(e.target.value));
document.getElementById('ns-receiver')?.addEventListener('change', () => _updateDebtInfo());
document.getElementById('ns-amount')?.addEventListener('input', debounce(() => _updateDebtInfo(), 400));

// ── Create Settlement Modal ───────────────────────────────────────────────────
document.getElementById('btn-record-settlement')?.addEventListener('click', () => {
  document.getElementById('ns-amount').value = '';
  document.getElementById('ns-global-error').textContent = '';
  document.getElementById('ns-debt-info').style.display = 'none';
  document.getElementById('ns-over-settlement-warn').style.display = 'none';
  const cb = document.getElementById('ns-allow-over');
  if (cb) cb.checked = false;
  openModal('modal-settlement');
});
document.getElementById('ns-cancel')?.addEventListener('click', () => closeModal('modal-settlement'));

document.getElementById('ns-submit')?.addEventListener('click', async () => {
  const btn       = document.getElementById('ns-submit');
  const globalErr = document.getElementById('ns-global-error');
  globalErr.textContent = '';

  const groupId  = parseInt(document.getElementById('ns-group').value);
  const receiver = parseInt(document.getElementById('ns-receiver').value);
  const amount   = parseFloat(document.getElementById('ns-amount').value);
  const currency = document.getElementById('ns-currency').value;
  const allowOver = document.getElementById('ns-allow-over')?.checked || false;

  if (!groupId)                   { globalErr.textContent = 'Select a group.'; return; }
  if (!receiver)                  { globalErr.textContent = 'Select a receiver.'; return; }
  if (!amount || amount <= 0)     { globalErr.textContent = 'Enter a valid amount.'; return; }

  // If warning is visible but checkbox not checked, block submission
  const warnEl = document.getElementById('ns-over-settlement-warn');
  if (warnEl && warnEl.style.display !== 'none' && !allowOver) {
    globalErr.textContent = 'Please check the confirmation box to proceed with this settlement.';
    return;
  }

  // Duplicate detection
  const now = Date.now();
  if (_lastSettlement &&
      _lastSettlement.receiver === receiver &&
      _lastSettlement.amount   === amount &&
      now - _lastSettlement.time < 60000) {
    if (!confirm('You just created a similar settlement — are you sure?')) return;
  }

  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
  try {
    await createSettlement({ group: groupId, receiver, amount, currency, allow_over_settlement: allowOver });
    _lastSettlement = { receiver, amount, time: now };
    closeModal('modal-settlement');
    showToast('Settlement recorded.', 'success');
    loadSettlements();
  } catch (err) {
    globalErr.textContent = err.message || 'Could not create settlement.';
  } finally { btn.disabled = false; btn.textContent = 'Save'; }
});

// ── Init ──────────────────────────────────────────────────────────────────────
await loadGroups();
loadSettlements();
