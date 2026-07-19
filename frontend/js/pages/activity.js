/**
 * activity.js — Full audit trail, grouped by date, with filters and load more.
 */
import { requireAuth } from '../core/auth.js';
import { getActivity } from '../core/api.js';
import { renderSidebar } from '../components/sidebar.js';
import { renderBottomNav } from '../components/bottom-nav.js';
import { showToast } from '../components/toast.js';
import { formatDate, formatTime, formatRelativeDate, getInitials, handleApiError, debounce, formatActivityDetail } from '../core/utils.js?v=2';

const user = await requireAuth();
if (!user) throw new Error('Not authenticated');

renderSidebar(user);
renderBottomNav();
document.getElementById('topbar-avatar').textContent   = getInitials(user.username);
document.getElementById('topbar-username').textContent = user.username;

const ACTION_ICONS = {
  EXPENSE_CREATED:       '💰',
  EXPENSE_UPDATED:       '✏️',
  EXPENSE_DELETED:       '🗑️',
  SETTLEMENT_CREATED:    '💸',
  SETTLEMENT_CONFIRMED:  '✅',
  SETTLEMENT_CANCELLED:  '❌',
  GROUP_CREATED:         '👥',
  GROUP_DELETED:         '🚮',
  MEMBER_ADDED:          '➕',
  MEMBER_JOINED:         '🔗',
  MEMBER_REMOVED:        '➖',
};

let _page    = 1;
let _hasMore = false;
let _entries = [];

// ── Render timeline ───────────────────────────────────────────────────────────
function renderTimeline(entries, append = false) {
  const container = document.getElementById('activity-timeline');
  const emptyEl   = document.getElementById('activity-empty');
  const moreEl    = document.getElementById('load-more-wrap');

  emptyEl.classList.toggle('hidden', !!entries.length);
  moreEl.classList.toggle('hidden', !_hasMore);

  if (!append) container.innerHTML = '';
  if (!entries.length && !append) return;

  // Group by date
  const groups = {};
  entries.forEach(entry => {
    const dateKey = formatDate(entry.timestamp);
    if (!groups[dateKey]) groups[dateKey] = [];
    groups[dateKey].push(entry);
  });

  Object.entries(groups).forEach(([date, items]) => {
    // Only add date header if first entry of this date in container
    const existingHeader = container.querySelector(`[data-date="${date}"]`);
    let groupEl;
    if (existingHeader) {
      groupEl = existingHeader.nextElementSibling;
    } else {
      const header = document.createElement('div');
      header.className = 'timeline-date';
      header.dataset.date = date;
      header.textContent  = formatRelativeDate(items[0].timestamp).toUpperCase() === 'TODAY'
        ? 'TODAY'
        : formatRelativeDate(items[0].timestamp).toUpperCase() === 'YESTERDAY'
        ? 'YESTERDAY'
        : date;
      container.appendChild(header);

      groupEl = document.createElement('div');
      groupEl.style.marginBottom = 'var(--space-4)';
      container.appendChild(groupEl);
    }

    items.forEach(entry => {
      const icon   = ACTION_ICONS[entry.action] || '📌';
      const label  = (entry.action || '').replace(/_/g, ' ');
      const detail = formatActivityDetail(entry);

      const expandedView = buildExpandedView(entry);
      const row = document.createElement('div');
      row.className    = 'activity-entry';
      row.dataset.id   = entry.id;
      row.innerHTML = `
        <div class="activity-icon">${icon}</div>
        <div class="activity-body">
          <div class="activity-action">${label}</div>
          <div class="activity-detail">${detail}</div>
          ${expandedView ? `<div class="activity-expanded" id="exp-${entry.id}">${expandedView}</div>` : ''}
        </div>
        <div class="activity-time">${formatTime(entry.timestamp)}</div>`;

      if (expandedView) {
        row.addEventListener('click', () => {
          const expEl = document.getElementById(`exp-${entry.id}`);
          expEl?.classList.toggle('open');
        });
      }

      groupEl.appendChild(row);
    });
  });
}

