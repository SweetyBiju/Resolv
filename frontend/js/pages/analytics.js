/**
 * analytics.js — Spending trends, category breakdown, budget vs actual, insights.
 * Uses Chart.js (loaded via script tag from js/vendor/chart.min.js).
 */
import { requireAuth } from '../core/auth.js';
import { getGroups, getTrends, getCategoryBreakdown, getBudgetVsActual, getInsights, exportCSV, getBudgets, createBudget, updateBudget } from '../core/api.js';
import { renderSidebar } from '../components/sidebar.js';
import { renderBottomNav } from '../components/bottom-nav.js';
import { showToast } from '../components/toast.js';
import { getInitials, formatCurrency, capitalize, handleApiError } from '../core/utils.js';

const user = await requireAuth();
if (!user) throw new Error('Not authenticated');

renderSidebar(user);
renderBottomNav();
document.getElementById('topbar-avatar').textContent   = getInitials(user.username);
document.getElementById('topbar-username').textContent = user.username;

let _trendsChart   = null;
let _categoryChart = null;
let _selectedGroup = '';
const currency = user.currency_preference || 'INR';

// ── Category colours ──────────────────────────────────────────────────────────
const CAT_COLORS = {
  FOOD: '#FFD60A', TRAVEL: '#2563EB', HOUSING: '#A855F7',
  ENTERTAINMENT: '#22C55E', UTILITIES: '#F97316', OTHER: '#9CA3AF',
};

// ── Load groups ───────────────────────────────────────────────────────────────
async function loadGroups() {
  try {
    const data = await getGroups();
    const groups = data.results || data;
    const sel = document.getElementById('analytics-group-select');
    sel.innerHTML = `<option value="">All Groups</option>` +
      groups.map(g => `<option value="${g.id}">${g.name}</option>`).join('');
  } catch { /* silent */ }
}

// ── Trends ────────────────────────────────────────────────────────────────────
// ── Trends ────────────────────────────────────────────────────────────────────
async function loadTrends() {
  const canvas = document.getElementById('chart-trends');
  const emptyEl = document.getElementById('chart-trends-empty');
  const errorEl = document.getElementById('chart-trends-error');
  try {
    const params = _selectedGroup ? { group_id: _selectedGroup } : {};
    const data   = await getTrends(params);
    const labels = data.map(d => d.month || d.label || '');
    const values = data.map(d => parseFloat(d.total || d.amount || 0));

    if (_trendsChart) _trendsChart.destroy();

    if (typeof Chart === 'undefined') {
      canvas.classList.add('hidden');
      emptyEl.classList.add('hidden');
      errorEl.classList.remove('hidden');
      return;
    }

    errorEl.classList.add('hidden');

    if (values.length === 0 || values.reduce((a, b) => a + b, 0) === 0) {
      canvas.classList.add('hidden');
      emptyEl.classList.remove('hidden');
      return;
    }

    canvas.classList.remove('hidden');
    emptyEl.classList.add('hidden');

    const ctx = canvas.getContext('2d');
    _trendsChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Total Spend',
          data: values,
          borderColor: '#0A0A0A',
          backgroundColor: 'rgba(255,214,10,0.15)',
          borderWidth: 2,
          pointBackgroundColor: '#FFD60A',
          pointBorderColor: '#0A0A0A',
          pointRadius: 5,
          tension: 0.3,
          fill: true,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { grid: { color: '#F0F2F8' }, ticks: { font: { family: 'Space Grotesk' } } },
          x: { grid: { display: false }, ticks: { font: { family: 'Space Grotesk' } } },
        }
      }
    });
  } catch (err) { handleApiError(err, showToast); }
}

