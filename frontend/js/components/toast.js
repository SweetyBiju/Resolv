/**
 * toast.js — Lightweight toast notification system.
 * Stacks bottom-right, auto-dismisses in 3s, has manual close button.
 * Neo-brutal style: white card, black border, colored left-border.
 */

let _container = null;

function _getContainer() {
  if (!_container) {
    _container = document.getElementById('toast-container');
    if (!_container) {
      _container = document.createElement('div');
      _container.id = 'toast-container';
      document.body.appendChild(_container);
    }
  }
  return _container;
}

/**
 * Show a toast notification.
 * @param {string} message
 * @param {'success'|'error'|'info'} type
 * @param {number} duration — ms before auto-dismiss (default 3000)
 */
export function showToast(message, type = 'info', duration = 3000) {
  const container = _getContainer();

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.setAttribute('role', 'alert');
  toast.innerHTML = `
    <span class="toast-message">${message}</span>
    <button class="toast-close" aria-label="Close notification">✕</button>`;

  container.appendChild(toast);

  const dismiss = () => {
    toast.style.transition = 'opacity 0.2s, transform 0.2s';
    toast.style.opacity    = '0';
    toast.style.transform  = 'translateX(110%)';
    setTimeout(() => toast.remove(), 220);
  };

  toast.querySelector('.toast-close').addEventListener('click', dismiss);

  if (duration > 0) setTimeout(dismiss, duration);

  return dismiss; // allow caller to manually dismiss
}
