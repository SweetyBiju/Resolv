/**
 * loader.js — Page-level and inline skeleton loaders.
 * showSkeleton() injects animated placeholder cards.
 * hideSkeleton() removes them.
 */

/**
 * Inject skeleton placeholder cards into a container while data loads.
 * @param {string} containerId — ID of the container element
 * @param {number} count       — number of skeleton cards to insert
 * @param {'card'|'row'|'line'} variant — shape of skeleton
 */
export function showSkeleton(containerId, count = 3, variant = 'card') {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = '';

  for (let i = 0; i < count; i++) {
    const el = document.createElement('div');
    el.className = 'skeleton-placeholder';

    if (variant === 'card') {
      el.innerHTML = `
        <div class="skeleton-card">
          <div class="skeleton skeleton-line-lg" style="width:55%"></div>
          <div class="skeleton skeleton-line" style="width:80%"></div>
          <div class="skeleton skeleton-line-sm"></div>
        </div>`;
    } else if (variant === 'row') {
      el.style.cssText = 'display:flex;align-items:center;gap:12px;padding:12px 0;border-bottom:2px solid #E5E7EB;';
      el.innerHTML = `
        <div class="skeleton" style="width:36px;height:36px;border-radius:50%;flex-shrink:0"></div>
        <div style="flex:1;display:flex;flex-direction:column;gap:6px">
          <div class="skeleton skeleton-line" style="width:50%"></div>
          <div class="skeleton skeleton-line-sm" style="width:30%"></div>
        </div>
        <div class="skeleton skeleton-line" style="width:80px"></div>`;
    } else {
      el.innerHTML = `<div class="skeleton skeleton-line" style="margin:6px 0"></div>`;
    }

    container.appendChild(el);
  }
}

/**
 * Remove all skeleton placeholders from a container.
 * @param {string} containerId
 */
export function hideSkeleton(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.querySelectorAll('.skeleton-placeholder').forEach(el => el.remove());
}

/**
 * Show a full-page loading overlay.
 */
export function showPageLoader() {
  let loader = document.getElementById('page-loader');
  if (!loader) {
    loader = document.createElement('div');
    loader.id = 'page-loader';
    loader.style.cssText = `
      position:fixed;inset:0;background:rgba(240,242,248,0.85);
      display:flex;align-items:center;justify-content:center;z-index:9999;`;
    loader.innerHTML = '<div class="spinner-lg"></div>';
    document.body.appendChild(loader);
  }
  loader.removeAttribute('hidden');
}

/**
 * Hide the full-page loading overlay.
 */
export function hidePageLoader() {
  const loader = document.getElementById('page-loader');
  if (loader) loader.setAttribute('hidden', '');
}
