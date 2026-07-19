/**
 * auth.js — Owns all token logic.
 *
 * Backend contract:
 *   - Login returns { access } in response body; refresh token is in HttpOnly cookie.
 *   - Refresh endpoint reads cookie automatically — no JS access to refresh token.
 *   - Access token stored in sessionStorage (cleared on tab close).
 */

const ACCESS_KEY = 'resolv_access';

// ── Token primitives ──────────────────────────────────────────────────────────

/** Read access token from sessionStorage. */
export function getAccessToken() {
  return sessionStorage.getItem(ACCESS_KEY);
}

/**
 * Store the access token. Refresh token is in HttpOnly cookie — browser manages it.
 * @param {string} access
 */
export function setTokens(access) {
  sessionStorage.setItem(ACCESS_KEY, access);
}

/** Clear access token. Called on logout. */
export function clearTokens() {
  sessionStorage.removeItem(ACCESS_KEY);
}

// ── Refresh ───────────────────────────────────────────────────────────────────

/**
 * Attempt a silent token refresh using the HttpOnly cookie the browser holds.
 * Returns new access token string on success, throws on failure.
 */
export async function refreshAccessToken() {
  const BASE_URL = _getBaseUrl();
  const res = await fetch(`${BASE_URL}/api/v1/auth/refresh/`, {
    method: 'POST',
    credentials: 'include',          // sends HttpOnly refresh cookie
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error('REFRESH_FAILED');
  const data = await res.json();
  setTokens(data.access);
  return data.access;
}

// ── Auth guard ────────────────────────────────────────────────────────────────

/**
 * Call this at the top of every protected page script.
 * - If no access token → redirect to login.html.
 * - If token present → call GET /api/v1/users/me/ to verify + get user object.
 * - On 401 → attempt refresh → retry.
 * - On second failure → redirect to login.html.
 * Returns the user object on success.
 */
export async function requireAuth() {
  const token = getAccessToken();
  if (!token) {
    _redirectToLogin();
    return null;
  }
  try {
    const user = await _fetchMe(token);
    return user;
  } catch (err) {
    if (err.status === 401) {
      // Try refresh
      try {
        const newToken = await refreshAccessToken();
        const user = await _fetchMe(newToken);
        return user;
      } catch {
        clearTokens();
        _redirectToLogin();
        return null;
      }
    }
    // Any other error — network down etc — still redirect
    clearTokens();
    _redirectToLogin();
    return null;
  }
}

// ── Logout ────────────────────────────────────────────────────────────────────

/**
 * Log the user out.
 * Attempts to call the backend logout endpoint (best-effort; refresh token is
 * in an HttpOnly cookie the backend may or may not blacklist via the cookie).
 * Always clears local access token and redirects.
 */
export async function logout() {
  try {
    const BASE_URL = _getBaseUrl();
    const token = getAccessToken();
    await fetch(`${BASE_URL}/api/v1/auth/logout/`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
    });
  } catch {
    // Ignore errors — always clear local state
  }
  clearTokens();
  window.location.href = '/login.html';
}

// ── Private helpers ───────────────────────────────────────────────────────────

async function _fetchMe(token) {
  const BASE_URL = _getBaseUrl();
  const res = await fetch(`${BASE_URL}/api/v1/users/me/`, {
    headers: { 'Authorization': `Bearer ${token}` },
    credentials: 'include',
  });
  if (!res.ok) {
    const err = new Error('AUTH_FAILED');
    err.status = res.status;
    throw err;
  }
  return res.json();
}

function _redirectToLogin() {
  if (!window.location.pathname.endsWith('login.html')) {
    window.location.href = '/login.html';
  }
}

function _getBaseUrl() {
  return window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : 'https://resolv-api.onrender.com';
}