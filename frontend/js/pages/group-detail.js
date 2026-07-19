/**
 * group-detail.js — Full group view: balances, expenses, settlements, members.
 * URL: group-detail.html?id=<group_id>
 */
import { requireAuth } from '../core/auth.js';
import {
  getGroup, getGroupBalances, getSuggestedSettlements,
  getExpenses, createExpense, updateExpense, deleteExpense, canDeleteExpense,
  getSettlements, createSettlement, confirmSettlement, cancelSettlement,
  addMember, removeMember, transferAdmin, getInviteCode, regenerateInviteCode, deleteGroup, updateGroup,
  getUserProfile
} from '../core/api.js';
import { renderSidebar } from '../components/sidebar.js';
import { renderBottomNav } from '../components/bottom-nav.js';
import { showToast } from '../components/toast.js';
import { openModal, closeModal, attachModalClose } from '../components/modal.js';
import {
  formatCurrency, formatDate, getInitials, getParam,
  parseSplitType, splitTypeBadgeClass, settlementStatusBadge,
  handleApiError, truncate, todayISO, capitalize,
} from '../core/utils.js';

const user = await requireAuth();
if (!user) throw new Error('Not authenticated');

const GROUP_ID = parseInt(getParam('id'));
if (!GROUP_ID) { window.location.href = '/groups.html'; throw 0; }

renderSidebar(user);
renderBottomNav();
document.getElementById('topbar-avatar').textContent   = getInitials(user.username);
document.getElementById('topbar-username').textContent = user.username;

let _group = null;
let _members = [];
let _editingExpenseId = null;
let _currentSplitType = 'EQUAL';

// ── Load Group ────────────────────────────────────────────────────────────────
async function loadGroup() {
  try {
    _group = await getGroup(GROUP_ID);
    document.title = `${_group.name} — Resolv`;
    document.getElementById('topbar-group-name').textContent = _group.name;
    document.getElementById('group-name-heading').textContent = _group.name;
    document.getElementById('group-emoji').textContent = _group.emoji || '';

    _members = (_group.memberships || []).map(m => m.user);

    const isAdmin = _group.admin === user.id;
    const metaEl  = document.getElementById('group-meta');
    metaEl.innerHTML = `
      <span class="badge badge-grey">${_group.currency || 'INR'}</span>
      <span class="badge">${_group.member_count || _members.length} Members</span>`;

    const actionsEl = document.getElementById('group-actions');
    if (isAdmin) {
      actionsEl.innerHTML = `
        <button class="btn btn-outline btn-sm" id="btn-invite">Invite Code</button>
        <button class="btn btn-outline btn-sm" id="btn-edit-group">Edit</button>
        <button class="btn btn-danger btn-sm" id="btn-delete-group">Delete</button>`;
      document.getElementById('btn-invite')?.addEventListener('click', showInviteModal);
      document.getElementById('btn-edit-group')?.addEventListener('click', openEditGroupModal);
      document.getElementById('btn-delete-group')?.addEventListener('click', () => openModal('modal-delete-group'));
    }

    // Populate expense payer dropdown
    populatePaidBySelect();
    populateSettlementReceiverSelect();
  } catch (err) {
    handleApiError(err, showToast);
  }
}

function populatePaidBySelect() {
  const sel = document.getElementById('exp-paid-by');
  if (!sel) return;
  sel.innerHTML = _members.map(m =>
    `<option value="${m.id}" ${m.id === user.id ? 'selected' : ''}>${m.username}${m.id === user.id ? ' (me)' : ''}</option>`
  ).join('');
}

function populateSettlementReceiverSelect() {
  const sel = document.getElementById('gs-receiver');
  if (!sel) return;
  sel.innerHTML = _members
    .filter(m => m.id !== user.id)
    .map(m => `<option value="${m.id}">${m.username}</option>`).join('');

  if (_group?.currency) {
    const currSel = document.getElementById('gs-currency');
    if (currSel) currSel.value = _group.currency;
  }
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => { b.classList.remove('active'); b.setAttribute('aria-selected','false'); });
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active'); btn.setAttribute('aria-selected','true');
    document.getElementById(`panel-${btn.dataset.tab}`).classList.add('active');

    if (btn.dataset.tab === 'balances')    loadBalances();
    if (btn.dataset.tab === 'expenses')    loadExpenses();
    if (btn.dataset.tab === 'settlements') loadGroupSettlements();
    if (btn.dataset.tab === 'members')     loadMembers();
  });
});

