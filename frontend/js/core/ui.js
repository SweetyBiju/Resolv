/**
 * ui.js - Neo-Brutalist UI Engine
 * Manages Modals, Skeleton Loaders, Confetti, and Theme Toggling.
 */

class UIManager {
    constructor() {
        this.modalContainer = null;
        this.init();
    }

    init() {
        // Create a hidden container for dynamic modals if it doesn't exist
        if (!document.getElementById('modal-root')) {
            const root = document.createElement('div');
            root.id = 'modal-root';
            root.className = 'fixed inset-0 z-50 hidden flex items-center justify-center bg-black bg-opacity-50 p-4';
            document.body.appendChild(root);
            this.modalContainer = root;
        }

        // Global listener for closing modals on background click
        this.modalContainer.addEventListener('click', (e) => {
            if (e.target === this.modalContainer) this.hideModal();
        });

        // Initialize Lucide icons for static elements
        this.refreshIcons();
    }

    /**
     * Re-runs Lucide icon replacement for dynamically injected HTML
     */
    refreshIcons() {
        if (window.lucide) {
            window.lucide.createIcons();
        }
    }

    /**
     * Triggers a Neo-Brutalist Confetti burst
     */
    fireConfetti() {
        if (typeof confetti === 'function') {
            confetti({
                particleCount: 150,
                spread: 70,
                origin: { y: 0.6 },
                ticks: 500,
                gravity:0.9,
                colors: ['#fde047', '#a3e635', '#f472b6', '#c084fc', '#60a5fa'], // Match palette
                disableForReducedMotion: true
            });
        }
    }

    /**
     * Injects a Neo-Brutalist modal into the DOM
     * @param {string} title - Header text
     * @param {string} body - HTML content string
     * @param {Array} actions - Array of button configs {label, class, onClick}
     */
    showModal(title, body, actions = []) {
        this.modalContainer.innerHTML = `
            <div class="bg-white border-4 border-black shadow-comic w-full max-w-md transform transition-all">
                <div class="bg-yellow-300 border-b-4 border-black p-4 flex justify-between items-center">
                    <h2 class="font-black text-xl uppercase tracking-tighter">${title}</h2>
                    <button id="modal-close-btn" class="font-black hover:text-red-600">
                        <i data-lucide="x" stroke-width="4"></i>
                    </button>
                </div>
                <div class="p-6">
                    <div class="mb-6 font-medium">${body}</div>
                    <div id="modal-actions-container" class="flex flex-wrap gap-4 justify-end">
                    </div>
                </div>
            </div>
        `;

        const actionsContainer = document.getElementById('modal-actions-container');
        
        actions.forEach(btn => {
            const button = document.createElement('button');
            button.className = `px-6 py-2 font-black uppercase tracking-widest border-4 border-black shadow-comic active:translate-x-1 active:translate-y-1 active:shadow-none transition-all ${btn.class}`;
            button.textContent = btn.label;
            
            // This natively preserves the module scope so `utils` and `api` are accessible
            button.addEventListener('click', async () => {
                await btn.onClick();
            });
            
            actionsContainer.appendChild(button);
        });

        document.getElementById('modal-close-btn').addEventListener('click', () => this.hideModal());

        this.modalContainer.classList.remove('hidden');
        this.refreshIcons();
    }

    hideModal() {
        this.modalContainer.classList.add('hidden');
        this.modalContainer.innerHTML = '';
    }

    /**
     * Shows a skeleton loader within a container
     * @param {string} selector - CSS Selector for the container
     * @param {number} count - Number of skeleton blocks
     */
    showSkeleton(selector, count = 3) {
        const container = document.querySelector(selector);
        if (!container) return;

        let skeletons = '';
        for (let i = 0; i < count; i++) {
            skeletons += `
                <div class="animate-pulse bg-slate-200 border-4 border-black h-24 w-full mb-4 shadow-comic"></div>
            `;
        }
        container.innerHTML = skeletons;
    }

    /**
     * Toggle Light/Dark mode via Tailwind class strategy
     */
    toggleTheme() {
        const html = document.documentElement;
        if (html.classList.contains('dark')) {
            html.classList.remove('dark');
            localStorage.setItem('resolv_theme', 'light');
        } else {
            html.classList.add('dark');
            localStorage.setItem('resolv_theme', 'dark');
        }
    }
}

export const ui = new UIManager();