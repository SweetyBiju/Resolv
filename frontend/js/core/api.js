/**
 * api.js - Core API Communication Layer for Resolv
 * Handles JWT injection, Error Handling, and Demo Mode Fallbacks.
 */

class ResolvAPI {
    constructor() {
        this.baseURL = 'http://localhost:8000/api'; // Update to production URL when deploying
        this.isDemoMode = false;
    }

    /**
     * Helper to get the access token from localStorage
     */
    getAccessToken() {
        return localStorage.getItem('resolv_access_token');
    }

    /**
     * Centralized Request Handler
     * @param {string} endpoint - The API path
     * @param {object} options - Fetch options (method, body, etc.)
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const token = this.getAccessToken();

        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(url, { ...options, headers });

            // Handle 401 Unauthorized (Token Expired or Invalid Credentials)
            if (response.status === 401) {
                // If the user is actively trying to log in, throw the error back to the UI
                // instead of triggering a global logout and redirect.
                if (endpoint === '/token/') {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Invalid credentials');
                }

                console.warn('Unauthorized request. Redirecting to login...');
                this.handleAuthFailure();
                return null;
            }

            if (!response.ok) {
            const contentType = response.headers.get("content-type");
            if (contentType && contentType.includes("application/json")) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'API Request Failed');
            } else {
                throw new Error(`Server crashed with status: ${response.status}`);
            }}

            if (response.status === 204) {
                return true; 
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            
            // Trigger Demo Mode if backend is unreachable
            if (this.isDemoMode || error.message.includes('Failed to fetch')) {
                console.info('Switching to Demo Mode (Goa Trip Scenario)');
                return this.getDemoData(endpoint);
            }
            throw error;
        }
    }

    /**
     * Logic to handle expired sessions
     */
    handleAuthFailure() {
        localStorage.removeItem('resolv_access_token');
        localStorage.removeItem('resolv_refresh_token');
        
        // Use relative path to maintain subfolder routes like /frontend/
        // Prevent redirect loops if already on login.html
        if (!window.location.pathname.includes('login.html')) {
            window.location.href = 'login.html';
        }
    }

    /**
     * Demo Mode Mock Data (Goa Trip Scenario)
     * Provides static data to keep UI functional during offline development.
     */
    getDemoData(endpoint) {
        const demoData = {
            '/users/me/': {
                username: 'cool_traveler',
                upi_id: 'travel@okaxis',
                currency_preference: 'INR',
                reliability_score: '98.50'
            },
            '/groups/': [
                { id: 1, name: 'Goa Trip 2024', invite_code: 'GOA2024X', member_count: 5 }
            ],
            '/expenses/group_balances/': [
                { name: 'You', balance: 1250.00 },
                { name: 'Rahul', balance: -450.00 },
                { name: 'Sneha', balance: -800.00 }
            ]
        };

        return demoData[endpoint] || {};
    }

    // --- Specific API Methods Mapping to Backend Map ---

    // Auth
    async login(credentials) {
        return await this.request('/token/', {
            method: 'POST',
            body: JSON.stringify(credentials)
        });
    }

    // Groups
    async getGroups() {
        return await this.request('/groups/');
    }

    async getGroupDetails(id) {
        return await this.request(`/groups/${id}/`);
    }

    // Expenses
    async getExpenses() {
        return await this.request('/expenses/');
    }

    async createExpense(data) {
        return await this.request('/expenses/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    // Settlements
    async confirmSettlement(id) {
        return await this.request(`/settlements/${id}/confirm_settlement/`, {
            method: 'POST'
        });
    }
}

export const api = new ResolvAPI();