// ── BALANCES ──────────────────────────────────────────────────────────────────
async function loadBalances() {
  const tbody = document.getElementById('balances-tbody');
  tbody.innerHTML = '<tr><td colspan="4" class="text-muted text-sm">Loading…</td></tr>';
  try {
    const balances  = await getGroupBalances(GROUP_ID);
    const suggested = await getSuggestedSettlements(GROUP_ID);

    // Personal Balance Banner
    const bannerEl = document.getElementById('personal-balance-banner');
    if (bannerEl) {
      const myEntry = (balances || []).find(b => b.user_id === user.id);
      const myNet   = parseFloat(myEntry?.net_balance ?? 0);
      if (myNet < 0) {
        bannerEl.innerHTML = `<div class="card card-sm" style="padding:16px;background:#FEF2F2;border-left:4px solid var(--red);display:flex;align-items:center;justify-content:space-between;color:#991B1B">
          <div><div class="fw-700" style="font-size:16px">🔴 You owe ${formatCurrency(Math.abs(myNet), _group?.currency)} overall</div><div class="text-xs" style="opacity:0.8;margin-top:2px">Pay back group members using the suggested settlements below.</div></div>
        </div>`;
      } else if (myNet > 0) {
        bannerEl.innerHTML = `<div class="card card-sm" style="padding:16px;background:#EFF6FF;border-left:4px solid var(--blue);display:flex;align-items:center;justify-content:space-between;color:#1E40AF">
          <div><div class="fw-700" style="font-size:16px">🟢 You are owed ${formatCurrency(myNet, _group?.currency)} overall</div><div class="text-xs" style="opacity:0.8;margin-top:2px">Members owe you money. Remind them to record settlements when they pay.</div></div>
        </div>`;
      } else {
        bannerEl.innerHTML = `<div class="card card-sm" style="padding:14px 16px;background:var(--surface);border-left:4px solid #9CA3AF;color:var(--text-main);display:flex;align-items:center;gap:8px">
          <span style="font-size:18px">🎉</span> <span class="fw-600">You are all settled up in this group!</span>
        </div>`;
      }
    }

    tbody.innerHTML = (balances || []).map(b => {
      const net = parseFloat(b.net_balance ?? b.net ?? 0);
      const cls = net > 0 ? 'text-blue' : net < 0 ? 'text-red' : 'text-muted';
      return `<tr>
        <td><div style="display:flex;align-items:center;gap:8px"><div class="avatar" style="width:28px;height:28px;font-size:10px">${getInitials(b.username||'?')}</div>${b.username||'—'}${b.user_id === user.id ? ' (you)' : ''}</div></td>
        <td>${formatCurrency(b.total_paid ?? 0, _group?.currency)}</td>
        <td>${formatCurrency(b.total_owed ?? 0, _group?.currency)}</td>
        <td class="${cls} fw-700">${net > 0 ? `gets back ${formatCurrency(net, _group?.currency)}` : net < 0 ? `owes ${formatCurrency(Math.abs(net), _group?.currency)}` : 'settled'}</td>
      </tr>`;
    }).join('') || '<tr><td colspan="4" class="text-muted text-sm">No balance data.</td></tr>';

    const payments = suggested.suggested_payments || [];
    const sugEl    = document.getElementById('suggested-list');
    if (!payments.length) {
      sugEl.innerHTML = '<div class="empty-state" style="padding:var(--space-4)">✓ All settled up!</div>';
    } else {
      sugEl.innerHTML = payments.map(p => {
        const isFromMe = p.from_user_id === user.id;
        const isToMe   = p.to_user_id   === user.id;
        const fromText = isFromMe ? 'You' : (p.from_user || `User ${p.from_user_id}`);
        const toText   = isToMe   ? 'you' : (p.to_user   || `User ${p.to_user_id}`);
        const textCls  = isFromMe ? 'text-red' : isToMe ? 'text-blue' : '';
        return `
          <div class="action-row" style="padding:12px 16px">
            <div class="text-sm">
              <span class="fw-700 ${textCls}">${fromText} owe${isFromMe ? '' : 's'} ${toText}</span>
              <span class="fw-700" style="margin-left:4px">${formatCurrency(p.amount, _group?.currency)}</span>
            </div>
            <button class="btn ${isFromMe ? 'btn-primary' : 'btn-outline'} btn-sm" data-from="${p.from_user_id}" data-to="${p.to_user_id}" data-amount="${p.amount}" data-action="record">Record Payment</button>
          </div>`;
      }).join('');

      sugEl.querySelectorAll('[data-action="record"]').forEach(btn => {
        btn.addEventListener('click', () => {
          document.getElementById('gs-amount').value = btn.dataset.amount;
          const recSel = document.getElementById('gs-receiver');
          if (recSel) {
            const opt = Array.from(recSel.options).find(o => o.value == btn.dataset.to);
            if (opt) recSel.value = opt.value;
          }
          openModal('modal-group-settlement');
        });
      });
    }
  } catch (err) { handleApiError(err, showToast); }
}

