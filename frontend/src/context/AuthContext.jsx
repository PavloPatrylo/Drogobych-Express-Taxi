import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem('admin_user');
    return savedUser ? JSON.parse(savedUser) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem('admin_token'));
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const handleUnauthorized = () => {
      setUser(null);
      setToken(null);
    };

    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, []);

  const login = async (username, password) => {
    setIsLoading(true);
    try {
      // FastAPI OAuth2 requires application/x-www-form-urlencoded with 'username' and 'password'
      const res = await api.postForm('/auth/login', { username, password });
      const authToken = res.access_token || res.token;

      if (!authToken) {
        throw new Error('Токен авторизації не отримано');
      }

      api.setToken(authToken);

      // Fetch user profile info from /auth/me
      let userData;
      try {
        const meRes = await api.get('/auth/me');
        userData = {
          id: meRes.id,
          name: meRes.full_name || meRes.name || username,
          role: meRes.role || 'dispatcher',
          phone: meRes.phone || username,
        };
      } catch (meError) {
        console.warn('Failed to fetch /auth/me, using fallback profile:', meError);
        userData = {
          name: username,
          role: 'dispatcher',
          phone: username,
        };
      }

      localStorage.setItem('admin_user', JSON.stringify(userData));

      setToken(authToken);
      setUser(userData);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    api.clearToken();
    setToken(null);
    setUser(null);
  };

  const isAuthenticated = Boolean(token);
  const isOwner = user?.role === 'owner' || user?.role === 'admin';

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated, isOwner, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
