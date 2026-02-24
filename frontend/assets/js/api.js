// API handler with demo mode fallback

class ResolvAPI {
    constructor(baseURL = 'http://127.0.0.1:8000/api') {
        this.baseURL = baseURL;
        this.demoMode = false;
    }

    // Get auth token from localStorage
    getToken() {
        return localStorage.getItem('access_token');
    }

    // Set auth token
    setToken(token) {
        localStorage.setItem('access_token', token);
    }

    // Remove auth token
    removeToken() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
    }

    // Build headers with auth token
    getHeaders(includeAuth = true) {
        const headers = {
            'Content-Type': 'application/json',
        };

        if (includeAuth) {
            const token = this.getToken();
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
        }

        return headers;
    }

    // Main request method with demo mode fallback
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            ...options,
            headers: this.getHeaders(options.auth !== false),
        };

        try {
            const response = await fetch(url, config);

            // Handle 401 Unauthorized
            if (response.status === 401) {
                this.removeToken();
                window.location.href = 'login.html';
                throw new Error('Unauthorized');
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || errorData.detail || 'Request failed');
            }

            return await response.json();
        } catch (error) {
            console.warn('API request failed, switching to demo mode:', error);

            // Enable demo mode and return mock data
            this.demoMode = true;
            return this.getDemoData(endpoint, options.method || 'GET');
        }
    }

    // Demo mode data generator
    getDemoData(endpoint, method) {
        console.log('Demo Mode: Serving mock data for', endpoint);

        // Demo user data
        const demoUser = {
            id: 1,
            username: 'demo_user',
            email: 'demo@resolv.com',
            name: 'Demo User',
            reliability_score: 85.5
        };

        // Demo groups with Goa Trip scenario
        const demoGroups = [
            {
                id: 1,
                name: 'Goa Trip 2024',
                description: 'Beach vacation with friends',
                invite_code: 'GOA2024X',
                member_count: 3,
                total_expenses: 1200,
                created_at: '2024-01-15T10:00:00Z',
                members: [
                    { id: 1, name: 'Demo User', username: 'demo_user' },
                    { id: 2, name: 'Alice Kumar', username: 'alice_k' },
                    { id: 3, name: 'Bob Sharma', username: 'bob_s' }
                ]
            },
            {
                id: 2,
                name: 'Apartment Roommates',
                description: 'Monthly shared expenses',
                invite_code: 'ROOM2024',
                member_count: 4,
                total_expenses: 8500,
                created_at: '2024-01-01T00:00:00Z',
                members: [
                    { id: 1, name: 'Demo User', username: 'demo_user' },
                    { id: 4, name: 'Carol Singh', username: 'carol_s' },
                    { id: 5, name: 'David Patel', username: 'david_p' },
                    { id: 6, name: 'Eve Reddy', username: 'eve_r' }
                ]
            }
        ];

        // Demo expenses for Goa Trip
        const demoExpenses = [
            {
                id: 1,
                group: 1,
                description: 'Hotel Booking',
                amount: 900,
                paid_by: { id: 1, name: 'Demo User' },
                split_among: [1, 2, 3],
                created_at: '2024-01-15T14:00:00Z',
                category: 'Accommodation'
            },
            {
                id: 2,
                group: 1,
                description: 'Beach Lunch',
                amount: 300,
                paid_by: { id: 2, name: 'Alice Kumar' },
                split_among: [1, 2, 3],
                created_at: '2024-01-15T13:30:00Z',
                category: 'Food'
            }
        ];

        // Demo settlements - optimal transactions
        const demoSettlements = [
            {
                id: 1,
                from_user: { id: 2, name: 'Alice Kumar', username: 'alice_k' },
                to_user: { id: 1, name: 'Demo User', username: 'demo_user' },
                amount: 200,
                group: { id: 1, name: 'Goa Trip 2024' },
                status: 'pending',
                created_at: '2024-01-16T10:00:00Z',
                description: 'Settlement for Goa Trip expenses'
            },
            {
                id: 2,
                from_user: { id: 3, name: 'Bob Sharma', username: 'bob_s' },
                to_user: { id: 1, name: 'Demo User', username: 'demo_user' },
                amount: 200,
                group: { id: 1, name: 'Goa Trip 2024' },
                status: 'pending',
                created_at: '2024-01-16T10:00:00Z',
                description: 'Settlement for Goa Trip expenses'
            }
        ];

        // Route matching for demo data
        if (endpoint.includes('/auth/token/') || endpoint.includes('/login')) {
            return {
                access: 'demo_access_token_' + Date.now(),
                refresh: 'demo_refresh_token_' + Date.now(),
                user: demoUser
            };
        }

        if (endpoint.includes('/auth/register/')) {
            return {
                ...demoUser,
                message: 'Registration successful'
            };
        }

        if (endpoint.includes('/auth/user/') || endpoint.includes('/me')) {
            return demoUser;
        }

        if (endpoint.includes('/groups/') && method === 'GET') {
            const groupId = endpoint.match(/\/groups\/(\d+)\//)?.[1];
            if (groupId) {
                return demoGroups.find(g => g.id === parseInt(groupId)) || demoGroups[0];
            }
            return demoGroups;
        }

        if (endpoint.includes('/groups/') && method === 'POST') {
            return {
                ...demoGroups[0],
                id: Date.now(),
                name: 'New Group',
                invite_code: utils.generateInviteCode(),
                created_at: new Date().toISOString()
            };
        }

        if (endpoint.includes('/expenses/')) {
            const groupId = endpoint.match(/group=(\d+)/)?.[1];
            if (groupId) {
                return demoExpenses.filter(e => e.group === parseInt(groupId));
            }
            return demoExpenses;
        }

        if (endpoint.includes('/settlements/')) {
            if (method === 'POST') {
                return {
                    ...demoSettlements[0],
                    id: Date.now(),
                    status: 'completed',
                    completed_at: new Date().toISOString()
                };
            }
            return demoSettlements;
        }

        if (endpoint.includes('/balances/')) {
            return [
                { user: 'Alice Kumar', balance: -200 },
                { user: 'Bob Sharma', balance: -200 },
                { user: 'Demo User', balance: 400 }
            ];
        }

        // Default empty response
        return { message: 'Demo mode active', data: [] };
    }

    // Auth endpoints
    async login(username, password) {
        const response = await this.request('/auth/token/', {
            method: 'POST',
            auth: false,
            body: JSON.stringify({ username, password })
        });

        if (response.access) {
            this.setToken(response.access);
            localStorage.setItem('refresh_token', response.refresh);
        }

        return response;
    }

    async register(userData) {
        return await this.request('/auth/register/', {
            method: 'POST',
            auth: false,
            body: JSON.stringify(userData)
        });
    }

    async getCurrentUser() {
        return await this.request('/auth/user/');
    }

    // Group endpoints
    async getGroups() {
        return await this.request('/groups/');
    }

    async getGroup(groupId) {
        return await this.request(`/groups/${groupId}/`);
    }

    async createGroup(groupData) {
        return await this.request('/groups/', {
            method: 'POST',
            body: JSON.stringify(groupData)
        });
    }

    async joinGroup(inviteCode) {
        return await this.request('/groups/join/', {
            method: 'POST',
            body: JSON.stringify({ invite_code: inviteCode })
        });
    }

    // Expense endpoints
    async getExpenses(groupId) {
        return await this.request(`/expenses/?group=${groupId}`);
    }

    async createExpense(expenseData) {
        return await this.request('/expenses/', {
            method: 'POST',
            body: JSON.stringify(expenseData)
        });
    }

    // Settlement endpoints
    async getSettlements() {
        return await this.request('/settlements/');
    }

    async confirmSettlement(settlementId) {
        return await this.request(`/settlements/${settlementId}/confirm/`, {
            method: 'POST'
        });
    }

    // Balance endpoints
    async getBalances(groupId) {
        return await this.request(`/balances/?group=${groupId}`);
    }
}

// Create global API instance
window.api = new ResolvAPI();