// ── EXPENSES ──────────────────────────────────────────────────────────────────
async function loadExpenses() {
  const tbody = document.getElementById('expenses-tbody');
  tbody.innerHTML = '<tr><td colspan="7" class="text-muted text-sm">Loading…</td></tr>';
  try {
    const data     = await getExpenses({ group: GROUP_ID });
    const expenses = data.results || data;
    const emptyEl  = document.getElementById('expenses-empty');

    if (!expenses.length) {
      tbody.innerHTML = '';
      emptyEl.classList.remove('hidden');
      return;
    }
    emptyEl.classList.add('hidden');

    tbody.innerHTML = expenses.map(exp => `
      <tr class="expense-row" data-id="${exp.id}">
        <td>
          <div class="fw-600">${truncate(exp.title, 30)}</div>
        </td>
        <td class="fw-700">${formatCurrency(exp.amount, exp.currency)}</td>
        <td class="text-muted text-sm">${exp.paid_by_username || '—'}</td>
        <td><span class="badge ${splitTypeBadgeClass(exp.split_type)}">${exp.split_type}</span></td>
        <td><span class="badge badge-grey">${capitalize(exp.category)}</span></td>
        <td class="text-muted text-sm">${formatDate(exp.date)}</td>
        <td style="display:flex;gap:4px;justify-content:flex-end">
          ${exp.paid_by === user.id || _group?.admin === user.id
            ? `<button class="btn btn-ghost btn-sm" data-action="edit" data-id="${exp.id}">✏️</button>
               <button class="btn btn-ghost btn-sm" data-action="delete" data-id="${exp.id}">🗑️</button>`
            : ''}
        </td>
      </tr>
      <tr class="expense-detail-row hidden" id="detail-${exp.id}">
        <td colspan="7">
          <div class="expense-detail-inner">
            ${exp.splits?.map(s => `<div class="text-sm text-muted">${s.username}: ${formatCurrency(s.amount_owed, exp.currency)}</div>`).join('') || 'No split detail.'}
          </div>
        </td>
      </tr>`).join('');

    // Row click → expand
    tbody.querySelectorAll('.expense-row').forEach(row => {
      row.addEventListener('click', (e) => {
        if (e.target.closest('[data-action]')) return;
        const detail = document.getElementById(`detail-${row.dataset.id}`);
        detail?.classList.toggle('hidden');
      });
    });

    // Edit/Delete buttons
    tbody.querySelectorAll('[data-action="edit"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const exp = expenses.find(x => x.id == btn.dataset.id);
        if (exp) openExpenseModal(exp);
      });
    });
    tbody.querySelectorAll('[data-action="delete"]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        if (!confirm('Delete this expense?')) return;
        try {
          const check = await canDeleteExpense(btn.dataset.id);
          if (!check.can_delete) { showToast('Cannot delete: settled debts exist.', 'error'); return; }
          await deleteExpense(btn.dataset.id);
          showToast('Expense deleted.', 'success');
          loadExpenses(); loadBalances();
        } catch (err) { handleApiError(err, showToast); }
      });
    });
  } catch (err) { handleApiError(err, showToast); }
}

