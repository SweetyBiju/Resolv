// Utility functions for Resolv

// Format currency in INR
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    }).format(amount);
}

// Animate number counting up
function animateNumber(element, start, end, duration = 1000) {
    const startTime = performance.now();
    const difference = end - start;

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Easing function for smooth animation
        const easeOutQuad = progress * (2 - progress);
        const current = start + (difference * easeOutQuad);

        element.textContent = Math.round(current);

        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            element.textContent = end;
        }
    }

    requestAnimationFrame(update);
}

// Haptic feedback
function hapticFeedback(pattern = [10, 30, 10]) {
    if ('vibrate' in navigator) {
        navigator.vibrate(pattern);
    }
}

// Show toast notification
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `fixed top-4 right-4 z-50 px-6 py-4 rounded-lg shadow-lg fade-in max-w-sm ${
        type === 'success' ? 'bg-green-500 text-white' :
        type === 'error' ? 'bg-red-500 text-white' :
        type === 'warning' ? 'bg-yellow-500 text-white' :
        'bg-blue-500 text-white'
    }`;

    const iconMap = {
        success: 'check-circle',
        error: 'x-circle',
        warning: 'alert-triangle',
        info: 'info'
    };

    toast.innerHTML = `
        <div class="flex items-center space-x-3">
            <i data-lucide="${iconMap[type]}" class="w-5 h-5"></i>
            <p class="font-medium">${message}</p>
        </div>
    `;

    document.body.appendChild(toast);

    if (window.lucide) {
        lucide.createIcons();
    }

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Generate random color for avatar
function generateAvatarColor(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }

    const colors = [
        'from-blue-400 to-blue-600',
        'from-purple-400 to-purple-600',
        'from-pink-400 to-pink-600',
        'from-green-400 to-green-600',
        'from-yellow-400 to-yellow-600',
        'from-red-400 to-red-600',
        'from-indigo-400 to-indigo-600',
        'from-teal-400 to-teal-600',
    ];

    return colors[Math.abs(hash) % colors.length];
}

// Get initials from name
function getInitials(name) {
    if (!name) return 'U';

    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) {
        return parts[0].substring(0, 2).toUpperCase();
    }
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
        return 'Today';
    } else if (diffDays === 1) {
        return 'Yesterday';
    } else if (diffDays < 7) {
        return `${diffDays} days ago`;
    } else if (diffDays < 30) {
        const weeks = Math.floor(diffDays / 7);
        return `${weeks} ${weeks === 1 ? 'week' : 'weeks'} ago`;
    } else {
        return date.toLocaleDateString('en-IN', {
            day: 'numeric',
            month: 'short',
            year: 'numeric'
        });
    }
}

// Validate invite code format
function validateInviteCode(code) {
    return /^[A-Z0-9]{8}$/.test(code);
}

// Copy to clipboard
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copied to clipboard!', 'success');
        hapticFeedback([10]);
        return true;
    } catch (err) {
        console.error('Failed to copy:', err);
        showToast('Failed to copy', 'error');
        return false;
    }
}

// Show loading spinner
function showLoading(element) {
    const spinner = document.createElement('div');
    spinner.className = 'spinner inline-block';
    element.appendChild(spinner);
    return spinner;
}

// Hide loading spinner
function hideLoading(spinner) {
    if (spinner && spinner.parentNode) {
        spinner.remove();
    }
}

// Confirm dialog
function confirm(message, onConfirm, onCancel) {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4';

    modal.innerHTML = `
        <div class="glass-card rounded-2xl p-6 max-w-sm w-full">
            <div class="flex items-start space-x-3 mb-6">
                <div class="w-10 h-10 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                    <i data-lucide="alert-triangle" class="w-6 h-6 text-yellow-600 dark:text-yellow-400"></i>
                </div>
                <div>
                    <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Confirm Action</h3>
                    <p class="text-sm text-gray-600 dark:text-gray-400">${message}</p>
                </div>
            </div>
            <div class="flex space-x-3">
                <button class="confirm-btn flex-1 bg-blue-600 text-white font-semibold py-2 rounded-lg hover:bg-blue-700 transition-colors">
                    Confirm
                </button>
                <button class="cancel-btn px-6 py-2 rounded-lg border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                    Cancel
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    if (window.lucide) {
        lucide.createIcons();
    }

    const confirmBtn = modal.querySelector('.confirm-btn');
    const cancelBtn = modal.querySelector('.cancel-btn');

    confirmBtn.addEventListener('click', () => {
        modal.remove();
        if (onConfirm) onConfirm();
    });

    cancelBtn.addEventListener('click', () => {
        modal.remove();
        if (onCancel) onCancel();
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
            if (onCancel) onCancel();
        }
    });
}

// Calculate reliability score increase
function calculateScoreIncrease(currentScore) {
    return Math.min(100.0, currentScore + 0.5);
}

// Trigger confetti animation
function triggerConfetti() {
    if (window.confetti) {
        confetti({
            particleCount: 100,
            spread: 70,
            origin: { y: 0.6 },
            colors: ['#3b82f6', '#8b5cf6', '#ec4899', '#10b981']
        });
    }
}

// Generate invite code
function generateInviteCode() {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let code = '';
    for (let i = 0; i < 8; i++) {
        code += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return code;
}

// Export utilities
window.utils = {
    formatCurrency,
    animateNumber,
    hapticFeedback,
    showToast,
    debounce,
    generateAvatarColor,
    getInitials,
    formatDate,
    validateInviteCode,
    copyToClipboard,
    showLoading,
    hideLoading,
    confirm,
    calculateScoreIncrease,
    triggerConfetti,
    generateInviteCode
};
