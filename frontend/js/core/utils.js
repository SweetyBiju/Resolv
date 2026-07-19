/**
 * utils.js — Pure functions, zero side effects.
 * No DOM access. No imports. Importable anywhere.
 */

// ── Currency ──────────────────────────────────────────────────────────────────

/**
 * Format a numeric amount using Intl.NumberFormat.
 * @param {number|string} amount
 * @param {string} currency — ISO 4217 code, e.g. 'INR'
 * @returns {string} e.g. '₹1,234.56'
 */
export function formatCurrency(amount, currency = 'INR') {
  const num = parseFloat(amount);
  if (isNaN(num)) return '—';
  try {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num);
  } catch {
    // Fallback for unsupported currency codes
    return `${currency} ${num.toFixed(2)}`;
  }
}

// ── Dates ─────────────────────────────────────────────────────────────────────

/**
 * Format an ISO date string to a human-readable date.
 * @param {string} isoString
 * @returns {string} e.g. '15 May 2026'
 */
export function formatDate(isoString) {
  if (!isoString) return '—';
  const d = new Date(isoString);
  if (isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
}

/**
 * Format an ISO date string as a relative label.
 * @param {string} isoString
 * @returns {string} e.g. 'Today', 'Yesterday', '3 days ago'
 */
export function formatRelativeDate(isoString) {
  if (!isoString) return '—';
  const d = new Date(isoString);
  if (isNaN(d.getTime())) return '—';
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const dStart     = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const diffDays   = Math.round((todayStart - dStart) / 86400000);
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7)   return `${diffDays} days ago`;
  return formatDate(isoString);
}

/**
 * Format a datetime string as a short time label (e.g. '14:32').
 */
export function formatTime(isoString) {
  if (!isoString) return '';
  const d = new Date(isoString);
  if (isNaN(d.getTime())) return '';
  return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
}

/**
 * Get today's date in YYYY-MM-DD format (for default date inputs).
 */
export function todayISO() {
  return new Date().toISOString().split('T')[0];
}

// ── String helpers ────────────────────────────────────────────────────────────

/**
 * Capitalize first letter, lowercase the rest.
 * @param {string} str
 * @returns {string} e.g. 'FOOD' → 'Food'
 */
export function capitalize(str) {
  if (!str) return '';
  const s = String(str);
  return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
}

/**
 * Get initials from a name (up to 2 letters).
 * @param {string} name — e.g. 'Rahul Sharma'
 * @returns {string} e.g. 'RS'
 */
export function getInitials(name) {
  if (!name) return '?';
  return name.trim().split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase();
}

/**
 * Truncate a string to n characters, appending '…'.
 * @param {string} str
 * @param {number} n
 */
export function truncate(str, n = 30) {
  if (!str) return '';
  return str.length > n ? str.slice(0, n) + '…' : str;
}

/**
 * Map a split_type code to a display label.
 * @param {string} type — 'EQUAL' | 'EXACT' | 'PERCENT' | 'ITEM'
 */
export function parseSplitType(type) {
  const map = { EQUAL: 'Equal Split', EXACT: 'Exact', PERCENT: 'Percent', ITEM: 'By Item' };
  return map[type] || type;
}

/**
 * Map a split_type to its badge CSS class.
 */
export function splitTypeBadgeClass(type) {
  const map = { EQUAL: 'badge-blue', EXACT: 'badge-purple', PERCENT: 'badge-yellow', ITEM: 'badge-green' };
  return map[type] || '';
}

/**
 * Map a settlement status to its badge CSS class.
 */
export function settlementStatusBadge(status) {
  const map = { PENDING: 'badge-yellow', CONFIRMED: 'badge-green', CANCELLED: 'badge-grey' };
  return map[status] || '';
}

// ── Validation ────────────────────────────────────────────────────────────────

/** Returns true if the string is a valid email address. */
export function validateEmail(str) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(str);
}

/** Returns true if the string is a 3-letter alphabetic currency code. */
export function validateCurrency(str) {
  return /^[A-Za-z]{3}$/.test(str);
}

// ── Function utilities ────────────────────────────────────────────────────────