// ── Expense Modal ─────────────────────────────────────────────────────────────
function openExpenseModal(exp = null) {
  _editingExpenseId = exp?.id || null;
  _currentSplitType = exp?.split_type || 'EQUAL';
  document.getElementById('expense-modal-title').textContent = exp ? 'Edit Expense' : 'Add Expense';
  document.getElementById('exp-title').value    = exp?.title || '';
  document.getElementById('exp-amount').value   = exp?.amount || '';
  document.getElementById('exp-category').value = exp?.category || 'FOOD';
  document.getElementById('exp-date').value     = exp?.date || todayISO();
  document.getElementById('exp-currency').value = exp?.currency || _group?.currency || 'INR';
  document.getElementById('exp-notes').value    = exp?.notes || '';
  document.getElementById('exp-receipt').value  = exp?.receipt_url || '';
  
  document.getElementById('exp-global-error').textContent = '';

  document.querySelectorAll('.split-pill').forEach(p => p.classList.toggle('active', p.dataset.split === _currentSplitType));
  renderSplitSection();
  openModal('modal-expense');
}

function renderSplitSection() {
  const el = document.getElementById('exp-split-section');
  if (_currentSplitType === 'EQUAL') { el.innerHTML = `<p class="text-sm text-muted">Split equally among all ${_members.length} members.</p>`; return; }
  if (_currentSplitType === 'EXACT') {
    el.innerHTML = `<div style="display:flex;flex-direction:column;gap:8px">
      ${_members.map(m => `<div style="display:flex;align-items:center;gap:8px"><span style="flex:1;font-size:13px;font-weight:600">${m.username}</span><input class="form-input exact-amount" data-uid="${m.id}" type="number" min="0" step="0.01" placeholder="0.00" style="width:120px"></div>`).join('')}
    </div>`;
    return;
  }
  if (_currentSplitType === 'PERCENT') {
    el.innerHTML = `<div style="display:flex;flex-direction:column;gap:8px">
      ${_members.map(m => `<div style="display:flex;align-items:center;gap:8px"><span style="flex:1;font-size:13px;font-weight:600">${m.username}</span><input class="form-input pct-amount" data-uid="${m.id}" type="number" min="0" step="0.01" placeholder="0" style="width:100px"><span class="text-muted text-sm">%</span></div>`).join('')}
    </div>`;
    return;
  }
  if (_currentSplitType === 'ITEM') {
    el.innerHTML = `<div id="items-list" style="display:flex;flex-direction:column;gap:8px"></div>
      <button type="button" class="btn btn-outline btn-sm" id="btn-add-item" style="margin-top:8px">+ Add Item</button>`;
    document.getElementById('btn-add-item')?.addEventListener('click', addItemRow);
    return;
  }
}

function addItemRow() {
  const list = document.getElementById('items-list');
  const row  = document.createElement('div');
  row.style.cssText = 'display:flex;gap:8px;align-items:center;flex-wrap:wrap';
  row.innerHTML = `
    <input class="form-input item-name" type="text" placeholder="Item name" style="flex:1;min-width:120px">
    <input class="form-input item-amount" type="number" min="0" step="0.01" placeholder="0.00" style="width:90px">
    <span class="text-sm text-muted">for:</span>
    ${_members.map(m => `<label style="display:flex;align-items:center;gap:4px;font-size:12px"><input type="checkbox" class="item-user" value="${m.id}"> ${m.username}</label>`).join('')}
    <button type="button" class="btn btn-ghost btn-sm" onclick="this.closest('div').remove()">✕</button>`;
  list.appendChild(row);
}

