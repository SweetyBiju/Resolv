/**
 * sidebar.js — Renders the sidebar into #sidebar on every protected page.
 * Sets active state by matching window.location.pathname.
 */
import { logout } from '../core/auth.js';
import { getInitials } from '../core/utils.js';

const NAV_ITEMS = [
  { href: '/dashboard.html', icon: '⊞', label: 'Dashboard' },
  { href: '/groups.html',    icon: '◉', label: 'Groups'    },
  { href: '/expenses.html',  icon: '₹', label: 'Expenses'  },
  { href: '/settlements.html', icon: '⇄', label: 'Settlements' },
  { href: '/analytics.html', icon: '▦', label: 'Analytics' },
  { href: '/activity.html',  icon: '◎', label: 'Activity'  },
];

/**
 * Render the sidebar.
 * @param {Object} user — from requireAuth(); used for avatar/username
 */
export function renderSidebar(user = {}) {
  const sidebar = document.getElementById('sidebar');
  if (!sidebar) return;

  const path = window.location.pathname;

  const navLinks = NAV_ITEMS.map(item => {
    const active = path.endsWith(item.href.replace('/', '')) ? 'active' : '';
    return `
      <a href="${item.href}" class="${active}" id="nav-${item.label.toLowerCase()}">
        <span class="nav-icon">${item.icon}</span>
        ${item.label}
      </a>`;
  }).join('');

  const initials = user.username ? getInitials(user.username) : '?';

  sidebar.innerHTML = `
    <div class="sidebar-logo">RESOLV<span>.</span></div>
    <nav class="sidebar-nav" aria-label="Main navigation">
      ${navLinks}
      <hr class="sidebar-sep">
      <a href="/profile.html" class="${path.endsWith('profile.html') ? 'active' : ''}" id="nav-profile">
        <span class="nav-icon">👤</span>
        Profile
      </a>
      <button id="sidebar-logout-btn" aria-label="Log out">
        <span class="nav-icon">⎋</span>
        Logout
      </button>
    </nav>
    <div style="padding:var(--space-4);border-top:var(--border);font-size:var(--text-xs);color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.06em;">
      ${user.username ? `${initials} · ${user.username}` : ''}
    </div>`;

  document.getElementById('sidebar-logout-btn')?.addEventListener('click', logout);
}
