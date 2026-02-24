// UI components and interactions

class UI {
    constructor() {
        this.modals = {};
    }

    // Initialize theme toggle
    initTheme() {
        const themeToggle = document.getElementById('themeToggle');
        if (!themeToggle) return;

        const html = document.documentElement;
        const savedTheme = localStorage.getItem('theme');
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

        if (savedTheme === 'dark' || (!savedTheme && systemPrefersDark)) {
            html.classList.add('dark');
        }

        themeToggle.addEventListener('click', () => {
            html.classList.toggle('dark');
            localStorage.setItem('theme', html.classList.contains('dark') ? 'dark' : 'light');
            utils.hapticFeedback([10]);
            if (window.lucide) {
                lucide.createIcons();
            }
        });
    }

    // Show modal
    showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('hidden');
            this.modals[modalId] = true;
        }
    }

    // Hide modal
    hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('hidden');
            this.modals[modalId] = false;
        }
    }

    // Toggle modal
    toggleModal(modalId) {
        if (this.modals[modalId]) {
            this.hideModal(modalId);
        } else {
            this.showModal(modalId);
        }
    }

    // Render group card
    renderGroupCard(group) {
        const memberText = group.member_count === 1 ? 'member' : 'members';

        return `
            <div class="glass-card rounded-xl p-6 hover:shadow-lg transition-all duration-200 cursor-pointer card-hover fade-in" data-group-id="${group.id}">
                <div class="flex items-start justify-between mb-4">
                    <div class="flex items-center space-x-3">
                        <div class="w-12 h-12 bg-gradient-to-br ${utils.generateAvatarColor(group.name)} rounded-lg flex items-center justify-center">
                            <i data-lucide="users" class="w-6 h-6 text-white"></i>
                        </div>
                        <div>
                            <h3 class="font-semibold text-gray-900 dark:text-white">${group.name}</h3>
                            <p class="text-sm text-gray-500 dark:text-gray-400">${group.member_count} ${memberText}</p>
                        </div>
                    </div>
                    <button class="copy-code-btn p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors" data-code="${group.invite_code}" title="Copy invite code">
                        <i data-lucide="copy" class="w-4 h-4 text-gray-600 dark:text-gray-400"></i>
                    </button>
                </div>

                ${group.description ? `<p class="text-sm text-gray-600 dark:text-gray-400 mb-4">${group.description}</p>` : ''}

                <div class="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
                    <div>
                        <p class="text-xs text-gray-500 dark:text-gray-400">Total Expenses</p>
                        <p class="text-lg font-semibold text-gray-900 dark:text-white">${utils.formatCurrency(group.total_expenses || 0)}</p>
                    </div>
                    <div class="text-right">
                        <p class="text-xs text-gray-500 dark:text-gray-400">Invite Code</p>
                        <p class="text-sm font-mono font-semibold text-blue-600 dark:text-blue-400">${group.invite_code}</p>
                    </div>
                </div>
            </div>
        `;
    }

    // Render settlement card
    renderSettlementCard(settlement) {
        const isOutgoing = settlement.from_user.username === auth.currentUser?.username;
        const otherUser = isOutgoing ? settlement.to_user : settlement.from_user;

        return `
            <div class="glass-card rounded-xl p-6 hover:shadow-lg transition-all duration-200 fade-in" data-settlement-id="${settlement.id}">
                <div class="flex items-center justify-between">
                    <div class="flex items-center space-x-4">
                        <div class="w-12 h-12 bg-gradient-to-br ${utils.generateAvatarColor(otherUser.name)} rounded-full flex items-center justify-center">
                            <span class="text-white font-semibold">${utils.getInitials(otherUser.name)}</span>
                        </div>
                        <div>
                            <div class="flex items-center space-x-2">
                                <i data-lucide="${isOutgoing ? 'arrow-up-right' : 'arrow-down-left'}" class="w-4 h-4 ${isOutgoing ? 'text-red-500' : 'text-green-500'}"></i>
                                <p class="font-semibold text-gray-900 dark:text-white">
                                    ${isOutgoing ? 'Pay' : 'Receive'} ${utils.formatCurrency(settlement.amount)}
                                </p>
                            </div>
                            <p class="text-sm text-gray-500 dark:text-gray-400">
                                ${isOutgoing ? 'to' : 'from'} ${otherUser.name}
                            </p>
                            <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">
                                ${settlement.group.name} • ${utils.formatDate(settlement.created_at)}
                            </p>
                        </div>
                    </div>

                    <div class="flex items-center space-x-3">
                        <span class="status-badge status-${settlement.status}">
                            ${settlement.status}
                        </span>
                        ${settlement.status === 'pending' && !isOutgoing ? `
                            <button class="confirm-settlement-btn bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg transition-colors font-semibold" data-settlement-id="${settlement.id}">
                                Confirm
                            </button>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    }

    // Render empty state
    renderEmptyState(message, icon = 'inbox') {
        return `
            <div class="text-center py-12">
                <div class="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                    <i data-lucide="${icon}" class="w-8 h-8 text-gray-400 dark:text-gray-600"></i>
                </div>
                <p class="text-gray-500 dark:text-gray-400">${message}</p>
            </div>
        `;
    }

    // Render skeleton loader
    renderSkeleton(count = 3) {
        let html = '';
        for (let i = 0; i < count; i++) {
            html += '<div class="shimmer glass-card rounded-xl p-6 h-48"></div>';
        }
        return html;
    }

    // Update reliability score with animation
    updateReliabilityScore(currentScore, newScore) {
        const scoreElement = document.getElementById('reliabilityScore');
        if (!scoreElement) return;

        // Add animation class
        scoreElement.classList.add('score-increase');

        // Animate the number
        utils.animateNumber(scoreElement, currentScore, newScore, 1000);

        // Remove animation class after animation completes
        setTimeout(() => {
            scoreElement.classList.remove('score-increase');
        }, 500);

        // Trigger confetti
        utils.triggerConfetti();

        // Haptic feedback
        utils.hapticFeedback([10, 50, 10, 50, 10]);

        // Show toast
        utils.showToast(`Reliability score increased to ${newScore}!`, 'success');
    }

    // Render doughnut chart for reliability score
    renderScoreChart(score) {
        const canvas = document.getElementById('scoreChart');
        if (!canvas || !window.Chart) return;

        const ctx = canvas.getContext('2d');

        // Destroy existing chart if any
        if (canvas.chart) {
            canvas.chart.destroy();
        }

        const percentage = score;
        const remaining = 100 - score;

        canvas.chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [percentage, remaining],
                    backgroundColor: [
                        'rgba(59, 130, 246, 0.8)',
                        'rgba(229, 231, 235, 0.3)'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                cutout: '75%',
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false
                    }
                }
            }
        });
    }

    // Show loading overlay
    showLoadingOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'loadingOverlay';
        overlay.className = 'fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center';
        overlay.innerHTML = `
            <div class="glass-card rounded-2xl p-8 flex flex-col items-center">
                <div class="spinner mb-4" style="width: 40px; height: 40px; border-width: 4px;"></div>
                <p class="text-gray-700 dark:text-gray-300 font-medium">Loading...</p>
            </div>
        `;
        document.body.appendChild(overlay);
    }

    // Hide loading overlay
    hideLoadingOverlay() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.remove();
        }
    }

    // Format and display user info
    displayUserInfo(user) {
        const userNameEl = document.getElementById('userName');
        const userInitialsEl = document.getElementById('userInitials');
        const reliabilityScoreEl = document.getElementById('reliabilityScore');

        if (userNameEl) {
            userNameEl.textContent = user.name || user.username;
        }

        if (userInitialsEl) {
            userInitialsEl.textContent = utils.getInitials(user.name || user.username);
        }

        if (reliabilityScoreEl) {
            utils.animateNumber(reliabilityScoreEl, 0, Math.round(user.reliability_score || 0), 1500);
        }

        // Render score chart
        this.renderScoreChart(Math.round(user.reliability_score || 0));
    }

    // Auto-format invite code input
    setupInviteCodeInput() {
        const inviteCodeInput = document.getElementById('inviteCode');
        if (!inviteCodeInput) return;

        inviteCodeInput.addEventListener('input', (e) => {
            e.target.value = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').substring(0, 8);
        });
    }

    // Setup copy code buttons
    setupCopyCodeButtons() {
        document.addEventListener('click', (e) => {
            const btn = e.target.closest('.copy-code-btn');
            if (btn) {
                e.stopPropagation();
                const code = btn.dataset.code;
                utils.copyToClipboard(code);
            }
        });
    }
}

// Create global UI instance
window.ui = new UI();