document.querySelectorAll('.split-pill').forEach(pill => {
  pill.addEventListener('click', () => {
    document.querySelectorAll('.split-pill').forEach(p => p.classList.remove('active'));
    pill.classList.add('active');
    _currentSplitType = pill.dataset.split;
    renderSplitSection();
  });
});

function buildSplitData() {
  if (_currentSplitType === 'EQUAL') return [];
  if (_currentSplitType === 'EXACT') {
    return Array.from(document.querySelectorAll('.exact-amount'))
      .filter(i => i.value)
      .map(i => ({ user: parseInt(i.dataset.uid), amount: parseFloat(i.value) }));
  }
  if (_currentSplitType === 'PERCENT') {
    return Array.from(document.querySelectorAll('.pct-amount'))
      .filter(i => i.value)
      .map(i => ({ user: parseInt(i.dataset.uid), percentage: parseFloat(i.value) }));
  }
  if (_currentSplitType === 'ITEM') {
    return Array.from(document.querySelectorAll('#items-list > div')).map(row => ({
      name:     row.querySelector('.item-name')?.value || '',
      amount:   parseFloat(row.querySelector('.item-amount')?.value || 0),
      user_ids: Array.from(row.querySelectorAll('.item-user:checked')).map(c => parseInt(c.value)),
    }));
  }
  return [];
}

document.getElementById('btn-add-expense')?.addEventListener('click', () => openExpenseModal());
document.getElementById('exp-cancel')?.addEventListener('click', () => closeModal('modal-expense'));
attachModalClose('modal-expense');

document.getElementById('exp-submit')?.addEventListener('click', async () => {
  const btn = document.getElementById('exp-submit');
  const globalErr = document.getElementById('exp-global-error');
  globalErr.textContent = '';

  const payload = {
    title:       document.getElementById('exp-title').value.trim(),
    amount:      parseFloat(document.getElementById('exp-amount').value),
    group:       GROUP_ID,
    category:    document.getElementById('exp-category').value,
    date:        document.getElementById('exp-date').value,
    currency:    document.getElementById('exp-currency').value,
    paid_by:     parseInt(document.getElementById('exp-paid-by').value),
    split_type:  _currentSplitType,
    split_data:  buildSplitData(),
    notes:       document.getElementById('exp-notes').value,
    receipt_url: document.getElementById('exp-receipt').value || null,
  };

  if (!payload.title) { globalErr.textContent = 'Title is required.'; return; }
  if (!payload.amount || payload.amount <= 0) { globalErr.textContent = 'Enter a valid amount.'; return; }

  // Frontend Split Validations
  if (payload.split_type === 'EXACT') {
    const exactSum = payload.split_data.reduce((sum, item) => sum + (item.amount || 0), 0);
    if (Math.abs(exactSum - payload.amount) > 0.01) {
      globalErr.textContent = `Sum of exact splits (${exactSum.toFixed(2)}) must equal expense amount (${payload.amount.toFixed(2)}).`;
      return;
    }
  } else if (payload.split_type === 'PERCENT') {
    const percentSum = payload.split_data.reduce((sum, item) => sum + (item.percentage || 0), 0);
    if (Math.abs(percentSum - 100) > 0.01) {
      globalErr.textContent = `Sum of percentages (${percentSum.toFixed(2)}%) must equal 100%.`;
      return;
    }
  } else if (payload.split_type === 'ITEM') {
    if (!payload.split_data.length) {
      globalErr.textContent = 'Please add at least one item.';
      return;
    }
    for (const item of payload.split_data) {
      if (!item.name.trim()) {
        globalErr.textContent = 'Item name is required.';
        return;
      }
      if (!item.amount || item.amount <= 0) {
        globalErr.textContent = `Item "${item.name}" must have a valid positive amount.`;
        return;
      }
      if (!item.user_ids || !item.user_ids.length) {
        globalErr.textContent = `Please select at least one member for item "${item.name}".`;
        return;
      }
    }
    const totalItemsAmount = payload.split_data.reduce((sum, item) => sum + item.amount, 0);
    if (Math.abs(totalItemsAmount - payload.amount) > 0.01) {
      globalErr.textContent = `Sum of items (${totalItemsAmount.toFixed(2)}) must equal expense amount (${payload.amount.toFixed(2)}).`;
      return;
    }
  }

  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
  try {
    if (_editingExpenseId) await updateExpense(_editingExpenseId, payload);
    else                   await createExpense(payload);
    closeModal('modal-expense');
    showToast(_editingExpenseId ? 'Expense updated.' : 'Expense added.', 'success');
    loadExpenses(); loadBalances();
  } catch (err) {
    globalErr.textContent = err.message || 'Could not save expense.';
    handleApiError(err, showToast);
  } finally {
    btn.disabled = false; btn.textContent = 'Save Expense';
  }
});

