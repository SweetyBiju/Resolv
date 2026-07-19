/**
 * expenses.js — Global view of all expenses. Filter, expand, add/edit.
 */
import { requireAuth } from '../core/auth.js';
import { getExpenses, getGroups, createExpense, updateExpense, deleteExpense, canDeleteExpense } from '../core/api.js';
import { renderSidebar } from '../components/sidebar.js';
import { renderBottomNav } from '../components/bottom-nav.js';
import { showToast } from '../components/toast.js';
import { openModal, closeModal, attachModalClose } from '../components/modal.js';
import { showSkeleton, hideSkeleton } from '../components/loader.js';
import { formatCurrency, formatDate, getInitials, parseSplitType, splitTypeBadgeClass, handleApiError, truncate, todayISO, capitalize } from '../core/utils.js';

const user = await requireAuth();
if (!user) throw new Error('Not authenticated');

renderSidebar(user);
renderBottomNav();
document.getElementById('topbar-avatar').textContent   = getInitials(user.username);
document.getElementById('topbar-username').textContent = user.username;

attachModalClose('modal-expense');

let _groups   = [];
let _expenses = [];
let _page     = 1;
let _hasMore  = false;
let _editingId = null;
let _currentSplitType = 'EQUAL';
let _currentGroupMembers = [];

// ── Load groups for filters and modal ─────────────────────────────────────────
async function loadGroups() {
  try {
    const data = await getGroups();
    _groups = data.results || data;
    const groupSel  = document.getElementById('filter-group');
    const expGrpSel = document.getElementById('exp-group');
    const opts = _groups.map(g => `<option value="${g.id}">${g.name}</option>`).join('');
    groupSel.innerHTML  = `<option value="">All Groups</option>` + opts;
    expGrpSel.innerHTML = `<option value="">Select Group</option>` + opts;
  } catch { /* silent */ }
}

// ── Load expenses ─────────────────────────────────────────────────────────────
async function loadExpenses(append = false) {
  const listEl  = document.getElementById('expenses-list');
  const emptyEl = document.getElementById('expenses-empty');
  const moreEl  = document.getElementById('load-more-container');

  if (!append) showSkeleton('expenses-list', 5, 'row');

  const params = {
    page: _page,
    ...(document.getElementById('filter-group').value    ? { group:    document.getElementById('filter-group').value } : {}),
    ...(document.getElementById('filter-category').value ? { category: document.getElementById('filter-category').value } : {}),
    ...(document.getElementById('filter-from').value     ? { date_after:  document.getElementById('filter-from').value } : {}),
    ...(document.getElementById('filter-to').value       ? { date_before: document.getElementById('filter-to').value } : {}),
  };

  try {
    const data = await getExpenses(params);
    if (!append) { hideSkeleton('expenses-list'); _expenses = []; listEl.innerHTML = ''; }
    const results = data.results || data;
    _hasMore = !!(data.next);
    _expenses = append ? [..._expenses, ...results] : results;

    emptyEl.classList.toggle('hidden', !!_expenses.length);
    moreEl.classList.toggle('hidden', !_hasMore);

    if (!append) listEl.innerHTML = '';
    results.forEach(exp => {
      const card = document.createElement('div');
      card.className = 'card card-sm';
      card.style.cssText = 'margin-bottom:var(--space-3);cursor:pointer';
      card.dataset.id = exp.id;
      card.innerHTML = `
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:var(--space-2)">
          <div style="flex:1;min-width:200px">
            <div class="fw-700">${truncate(exp.title, 40)}</div>
            <div style="display:flex;gap:var(--space-2);margin-top:4px;flex-wrap:wrap">
              <span class="badge badge-grey">${exp.group_name || '—'}</span>
              <span class="badge badge-grey">${capitalize(exp.category)}</span>
              <span class="badge ${splitTypeBadgeClass(exp.split_type)}">${exp.split_type}</span>
            </div>
          </div>
          <div style="text-align:right">
            <div class="text-2xl fw-700">${formatCurrency(exp.amount, exp.currency)}</div>
            <div class="text-muted text-xs">${exp.paid_by_username} · ${formatDate(exp.date)}</div>
          </div>
          <span style="color:var(--text-muted)">▾</span>
        </div>
        <div class="expense-detail-inner hidden" id="split-${exp.id}" style="margin-top:var(--space-3);padding-top:var(--space-3);border-top:var(--border)">
          ${exp.splits?.map(s => `<div class="text-sm text-muted">${s.username}: ${formatCurrency(s.amount_owed, exp.currency)}</div>`).join('') || 'No split data.'}
          ${exp.paid_by === user.id
            ? `<div style="margin-top:var(--space-3);display:flex;gap:8px">
                 <button class="btn btn-outline btn-sm" data-action="edit" data-id="${exp.id}">Edit</button>
                 <button class="btn btn-danger btn-sm" data-action="delete" data-id="${exp.id}">Delete</button>
               </div>` : ''}
        </div>`;
      listEl.appendChild(card);

      card.addEventListener('click', (e) => {
        if (e.target.closest('[data-action]')) return;
        document.getElementById(`split-${exp.id}`)?.classList.toggle('hidden');
      });
    });

    listEl.querySelectorAll('[data-action="edit"]').forEach(btn => {
      btn.addEventListener('click', (e) => { e.stopPropagation(); const exp = _expenses.find(x => x.id == btn.dataset.id); if (exp) openExpenseModal(exp); });
    });
    listEl.querySelectorAll('[data-action="delete"]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        if (!confirm('Delete this expense?')) return;
        try {
          const check = await canDeleteExpense(btn.dataset.id);
          if (!check.can_delete) { showToast('Cannot delete: settled debts exist.', 'error'); return; }
          await deleteExpense(btn.dataset.id);
          showToast('Expense deleted.', 'success');
          _page = 1; loadExpenses();
        } catch (err) { handleApiError(err, showToast); }
      });
    });
  } catch (err) {
    hideSkeleton('expenses-list');
    handleApiError(err, showToast);
  }
}