// ── Category breakdown ────────────────────────────────────────────────────────
async function loadCategories() {
  const canvas = document.getElementById('chart-categories');
  const emptyEl = document.getElementById('chart-categories-empty');
  const legendEl = document.getElementById('category-legend');
  try {
    const params = _selectedGroup ? { group_id: _selectedGroup } : {};
    const data   = await getCategoryBreakdown(params);
    const labels = data.map(d => capitalize(d.category));
    const values = data.map(d => parseFloat(d.total || d.amount || 0));
    const colors = data.map(d => CAT_COLORS[d.category] || '#E5E7EB');

    if (_categoryChart) _categoryChart.destroy();

    if (typeof Chart === 'undefined') {
      canvas.classList.add('hidden');
      emptyEl.classList.add('hidden');
      legendEl.innerHTML = '';
      return;
    }

    if (values.length === 0 || values.reduce((a, b) => a + b, 0) === 0) {
      canvas.classList.add('hidden');
      emptyEl.classList.remove('hidden');
      legendEl.innerHTML = '';
      return;
    }

    canvas.classList.remove('hidden');
    emptyEl.classList.add('hidden');

    const ctx = canvas.getContext('2d');
    _categoryChart = new Chart(ctx, {
      type: 'doughnut',
      data: { labels, datasets: [{ data: values, backgroundColor: colors, borderColor: '#0A0A0A', borderWidth: 2 }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        cutout: '60%',
      }
    });

    // Legend
    const total    = values.reduce((a, b) => a + b, 0);
    legendEl.innerHTML = data.map((d, i) => {
      const pct = total > 0 ? ((values[i] / total) * 100).toFixed(1) : 0;
      return `<div style="display:flex;align-items:center;gap:4px;font-size:11px;font-weight:600">
        <span style="width:10px;height:10px;border-radius:50%;background:${colors[i]};border:1px solid #0A0A0A;flex-shrink:0"></span>
        ${labels[i]} (${pct}%)
      </div>`;
    }).join('');
  } catch (err) { handleApiError(err, showToast); }
}

// ── Budget vs Actual ──────────────────────────────────────────────────────────
async function loadBudget() {
  const listEl  = document.getElementById('budget-list');
  const emptyEl = document.getElementById('budget-empty');
  try {
    const params = _selectedGroup ? { group_id: _selectedGroup } : {};
    const data   = await getBudgetVsActual(params);
    if (!data.length) { emptyEl.classList.remove('hidden'); listEl.innerHTML = ''; return; }
    emptyEl.classList.add('hidden');

    listEl.innerHTML = data.map(d => {
      const budget = parseFloat(d.budget_limit || 0);
      const actual = parseFloat(d.actual_spent || 0);
      const pct    = budget > 0 ? Math.min((actual / budget) * 100, 100) : 0;
      const over   = d.over_budget;
      const color  = over ? 'var(--red)' : CAT_COLORS[d.category] || 'var(--blue)';
      return `
        <div class="budget-row">
          <div class="budget-label">${capitalize(d.category)}</div>
          <div class="budget-bar-wrap">
            <div class="budget-bar" style="width:${pct}%;background:${color}"></div>
          </div>
          <div class="budget-amount ${over ? 'text-red' : 'text-muted'}">
            ${formatCurrency(actual, currency)} / ${budget > 0 ? formatCurrency(budget, currency) : 'No Budget'}
          </div>
          <button class="btn btn-ghost btn-sm text-blue" data-cat="${d.category}" data-budget-id="${d.budget_id || ''}" data-action="set-budget" title="Set budget">✎</button>
        </div>`;
    }).join('');

    listEl.querySelectorAll('[data-action="set-budget"]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const amt = prompt(`Set budget for ${capitalize(btn.dataset.cat)} (${currency}):`);
        if (!amt || isNaN(parseFloat(amt))) return;
        try {
          const today = new Date();
          const currentMonth = today.getMonth() + 1;
          const currentYear = today.getFullYear();
          const payload = {
            category: btn.dataset.cat,
            amount_limit: parseFloat(amt),
            month: currentMonth,
            year: currentYear,
            group: _selectedGroup ? parseInt(_selectedGroup) : null
          };
          if (btn.dataset.budgetId) await updateBudget(btn.dataset.budgetId, payload);
          else                       await createBudget(payload);
          showToast('Budget updated.', 'success');
          loadBudget();
        } catch (err) { handleApiError(err, showToast); }
      });
    });
  } catch (err) { handleApiError(err, showToast); }
}

// ── Insights ──────────────────────────────────────────────────────────────────
async function loadInsights() {
  const el = document.getElementById('insights-list');
  try {
    const data = await getInsights();
    if (!data.length) { el.innerHTML = '<div class="text-muted text-sm">No insights yet.</div>'; return; }
    el.innerHTML = data.slice(0, 4).map(ins => `
      <div class="insight-card">
        <div class="insight-icon">${ins.icon || '💡'}</div>
        <div>
          <div class="insight-headline">${ins.headline || ins.title || '—'}</div>
          <div class="text-sm text-muted">${ins.description || ins.detail || ''}</div>
        </div>
      </div>`).join('');
  } catch { el.innerHTML = '<div class="text-muted text-sm">Could not load insights.</div>'; }
}

// ── Export CSV ────────────────────────────────────────────────────────────────
document.getElementById('btn-export-csv')?.addEventListener('click', async () => {
  const btn = document.getElementById('btn-export-csv');
  btn.disabled = true; btn.textContent = 'Exporting…';
  try {
    const params = _selectedGroup ? { group_id: _selectedGroup } : {};
    const blob   = await exportCSV(params);
    const url    = URL.createObjectURL(blob);
    const a      = document.createElement('a');
    a.href = url; a.download = 'resolv_export.csv'; a.click();
    URL.revokeObjectURL(url);
    showToast('CSV exported!', 'success');
  } catch (err) { handleApiError(err, showToast); }
  finally { btn.disabled = false; btn.textContent = 'Export CSV'; }
});

// ── Group selector ────────────────────────────────────────────────────────────
document.getElementById('analytics-group-select')?.addEventListener('change', (e) => {
  _selectedGroup = e.target.value;
  loadTrends(); loadCategories(); loadBudget();
});

// ── Init ──────────────────────────────────────────────────────────────────────
await loadGroups();
loadTrends();
loadCategories();
loadBudget();
loadInsights();