// ── SETTLEMENTS ───────────────────────────────────────────────────────────────
async function loadGroupSettlements() {
  const listEl = document.getElementById('settlements-list');
  const emptyEl = document.getElementById('settlements-empty');
  listEl.innerHTML = '<div class="text-muted text-sm">Loading…</div>';
  try {
    const data = await getSettlements({ group: GROUP_ID });
    const settlements = data.results || data;
    emptyEl.classList.toggle('hidden', !!settlements.length);

    listEl.innerHTML = settlements.map(s => `
      <div class="card card-sm" style="margin-bottom:var(--space-3);display:flex;align-items:center;justify-content:space-between;gap:var(--space-3);flex-wrap:wrap">
        <div>
          <div class="text-sm fw-700">${s.payer_username} → ${s.receiver_username}</div>
          <div class="text-muted text-xs">${formatCurrency(s.amount, s.currency)} · ${formatDate(s.created_at)}</div>
        </div>
        <div style="display:flex;align-items:center;gap:var(--space-2)">
          <span class="badge ${settlementStatusBadge(s.status)}">${s.status}</span>
          ${s.status === 'PENDING' && s.receiver === user.id
            ? `<button class="btn btn-green btn-sm" data-id="${s.id}" data-action="confirm">Confirm</button>` : ''}
          ${s.status === 'PENDING' && s.payer === user.id
            ? `<button class="btn btn-ghost btn-sm text-red" data-id="${s.id}" data-action="cancel">Cancel</button>` : ''}
        </div>
      </div>`).join('');

    listEl.querySelectorAll('[data-action="confirm"]').forEach(btn => {
      btn.addEventListener('click', async () => {
        btn.disabled = true;
        try { await confirmSettlement(btn.dataset.id); showToast('Confirmed!', 'success'); loadGroupSettlements(); loadBalances(); }
        catch (err) { handleApiError(err, showToast); btn.disabled = false; }
      });
    });
    listEl.querySelectorAll('[data-action="cancel"]').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('Cancel this settlement?')) return;
        try { await cancelSettlement(btn.dataset.id); showToast('Cancelled.', 'info'); loadGroupSettlements(); }
        catch (err) { handleApiError(err, showToast); }
      });
    });
  } catch (err) { handleApiError(err, showToast); }
}

document.getElementById('btn-create-settlement')?.addEventListener('click', () => openModal('modal-group-settlement'));
document.getElementById('gs-cancel')?.addEventListener('click', () => closeModal('modal-group-settlement'));
attachModalClose('modal-group-settlement');

document.getElementById('gs-submit')?.addEventListener('click', async () => {
  const btn = document.getElementById('gs-submit');
  const globalErr = document.getElementById('gs-global-error');
  globalErr.textContent = '';
  const receiver = parseInt(document.getElementById('gs-receiver').value);
  const amount   = parseFloat(document.getElementById('gs-amount').value);
  const currency = document.getElementById('gs-currency').value;
  if (!amount || amount <= 0) { globalErr.textContent = 'Enter a valid amount.'; return; }
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
  try {
    await createSettlement({ group: GROUP_ID, receiver, amount, currency });
    closeModal('modal-group-settlement');
    showToast('Settlement recorded.', 'success');
    loadGroupSettlements(); loadBalances();
  } catch (err) {
    globalErr.textContent = err.message || 'Could not create settlement.';
  } finally { btn.disabled = false; btn.textContent = 'Record Settlement'; }
});

