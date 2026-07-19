/**
 * modal.js — Generic modal open/close/backdrop.
 * Every modal in the app is pre-rendered in HTML, hidden by default.
 * Supports: backdrop click to close, Escape key, focus trap.
 */

let _activeModal = null;
const _prevFocus = new WeakMap();

/**
 * Open a modal overlay by its element ID.
 * @param {string} id — the modal-overlay element's id
 */
export function openModal(id) {
  const overlay = document.getElementById(id);
  if (!overlay) return;

  // Close any currently open modal first
  if (_activeModal && _activeModal !== overlay) closeModal(_activeModal.id);

  _prevFocus.set(overlay, document.activeElement);
  overlay.removeAttribute('hidden');
  overlay.setAttribute('aria-modal', 'true');
  document.body.style.overflow = 'hidden';
  _activeModal = overlay;

  // Focus first focusable element inside modal
  const focusable = _getFocusable(overlay);
  if (focusable.length) focusable[0].focus();

  // Backdrop click
  overlay.addEventListener('click', _backdropHandler);
  // Escape key
  document.addEventListener('keydown', _escHandler);
  // Focus trap
  overlay.addEventListener('keydown', _trapFocus);
}

/**
 * Close a modal overlay by its element ID (or the element itself).
 * @param {string|HTMLElement} idOrEl
 */
export function closeModal(idOrEl) {
  const overlay = typeof idOrEl === 'string'
    ? document.getElementById(idOrEl)
    : idOrEl;
  if (!overlay) return;

  overlay.setAttribute('hidden', '');
  document.body.style.overflow = '';
  _activeModal = null;

  overlay.removeEventListener('click', _backdropHandler);
  document.removeEventListener('keydown', _escHandler);
  overlay.removeEventListener('keydown', _trapFocus);

  // Restore focus
  const prev = _prevFocus.get(overlay);
  if (prev && prev.focus) prev.focus();
}

// ── Private helpers ───────────────────────────────────────────────────────────

function _backdropHandler(e) {
  // Close only if click is directly on the overlay (backdrop), not inner modal
  if (e.target === e.currentTarget) closeModal(e.currentTarget);
}

function _escHandler(e) {
  if (e.key === 'Escape' && _activeModal) closeModal(_activeModal);
}

function _trapFocus(e) {
  if (e.key !== 'Tab') return;
  const focusable = _getFocusable(e.currentTarget);
  if (!focusable.length) { e.preventDefault(); return; }
  const first = focusable[0];
  const last  = focusable[focusable.length - 1];
  if (e.shiftKey) {
    if (document.activeElement === first) { e.preventDefault(); last.focus(); }
  } else {
    if (document.activeElement === last)  { e.preventDefault(); first.focus(); }
  }
}

function _getFocusable(container) {
  return Array.from(container.querySelectorAll(
    'button:not([disabled]),a[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])'
  )).filter(el => !el.closest('[hidden]') && el.offsetParent !== null);
}

/** Convenience: attach close behaviour to all .modal-close buttons inside an overlay. */
export function attachModalClose(overlayId) {
  const overlay = document.getElementById(overlayId);
  if (!overlay) return;
  overlay.querySelectorAll('.modal-close').forEach(btn => {
    btn.addEventListener('click', () => closeModal(overlayId));
  });
}
