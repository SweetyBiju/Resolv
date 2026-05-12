/**
 * utils.js - Functional Helpers & Polish
 * Handles formatting, animations, and device haptics.
 */

export const utils = {
    /**
     * Formats numbers into currency strings based on user preference
     * @param {number} amount 
     * @param {string} currencyCode - e.g., 'INR', 'USD'
     */
    formatCurrency: (amount, currencyCode = 'INR') => {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: currencyCode,
            maximumFractionDigits: 2
        }).format(amount);
    },

    /**
     * Animates a number from start to end (used for Trust Banner)
     * @param {HTMLElement} element - The DOM element to update
     * @param {number} start - Starting value
     * @param {number} end - Target value
     * @param {number} duration - Animation time in ms
     */
    animateNumber: (element, start, end, duration = 1000) => {
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            const value = (progress * (end - start) + start).toFixed(2);
            element.innerHTML = value;
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    },

    /**
     * Triggers mobile haptics if supported
     * @param {string} type - 'light', 'medium', 'heavy'
     */
    hapticFeedback: (type = 'light') => {
        if (!window.navigator.vibrate) return;
        
        const patterns = {
            light: [10],
            medium: [20],
            heavy: [50],
            error: [50, 30, 50]
        };
        
        window.navigator.vibrate(patterns[type] || patterns.light);
    },

    /**
     * Simple debounce for search inputs
     */
    debounce: (func, wait) => {
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
};