// ── MEMBERS ───────────────────────────────────────────────────────────────────
async function loadMembers() {
  const listEl = document.getElementById('members-list');
  const isAdmin = _group?.admin === user.id;
  listEl.innerHTML = (_group?.memberships || []).map(m => `
    <div class="member-row">
      <div class="member-profile-btn" data-uid="${m.user.id}" style="display:flex;align-items:center;gap:12px;flex:1;cursor:pointer;">
        <div class="avatar">${getInitials(m.user.username)}</div>
        <div style="flex:1">
          <div class="fw-700 text-sm">${m.user.username}${m.user.id === user.id ? ' (you)' : ''}</div>
          <div class="text-muted text-xs">${m.role} · since ${formatDate(m.joined_at)}</div>
        </div>
      </div>
      <span class="badge ${m.role === 'ADMIN' ? 'badge-purple' : 'badge-grey'}">${m.role}</span>
      <div style="display:flex;gap:4px">
        ${isAdmin && m.user.id !== user.id
          ? `<button class="btn btn-outline btn-sm" data-uid="${m.user.id}" data-action="transfer">Make Admin</button>
             <button class="btn btn-danger btn-sm" data-uid="${m.user.id}" data-action="remove">Remove</button>` : ''}
      </div>
    </div>`).join('');

  listEl.querySelectorAll('.member-profile-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      try {
        const profile = await getUserProfile(btn.dataset.uid);
        document.getElementById('up-avatar').textContent = getInitials(profile.username);
        document.getElementById('up-username').textContent = profile.username;
        document.getElementById('up-email').textContent = profile.email || '';
        document.getElementById('up-score').textContent = (parseFloat(profile.reliability_score || 0)).toFixed(1);
        document.getElementById('up-settlements').textContent = profile.settlement_count || 0;
        document.getElementById('up-joined').textContent = formatDate(profile.date_joined);
        openModal('modal-user-profile');
      } catch (err) { handleApiError(err, showToast); }
    });
  });

  listEl.querySelectorAll('[data-action="transfer"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm(`Transfer admin rights to this member? You will be demoted to a regular member.`)) return;
      try {
        await transferAdmin(GROUP_ID, btn.dataset.uid);
        showToast('Admin rights transferred.', 'success');
        await loadGroup(); loadMembers();
      } catch (err) { handleApiError(err, showToast); }
    });
  });

  listEl.querySelectorAll('[data-action="remove"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm(`Remove this member?`)) return;
      try {
        await removeMember(GROUP_ID, btn.dataset.uid);
        showToast('Member removed.', 'success');
        await loadGroup(); loadMembers();
      } catch (err) { handleApiError(err, showToast); }
    });
  });

  // Invite code
  const codeCard = document.getElementById('invite-code-card');
  if (isAdmin && _group?.invite_code) {
    codeCard.classList.remove('hidden');
    document.getElementById('invite-code-display').textContent = _group.invite_code;
  } else {
    codeCard.classList.add('hidden');
  }
}

document.getElementById('btn-add-member')?.addEventListener('click', () => openModal('modal-add-member'));
document.getElementById('am-cancel')?.addEventListener('click', () => closeModal('modal-add-member'));
attachModalClose('modal-add-member');

document.getElementById('am-submit')?.addEventListener('click', async () => {
  const identifier = document.getElementById('am-username-email').value.trim();
  const errEl = document.getElementById('am-error');
  errEl.textContent = '';
  if (!identifier) { errEl.textContent = 'Username or Email is required.'; return; }
  const btn = document.getElementById('am-submit');
  btn.disabled = true;
  try {
    await addMember(GROUP_ID, identifier);
    closeModal('modal-add-member');
    showToast('Member added.', 'success');
    await loadGroup(); loadMembers();
  } catch (err) { errEl.textContent = err.message || 'Could not add member.'; }
  finally { btn.disabled = false; }
});

