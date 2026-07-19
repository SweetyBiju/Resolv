/**
 * bottom-nav.js — Renders mobile bottom navigation into #bottom-nav.
 * Visible below 768px. Active item gets yellow underline.
 */

const MOBILE_NAV_ITEMS = [
  { href: '/dashboard.html',   icon: '⊞', label: 'Home'       },
  { href: '/groups.html',      icon: '◉', label: 'Groups'     },
  { href: '/expenses.html',    icon: '₹', label: 'Expenses'   },
  { href: '/settlements.html', icon: '⇄', label: 'Settle'     },
  { href: '/analytics.html',   icon: '▦', label: 'Analytics'  },
  { href: '/profile.html',     icon: '👤', label: 'Profile'   },
];

/** Render the bottom nav. Call at page load on every protected page. */
export function renderBottomNav() {
  const nav = document.getElementById('bottom-nav');
  if (!nav) return;

  const path = window.location.pathname;

  const items = MOBILE_NAV_ITEMS.map(item => {
    const active = path.endsWith(item.href.replace('/', '')) ? 'active' : '';
    return `
      <a href="${item.href}" class="bottom-nav-item ${active}" aria-label="${item.label}">
        <span class="nav-icon">${item.icon}</span>
        <span>${item.label}</span>
      </a>`;
  }).join('');

  nav.innerHTML = `<div class="bottom-nav-inner">${items}</div>`;
}