// ── Expense Modal ─────────────────────────────────────────────────────────────
function openExpenseModal(exp = null) {
  _editingId = exp?.id || null;
  _currentSplitType = exp?.split_type || 'EQUAL';
  document.getElementById('exp-modal-title').textContent = exp ? 'Edit Expense' : 'Add Expense';
  document.getElementById('exp-title').value    = exp?.title || '';
  document.getElementById('exp-amount').value   = exp?.amount || '';
  document.getElementById('exp-category').value = exp?.category || 'FOOD';
  document.getElementById('exp-date').value     = exp?.date || todayISO();
  document.getElementById('exp-currency').value = exp?.currency || 'INR';
  document.getElementById('exp-notes').value    = exp?.notes || '';
  document.getElementById('exp-global-error').textContent = '';
  if (exp?.group) document.getElementById('exp-group').value = exp.group;
  document.querySelectorAll('.split-pill').forEach(p => p.classList.toggle('active', p.dataset.split === _currentSplitType));
  _updatePaidByFromGroup();
  openModal('modal-expense');
}

async function _updatePaidByFromGroup() {
  const groupId = parseInt(document.getElementById('exp-group').value);
  if (!groupId) return;
  const g = _groups.find(x => x.id === groupId);
  _currentGroupMembers = (g?.memberships || []).map(m => m.user);
  const sel = document.getElementById('exp-paid-by');
  if (sel) sel.innerHTML = _currentGroupMembers.map(m =>
    `<option value="${m.id}" ${m.id === user.id ? 'selected' : ''}>${m.username}</option>`).join('');
}

document.getElementById('exp-group')?.addEventListener('change', _updatePaidByFromGroup);
document.querySelectorAll('.split-pill').forEach(pill => {
  pill.addEventListener('click', () => {
    document.querySelectorAll('.split-pill').forEach(p => p.classList.remove('active'));
    pill.classList.add('active'); _currentSplitType = pill.dataset.split;
  });
});

document.getElementById('btn-add-expense')?.addEventListener('click', () => openExpenseModal());
document.getElementById('exp-cancel')?.addEventListener('click', () => closeModal('modal-expense'));

document.getElementById('exp-submit')?.addEventListener('click', async () => {
  const btn = document.getElementById('exp-submit');
  const globalErr = document.getElementById('exp-global-error');
  globalErr.textContent = '';
  const groupId = parseInt(document.getElementById('exp-group').value);
  const title   = document.getElementById('exp-title').value.trim();
  const amount  = parseFloat(document.getElementById('exp-amount').value);
  if (!groupId) { globalErr.textContent = 'Please select a group.'; return; }
  if (!title)   { globalErr.textContent = 'Title is required.'; return; }
  if (!amount || amount <= 0) { globalErr.textContent = 'Enter a valid amount.'; return; }

  const payload = {
    group: groupId, title, amount,
    category:    document.getElementById('exp-category').value,
    date:        document.getElementById('exp-date').value,
    currency:    document.getElementById('exp-currency').value,
    paid_by:     parseInt(document.getElementById('exp-paid-by').value),
    split_type:  _currentSplitType, split_data: [],
    notes:       document.getElementById('exp-notes').value,
  };

  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
  try {
    if (_editingId) await updateExpense(_editingId, payload);
    else            await createExpense(payload);
    closeModal('modal-expense');
    showToast(_editingId ? 'Expense updated.' : 'Expense added.', 'success');
    _page = 1; loadExpenses();
  } catch (err) {
    globalErr.textContent = err.message || 'Could not save.';
  } finally { btn.disabled = false; btn.textContent = 'Save Expense'; }
});

// ── Filters + Load More ───────────────────────────────────────────────────────
['filter-group','filter-category','filter-from','filter-to'].forEach(id => {
  document.getElementById(id)?.addEventListener('change', () => { _page = 1; loadExpenses(); });
});
document.getElementById('btn-clear-filters')?.addEventListener('click', () => {
  ['filter-group','filter-category','filter-from','filter-to'].forEach(id => {
    const el = document.getElementById(id); if (el) el.value = '';
  });
  _page = 1; loadExpenses();
});
document.getElementById('btn-load-more')?.addEventListener('click', () => { _page++; loadExpenses(true); });

// ── Init ──────────────────────────────────────────────────────────────────────
await loadGroups();
loadExpenses();
