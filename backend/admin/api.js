// ══════════════════════════════════════════════
//  API CLIENT + STATE MANAGER (api.js)
//  Production Ready v2.3 — вилучено дублікати
// ══════════════════════════════════════════════

const API_BASE_URL = '/api/admin';

// ====================== STATE MANAGER ======================
const appState = {
    trips: [],
    passengers: [],
    bookings: [],
    vehicles: [],
    drivers: [],
    auditLog: [],
    lastSync: null,
    isInitialized: false
};

// ====================== CONFIG (відповідно до SRS) ======================
const CONFIG = {
    DEFAULT_PRICE_SEATED: 120,
    DEFAULT_PRICE_STANDING: 80,
    DEFAULT_PRICE_PARCEL: 50,
    CANCELLATION_DEADLINE_HOURS: 2,

    TRUST_SCORE_FORMULA: (trips = 0, noshows = 0) =>
        Math.max(0, Math.round(100 - (noshows / Math.max(trips, 1)) * 100)),

    STATUS_FLOW: {
        SCHEDULED: 'BOARDING',
        BOARDING: 'ACTIVE',
        ACTIVE: 'COMPLETED',
        COMPLETED: 'CLOSED'
    }
};

// ====================== API CLIENT ======================
const api = {
    token: localStorage.getItem('admin_token'),

    setToken(newToken) {
        this.token = newToken;
        localStorage.setItem('admin_token', newToken);
    },

    clearToken() {
        this.token = null;
        localStorage.removeItem('admin_token');
    },

    async request(endpoint, options = {}) {
        // Захист від запитів без токена (крім авторизації)
        if (!this.token && !endpoint.includes('/auth')) {
            console.warn('API call without token:', endpoint);
            throw new Error('No authentication token');
        }

        const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;

        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...(this.token && { 'Authorization': `Bearer ${this.token}` })
            },
            ...options
        };

        const response = await fetch(url, config);

        if (!response.ok) {
            if (response.status === 401) {
                this.clearToken();
                toast('error', 'Сесія закінчилася. Увійдіть знову.');
                setTimeout(() => window.location.reload(), 1500);
                throw new Error('Unauthorized');
            }

            let errorMsg = `HTTP ${response.status}`;
            try {
                const errorData = await response.json();
                errorMsg = errorData.detail || errorData.message || errorMsg;
            } catch (e) {}

            throw new Error(errorMsg);
        }

        return await response.json();
    },

    get(endpoint, params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(query ? `${endpoint}?${query}` : endpoint, { method: 'GET' });
    },

    post(endpoint, data) {
        return this.request(endpoint, { method: 'POST', body: JSON.stringify(data) });
    },

    put(endpoint, data) {
        return this.request(endpoint, { method: 'PUT', body: JSON.stringify(data) });
    },

    delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }
};

// ====================== DATA OPERATIONS ======================
async function syncData() {
    try {
        const [tripsRes, passengersRes, vehiclesRes] = await Promise.all([
            api.get('/trips').catch(() => ({ data: [] })),
            api.get('/users/passengers?include_stats=true').catch(() => ({ data: [] })),
            api.get('/vehicles').catch(() => ({ data: [] }))
        ]);

        appState.trips = tripsRes.data || [];
        appState.passengers = passengersRes.data || [];
        appState.vehicles = vehiclesRes.data || [];
        appState.lastSync = new Date();
        appState.isInitialized = true;

        return true;
    } catch (err) {
        console.error('Sync failed:', err);
        return false;
    }
}

function updateEntity(collectionName, id, updates) {
    const collection = appState[collectionName];
    if (!Array.isArray(collection)) return false;

    const index = collection.findIndex(item => item.id === id);
    if (index === -1) return false;

    appState[collectionName][index] = { ...appState[collectionName][index], ...updates };
    return true;
}

async function fetchAuditLog(filters = {}) {
    try {
        const res = await api.get('/audit/log', filters);
        appState.auditLog = res.data || [];
        return appState.auditLog;
    } catch (err) {
        console.error('Failed to fetch audit log', err);
        return [];
    }
}

// ====================== PUBLIC API ======================
window.api = api;
window.apiFetch = (endpoint, params) => api.get(endpoint, params);
window.appState = appState;
window.CONFIG = CONFIG;
window.syncData = syncData;
window.updateEntity = updateEntity;
window.fetchAuditLog = fetchAuditLog;