/**
 * Debounce a function.
 * @param {Function} fn
 * @param {number} delay — ms
 */
export function debounce(fn, delay = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

// ── URL helpers ───────────────────────────────────────────────────────────────

/** Get a URL query parameter value. */
export function getParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

// ── Error mapping ─────────────────────────────────────────────────────────────

/**
 * Map field errors from an API error onto DOM form fields.
 * @param {{ field_errors: Object }} err — normalised error from api.js
 * @param {Object} fieldMap — { fieldName: 'error-element-id' }
 */
export function mapFieldErrors(err, fieldMap) {
  if (!err.field_errors) return;
  for (const [field, elId] of Object.entries(fieldMap)) {
    const el = document.getElementById(elId);
    if (el && err.field_errors[field]) {
      el.textContent = err.field_errors[field];
    }
  }
}

/**
 * Clear all field error elements.
 * @param {string[]} ids — array of element IDs
 */
export function clearFieldErrors(ids) {
  ids.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = '';
  });
}

/**
 * Standard error handler for page API calls.
 * Maps HTTP status codes to appropriate toast/inline messages.
 * @param {Error} err — normalised error from api.js
 * @param {Function} showToast
 */
export function handleApiError(err, showToast) {
  if (!err.status) {
    showToast('Check your connection and try again.', 'error');
    return;
  }
  if (err.status === 400) {
    showToast(err.message || 'Please fix the errors below.', 'error');
    return;
  }
  if (err.status === 403) { showToast("You don't have permission to do that.", 'error'); return; }
  if (err.status === 404) { showToast('Not found.', 'error'); return; }
  if (err.status === 429) { showToast('Too many requests. Slow down.', 'error'); return; }
  if (err.status >= 500)  { showToast('Server error. Try again.', 'error'); return; }
  showToast(err.message || 'Something went wrong.', 'error');
}

/**
 * Format an activity log entry into a clean, human-readable sentence.
 */
export function formatActivityDetail(entry) {
  if (!entry) return '—';

  let d = entry.details || {};
  if (typeof d === 'string') {
    try { d = JSON.parse(d); } catch { d = {}; }
  }

  const groupText = d.group_name ? ` in ${d.group_name}` : '';
  const amountText = d.amount ? formatCurrency(d.amount, d.currency || 'INR') : '';

  switch (entry.action) {
    case 'EXPENSE_CREATED':
      return `Added "${d.title || 'Expense'}" (${amountText})${groupText}`;
    case 'EXPENSE_UPDATED':
      return `Updated "${d.after?.title || d.before?.title || d.title || 'Expense'}"${groupText}`;
    case 'EXPENSE_DELETED':
      return `Deleted "${d.title || 'Expense'}"${groupText}`;
    case 'SETTLEMENT_CREATED':
      return `Recorded payment of ${amountText}${d.receiver_username ? ` to ${d.receiver_username}` : ''}${groupText}`;
    case 'SETTLEMENT_CONFIRMED':
      return `Confirmed payment of ${amountText}${d.payer_username ? ` from ${d.payer_username}` : ''}${groupText}`;
    case 'SETTLEMENT_CANCELLED':
      return `Cancelled payment of ${amountText}${groupText}`;
    case 'GROUP_CREATED':
      return `Created group "${d.group_name || d.name || 'Group'}"`;
    case 'GROUP_DELETED':
      return `Deleted group "${d.group_name || d.name || 'Group'}"`;
    case 'MEMBER_ADDED':
      return `Added member${d.group_name ? ` to ${d.group_name}` : ''}`;
    case 'MEMBER_JOINED':
      return `Joined "${d.group_name || 'Group'}" via invite code`;
    case 'MEMBER_REMOVED':
      return `Removed member from "${d.group_name || 'Group'}"`;
    default:
      if (d.title && d.amount) return `"${d.title}" (${amountText})${groupText}`;
      if (d.title)             return `"${d.title}"${groupText}`;
      if (d.amount)            return `${amountText}${groupText}`;
      if (d.group_name)        return d.group_name;
      return (entry.action || 'Activity').replace(/_/g, ' ');
  }
}