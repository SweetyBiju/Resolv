/**
 * api.js — Owns all HTTP calls to the Django backend.
 *
 * Single request() function all calls go through.
 * On 401 → refreshes token once → retries → on second 401 → logout.
 * All errors normalized to { status, message, field_errors }.
 */

import { getAccessToken, refreshAccessToken, logout } from './auth.js';

// ── Base URL ──────────────────────────────────────────────────────────────────

const BASE_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? 'http://localhost:8000'
  : 'https://resolv-api.onrender.com';

// ── Core request ──────────────────────────────────────────────────────────────

/**
 * Central fetch wrapper. Attaches auth header, handles 401 refresh + retry,
 * normalises errors.
 * @param {string} path   — e.g. '/api/v1/groups/'
 * @param {object} opts   — { method, body, params, isFormData }
 * @returns {Promise<any>}
 */
async function request(path, { method = 'GET', body, params, isFormData = false } = {}) {
  let url = `${BASE_URL}${path}`;
  if (params) {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v != null))
    ).toString();
    if (qs) url += `?${qs}`;
  }

  const makeHeaders = () => {
    const token = getAccessToken();
    const h = { ...(token ? { 'Authorization': `Bearer ${token}` } : {}) };
    if (!isFormData) h['Content-Type'] = 'application/json';
    return h;
  };

  const makeInit = () => ({
    method,
    credentials: 'include',
    headers: makeHeaders(),
    ...(body != null ? { body: isFormData ? body : JSON.stringify(body) } : {}),
  });

  let res = await fetch(url, makeInit());

  // Silent refresh on first 401
  if (res.status === 401) {
    try {
      await refreshAccessToken();
      res = await fetch(url, makeInit());
    } catch {
      await logout();
      throw _error(401, 'Session expired. Please log in again.', {});
    }
    // Second 401 → force logout
    if (res.status === 401) {
      await logout();
      throw _error(401, 'Session expired. Please log in again.', {});
    }
  }

  // 204 No Content
  if (res.status === 204) return null;

  // Successful response
  if (res.ok) {
    // Check content-type for CSV / blob responses
    const ct = res.headers.get('Content-Type') || '';
    if (ct.includes('text/csv') || ct.includes('application/octet-stream')) {
      return res.blob();
    }
    return res.json();
  }

  // Error response
  let errBody = {};
  try { errBody = await res.json(); } catch { /* no JSON body */ }

  // Handle the custom exception handler wrapper: { error: 400, detail: { field: ["msg"] } }
  const detail = errBody.detail;
  let message;
  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    // detail is a nested object of field errors — extract the first readable message
    message = _firstFieldError(detail) || `Request failed (${res.status})`;
  } else {
    message = (typeof detail === 'string' ? detail : null)
      || errBody.message || errBody.error
      || _firstFieldError(errBody) || `Request failed (${res.status})`;
  }
  const field_errors = _extractFieldErrors(
    (detail && typeof detail === 'object' && !Array.isArray(detail)) ? detail : errBody
  );

  throw _error(res.status, message, field_errors);
}

function _error(status, message, field_errors) {
  const err = new Error(message);
  err.status = status;
  err.message = message;
  err.field_errors = field_errors || {};
  return err;
}

function _firstFieldError(body) {
  for (const key of Object.keys(body)) {
    const val = body[key];
    if (Array.isArray(val) && val.length) return val[0];
    if (typeof val === 'string') return val;
  }
  return null;
}