function buildDetail(entry) {
  const d = entry.details || {};
  const c = d.currency ? `${d.currency} ` : '';
  
  switch (entry.action) {
    case 'EXPENSE_CREATED':
      return `Added expense "${d.title}" of ${c}${d.amount}${d.group_name ? ` in ${d.group_name}` : ''}`;
    case 'EXPENSE_UPDATED':
      return `Updated expense "${d.after?.title || d.before?.title || d.title || 'Unknown'}"${d.group_name ? ` in ${d.group_name}` : ''}`;
    case 'EXPENSE_DELETED':
      return `Deleted expense "${d.title}"${d.group_name ? ` from ${d.group_name}` : ''}`;
    case 'SETTLEMENT_CREATED':
      return `Recorded a payment of ${c}${d.amount}${d.receiver_username ? ` to ${d.receiver_username}` : ''}`;
    case 'SETTLEMENT_CONFIRMED':
      return `Confirmed a payment of ${c}${d.amount}${d.payer_username ? ` from ${d.payer_username}` : ''}`;
    case 'SETTLEMENT_CANCELLED':
      return `Cancelled a payment of ${c}${d.amount}`;
    case 'GROUP_CREATED':
      return `Created group "${d.group_name || d.name || 'Unknown'}"`;
    case 'GROUP_DELETED':
      return `Deleted group "${d.group_name || d.name || 'Unknown'}"`;
    case 'MEMBER_ADDED':
      return `Was added to "${d.group_name || 'the group'}" as ${d.role || 'Member'}`;
    case 'MEMBER_JOINED':
      return `Joined "${d.group_name || 'the group'}" via invite link`;
    case 'MEMBER_REMOVED':
      return `Left or was removed from "${d.group_name || 'the group'}"`;
    default:
      // Fallback if action is unknown
      if (d.title)        return `"${d.title}"${d.group_name ? ` in ${d.group_name}` : ''}`;
      if (d.amount)       return `${c}${d.amount}${d.group_name ? ` · ${d.group_name}` : ''}`;
      if (d.group_name)   return d.group_name;
      if (d.username)     return d.username;
      return '—';
  }
}

function buildExpandedView(entry) {
  const d = entry.details || {};
  if (!Object.keys(d).length) return '';

  // For EXPENSE_UPDATED, show before/after table
  if (entry.action === 'EXPENSE_UPDATED' && d.before && d.after) {
    const fields = new Set([...Object.keys(d.before), ...Object.keys(d.after)]);
    const rows   = [...fields].filter(f => d.before[f] !== d.after[f]).map(f => `
      <tr>
        <td class="fw-600">${f}</td>
        <td class="text-red" style="text-decoration:line-through">${String(d.before[f] ?? '—')}</td>
        <td class="text-green">${String(d.after[f] ?? '—')}</td>
      </tr>`).join('');
    if (!rows) return '<span class="text-muted text-sm">No field changes detected.</span>';
    return `<table class="diff-table"><thead><tr><th>Field</th><th>Before</th><th>After</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  return '';
}

// ── Load activity ─────────────────────────────────────────────────────────────
async function loadActivity(append = false) {
  const params = {
    page: _page,
    ...(document.getElementById('filter-action').value ? { action: document.getElementById('filter-action').value } : {}),
    ...(document.getElementById('filter-from').value   ? { date_after:  document.getElementById('filter-from').value } : {}),
    ...(document.getElementById('filter-to').value     ? { date_before: document.getElementById('filter-to').value } : {}),
  };

  try {
    const data    = await getActivity(params);
    const results = data.results || data;
    _hasMore = !!(data.next);
    if (!append) _entries = [];
    _entries  = [..._entries, ...results];
    renderTimeline(results, append);
  } catch (err) { handleApiError(err, showToast); }
}

// ── Filters ───────────────────────────────────────────────────────────────────
['filter-action','filter-from','filter-to'].forEach(id => {
  document.getElementById(id)?.addEventListener('change', () => {
    _page = 1; document.getElementById('activity-timeline').innerHTML = '';
    loadActivity();
  });
});
document.getElementById('btn-clear-filters')?.addEventListener('click', () => {
  ['filter-action','filter-from','filter-to'].forEach(id => {
    const el = document.getElementById(id); if (el) el.value = '';
  });
  _page = 1; document.getElementById('activity-timeline').innerHTML = '';
  loadActivity();
});

document.getElementById('btn-load-more')?.addEventListener('click', () => { _page++; loadActivity(true); });

// ── Init ──────────────────────────────────────────────────────────────────────
loadActivity();
