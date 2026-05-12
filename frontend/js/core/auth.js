/**
 * auth.js - Authentication & Session Management
 * Handles token persistence, refresh logic, and route guarding.
 */

import { api } from './api.js';

class AuthManager {
    constructor() {
        this.accessKey = 'resolv_access_token';
        this.refreshKey = 'resolv_refresh_token';
    }

    /**
     * Stores tokens and redirects to dashboard
     * @param {string} access - JWT Access Token
     * @param {string} refresh - JWT Refresh Token
     */
    setSession(access, refresh) {
        localStorage.setItem(this.accessKey, access);
        localStorage.setItem(this.refreshKey, refresh);
    }

    /**
     * Clears local session and redirects to login
     */
    logout() {
        localStorage.removeItem(this.accessKey);
        localStorage.removeItem(this.refreshKey);
        window.location.href = 'login.html';
    }

    /**
     * Checks if user is logged in
     * @returns {boolean}
     */
    isAuthenticated() {
        return !!localStorage.getItem(this.accessKey);
    }

    /**
     * Attempt to refresh the access token using the refresh token
     * Maps to POST /api/token/refresh/
     */
    async refreshAccessToken() {
        const refreshToken = localStorage.getItem(this.refreshKey);
        if (!refreshToken) {
            this.logout();
            return null;
        }

        try {
            const response = await fetch(`${api.baseURL}/token/refresh/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh: refreshToken })
            });

            if (response.ok) {
                const data = await response.json();
                localStorage.setItem(this.accessKey, data.access);
                return data.access;
            } else {
                throw new Error('Refresh token expired');
            }
        } catch (error) {
            console.error('Session expired. Please log in again.');
            this.logout();
            return null;
        }
    }

    /**
     * Guard: Redirects to login if not authenticated.
     * Call this at the top of protected pages.
     */
    checkAuthAndRedirect() {
        if (!this.isAuthenticated()) {
            window.location.href = 'login.html';
        }
    }

    /**
     * Guard: Redirects to dashboard if already logged in.
     * Call this on login/register pages.
     */
    checkGuestAndRedirect() {
        if (this.isAuthenticated()) {
            window.location.href = 'dashboard.html';
        }
    }
}

export const auth = new AuthManager();