function _extractFieldErrors(body) {
  const fields = {};
  for (const [k, v] of Object.entries(body)) {
    if (!['detail', 'message', 'error'].includes(k)) {
      fields[k] = Array.isArray(v) ? v[0] : String(v);
    }
  }
  return fields;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export const login = (email, password) =>
  request('/api/v1/auth/login/', { method: 'POST', body: { email, password } });

export const register = (data) =>
  request('/api/v1/users/register/', { method: 'POST', body: data });

export const logoutUser = () =>
  request('/api/v1/auth/logout/', { method: 'POST' });

export const logoutAll = () =>
  request('/api/v1/auth/logout-all/', { method: 'POST' });

// ── Users ─────────────────────────────────────────────────────────────────────

export const getMe = () =>
  request('/api/v1/users/me/');

export const updateMe = (data) =>
  request('/api/v1/users/me/', { method: 'PATCH', body: data });

export const changePassword = (data) =>
  request('/api/v1/users/change-password/', { method: 'POST', body: data });

export const getUserProfile = (id) =>
  request(`/api/v1/users/profile/${id}/`);

// ── Groups ────────────────────────────────────────────────────────────────────

export const getGroups = () =>
  request('/api/v1/groups/');

export const createGroup = (data) =>
  request('/api/v1/groups/', { method: 'POST', body: data });

export const getGroup = (id) =>
  request(`/api/v1/groups/${id}/`);

export const updateGroup = (id, data) =>
  request(`/api/v1/groups/${id}/`, { method: 'PATCH', body: data });

export const deleteGroup = (id) =>
  request(`/api/v1/groups/${id}/`, { method: 'DELETE' });

export const addMember = (groupId, identifier) =>
  request(`/api/v1/groups/${groupId}/add-member/`, { method: 'POST', body: { identifier, user_id: identifier } });

export const removeMember = (groupId, userId) =>
  request(`/api/v1/groups/${groupId}/remove-member/`, { method: 'POST', body: { user_id: userId } });

export const transferAdmin = (groupId, userId) =>
  request(`/api/v1/groups/${groupId}/transfer-admin/`, { method: 'POST', body: { user_id: userId } });

export const getInviteCode = (groupId) =>
  request(`/api/v1/groups/${groupId}/invite-code/`);

export const joinGroup = (inviteCode) =>
  request('/api/v1/groups/join/', { method: 'POST', body: { invite_code: inviteCode } });

export const regenerateInviteCode = (groupId) =>
  request(`/api/v1/groups/${groupId}/regenerate-invite/`, { method: 'POST' });

// ── Expenses ──────────────────────────────────────────────────────────────────

export const getExpenses = (params) =>
  request('/api/v1/expenses/', { params });

export const createExpense = (data) =>
  request('/api/v1/expenses/', { method: 'POST', body: data });

export const updateExpense = (id, data) =>
  request(`/api/v1/expenses/${id}/`, { method: 'PATCH', body: data });

export const deleteExpense = (id) =>
  request(`/api/v1/expenses/${id}/`, { method: 'DELETE' });

export const canDeleteExpense = (id) =>
  request(`/api/v1/expenses/${id}/can-delete/`);

export const getGroupBalances = (groupId) =>
  request(`/api/v1/expenses/balances/${groupId}/`);

export const getSuggestedSettlements = (groupId) =>
  request(`/api/v1/expenses/suggested-settlements/${groupId}/`);

// ── Settlements ───────────────────────────────────────────────────────────────

export const getSettlements = (params) =>
  request('/api/v1/settlements/', { params });

export const createSettlement = (data) =>
  request('/api/v1/settlements/', { method: 'POST', body: data });

export const confirmSettlement = (id) =>
  request(`/api/v1/settlements/${id}/confirm_settlement/`, { method: 'POST' });

export const cancelSettlement = (id) =>
  request(`/api/v1/settlements/${id}/`, { method: 'DELETE' });

// ── Activity ──────────────────────────────────────────────────────────────────

export const getActivity = (params) =>
  request('/api/v1/activity/', { params });

export const getActivityEntry = (id) =>
  request(`/api/v1/activity/${id}/`);

// ── Analytics ─────────────────────────────────────────────────────────────────

export const getTrends = (params) =>
  request('/api/v1/analytics/trends/', { params });

export const getCategoryBreakdown = (params) =>
  request('/api/v1/analytics/categories/', { params });

export const getBudgetVsActual = (params) =>
  request('/api/v1/analytics/budget/', { params });

export const getInsights = () =>
  request('/api/v1/analytics/insights/');

export const exportCSV = (params) =>
  request('/api/v1/analytics/export/', { params });

// ── Budgets ───────────────────────────────────────────────────────────────────

export const getBudgets = () =>
  request('/api/v1/budgets/');

export const createBudget = (data) =>
  request('/api/v1/budgets/', { method: 'POST', body: data });

export const updateBudget = (id, data) =>
  request(`/api/v1/budgets/${id}/`, { method: 'PATCH', body: data });