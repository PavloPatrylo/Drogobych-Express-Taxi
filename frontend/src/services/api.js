// API Service for Drogobych Express Taxi Admin CRM

const API_BASE_URL = '/api/admin';

export const api = {
  getToken() {
    return localStorage.getItem('admin_token');
  },

  setToken(token) {
    if (token) {
      localStorage.setItem('admin_token', token);
    } else {
      localStorage.removeItem('admin_token');
    }
  },

  clearToken() {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
  },

  async request(endpoint, options = {}) {
    const token = this.getToken();
    const isAuthRequest = endpoint.includes('/auth/login');

    if (!token && !isAuthRequest) {
      throw new Error('Необхідно авторизуватися');
    }

    const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;

    const headers = {
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    };

    try {
      const response = await fetch(url, { ...options, headers });

      if (response.status === 401) {
        this.clearToken();
        window.dispatchEvent(new Event('auth:unauthorized'));
        throw new Error('Сесія закінчилася або невірний логін/пароль');
      }

      if (!response.ok) {
        let errorMsg = `Помилка запиту HTTP ${response.status}`;
        try {
          const data = await response.json();
          if (typeof data.detail === 'string') {
            errorMsg = data.detail;
          } else if (Array.isArray(data.detail)) {
            // FastAPI validation errors detail array
            errorMsg = data.detail.map((err) => err.msg || JSON.stringify(err)).join(', ');
          } else if (data.message) {
            errorMsg = data.message;
          }
        } catch {
          // ignore json parse error
        }
        throw new Error(errorMsg);
      }

      return await response.json();
    } catch (err) {
      console.error(`[API Error] ${endpoint}:`, err.message);
      throw err;
    }
  },

  get(endpoint, params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(query ? `${endpoint}?${query}` : endpoint, { method: 'GET' });
  },

  post(endpoint, data) {
    return this.request(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },

  // Special form-urlencoded post method for OAuth2 FastAPI login
  postForm(endpoint, formData) {
    const body = new URLSearchParams();
    Object.entries(formData).forEach(([key, value]) => {
      body.append(key, value);
    });

    return this.request(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    });
  },

  put(endpoint, data) {
    return this.request(endpoint, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },

  patch(endpoint, data) {
    return this.request(endpoint, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },

  delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  },
};

export default api;