// Copy invite code
document.getElementById('btn-copy-invite')?.addEventListener('click', () => {
  navigator.clipboard?.writeText(_group?.invite_code || '');
  showToast('Invite code copied!', 'success');
});
document.getElementById('btn-regen-invite')?.addEventListener('click', async () => {
  try {
    const res = await regenerateInviteCode(GROUP_ID);
    _group.invite_code = res.invite_code;
    document.getElementById('invite-code-display').textContent = res.invite_code;
    showToast('Invite code regenerated.', 'success');
  } catch (err) { handleApiError(err, showToast); }
});

// ── Invite Modal ──────────────────────────────────────────────────────────────
async function showInviteModal() {
  try {
    const res = await getInviteCode(GROUP_ID);
    document.getElementById('invite-modal-code').textContent = res.invite_code;
    document.getElementById('btn-copy-invite-modal').onclick = () => {
      navigator.clipboard?.writeText(res.invite_code);
      showToast('Copied!', 'success');
    };
    openModal('modal-invite');
  } catch (err) { handleApiError(err, showToast); }
}
attachModalClose('modal-invite');

// ── Delete Group ──────────────────────────────────────────────────────────────
document.getElementById('del-group-cancel')?.addEventListener('click', () => closeModal('modal-delete-group'));
document.getElementById('del-group-confirm')?.addEventListener('click', async () => {
  const btn = document.getElementById('del-group-confirm');
  btn.disabled = true;
  try {
    await deleteGroup(GROUP_ID);
    window.location.href = '/groups.html';
  } catch (err) {
    document.getElementById('del-group-error').textContent = err.message || 'Cannot delete group.';
    btn.disabled = false;
  }
});

// ── Edit Group ────────────────────────────────────────────────────────────────
function openEditGroupModal() {
  document.getElementById('eg-name').value = _group?.name || '';
  document.getElementById('eg-currency').value = _group?.currency || 'INR';
  document.getElementById('eg-description').value = _group?.description || '';
  
  const selectedEmoji = _group?.emoji || '';
  document.getElementById('eg-emoji').value = selectedEmoji;
  document.querySelectorAll('#eg-emoji-picker .emoji-opt').forEach(opt => {
    opt.classList.toggle('selected', opt.dataset.emoji === selectedEmoji);
  });
  
  document.getElementById('eg-global-error').textContent = '';
  openModal('modal-edit-group');
}

document.querySelectorAll('#eg-emoji-picker .emoji-opt').forEach(opt => {
  opt.addEventListener('click', () => {
    document.querySelectorAll('#eg-emoji-picker .emoji-opt').forEach(o => o.classList.remove('selected'));
    opt.classList.add('selected');
    document.getElementById('eg-emoji').value = opt.dataset.emoji;
  });
});

document.getElementById('eg-cancel')?.addEventListener('click', () => closeModal('modal-edit-group'));
attachModalClose('modal-edit-group');

document.getElementById('eg-submit')?.addEventListener('click', async () => {
  const name = document.getElementById('eg-name').value.trim();
  const currency = document.getElementById('eg-currency').value;
  const emoji = document.getElementById('eg-emoji').value;
  const description = document.getElementById('eg-description').value.trim();
  
  if (!name) {
    document.getElementById('eg-name-error').textContent = 'Name is required.';
    return;
  }
  document.getElementById('eg-name-error').textContent = '';

  const btn = document.getElementById('eg-submit');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>';
  try {
    const updated = await updateGroup(GROUP_ID, { name, currency, emoji, description });
    _group = updated;
    closeModal('modal-edit-group');
    showToast('Group updated successfully.', 'success');
    await loadGroup();
  } catch (err) {
    document.getElementById('eg-global-error').textContent = err.message || 'Could not update group.';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Save Changes';
  }
});

attachModalClose('modal-user-profile');

// ── Init ──────────────────────────────────────────────────────────────────────
await loadGroup();
loadBalances();
loadExpenses();
