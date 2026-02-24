// Authentication handler

class Auth {
    constructor() {
        this.currentUser = null;
    }

    // Check if user is authenticated
    isAuthenticated() {
        return !!api.getToken();
    }

    // Login user
    async login(username, password) {
        try {
            const response = await api.login(username, password);

            if (response.user) {
                this.currentUser = response.user;
            }

            // Redirect to dashboard
            window.location.href = 'index.html';

            return response;
        } catch (error) {
            console.error('Login failed:', error);
            throw error;
        }
    }

    // Register new user
    async register(userData) {
        try {
            const response = await api.register(userData);
            return response;
        } catch (error) {
            console.error('Registration failed:', error);
            throw error;
        }
    }

    // Logout user
    logout() {
        api.removeToken();
        this.currentUser = null;
        window.location.href = 'login.html';
    }

    // Get current user
    async getCurrentUser() {
        if (this.currentUser) {
            return this.currentUser;
        }

        try {
            this.currentUser = await api.getCurrentUser();
            return this.currentUser;
        } catch (error) {
            console.error('Failed to get current user:', error);
            this.logout();
            throw error;
        }
    }

    // Require authentication (redirect if not logged in)
    requireAuth() {
        if (!this.isAuthenticated()) {
            window.location.href = 'login.html';
            return false;
        }
        return true;
    }

    // Update user reliability score
    async updateReliabilityScore(newScore) {
        if (this.currentUser) {
            this.currentUser.reliability_score = newScore;
        }
    }
}

// Create global auth instance
window.auth = new Auth();
