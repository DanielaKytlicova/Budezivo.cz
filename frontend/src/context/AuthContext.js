import React, { createContext, useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { API } from '../config/api';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const refreshTimerRef = useRef(null);

  // Schedule automatic token refresh 1 minute before expiry
  const scheduleRefresh = useCallback((accessToken) => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    try {
      const payload = JSON.parse(atob(accessToken.split('.')[1]));
      const expiresAt = payload.exp * 1000;
      const refreshAt = expiresAt - 60_000; // 1 min before expiry
      const delay = Math.max(refreshAt - Date.now(), 5000);
      refreshTimerRef.current = setTimeout(() => refreshAccessToken(), delay);
    } catch {
      // Invalid token format – skip scheduling
    }
  }, []);

  const refreshAccessToken = useCallback(async () => {
    const savedRefresh = localStorage.getItem('refresh_token');
    if (!savedRefresh) {
      doLogout();
      return;
    }
    try {
      const res = await axios.post(`${API}/auth/refresh`, { refresh_token: savedRefresh });
      const { token: newAccess, refresh_token: newRefresh, user: newUser } = res.data;

      setToken(newAccess);
      setUser(newUser);
      localStorage.setItem('token', newAccess);
      localStorage.setItem('refresh_token', newRefresh);
      localStorage.setItem('user', JSON.stringify(newUser));
      axios.defaults.headers.common['Authorization'] = `Bearer ${newAccess}`;
      scheduleRefresh(newAccess);
    } catch {
      doLogout();
    }
  }, [scheduleRefresh]);

  const doLogout = useCallback(() => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    delete axios.defaults.headers.common['Authorization'];
  }, []);

  // On mount: restore session
  useEffect(() => {
    const savedToken = localStorage.getItem('token');
    const savedUser = localStorage.getItem('user');

    if (savedToken && savedUser) {
      setToken(savedToken);
      setUser(JSON.parse(savedUser));
      axios.defaults.headers.common['Authorization'] = `Bearer ${savedToken}`;
      scheduleRefresh(savedToken);
    }
    setLoading(false);
  }, [scheduleRefresh]);

  // Axios interceptor: on 401, attempt refresh once
  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;
        if (
          error.response?.status === 401 &&
          !originalRequest._retry &&
          !originalRequest.url?.includes('/auth/refresh') &&
          !originalRequest.url?.includes('/auth/login')
        ) {
          originalRequest._retry = true;
          const savedRefresh = localStorage.getItem('refresh_token');
          if (savedRefresh) {
            try {
              const res = await axios.post(`${API}/auth/refresh`, { refresh_token: savedRefresh });
              const { token: newAccess, refresh_token: newRefresh, user: newUser } = res.data;

              setToken(newAccess);
              setUser(newUser);
              localStorage.setItem('token', newAccess);
              localStorage.setItem('refresh_token', newRefresh);
              localStorage.setItem('user', JSON.stringify(newUser));
              axios.defaults.headers.common['Authorization'] = `Bearer ${newAccess}`;
              scheduleRefresh(newAccess);

              originalRequest.headers['Authorization'] = `Bearer ${newAccess}`;
              return axios(originalRequest);
            } catch {
              doLogout();
            }
          } else {
            doLogout();
          }
        }
        return Promise.reject(error);
      }
    );
    return () => axios.interceptors.response.eject(interceptor);
  }, [scheduleRefresh, doLogout]);

  const login = async (email, password) => {
    const response = await axios.post(`${API}/auth/login`, { email, password });
    const { token: newToken, refresh_token: newRefresh, user: newUser } = response.data;

    setToken(newToken);
    setUser(newUser);
    localStorage.setItem('token', newToken);
    localStorage.setItem('refresh_token', newRefresh);
    localStorage.setItem('user', JSON.stringify(newUser));
    axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
    scheduleRefresh(newToken);

    return newUser;
  };

  const register = async (userData) => {
    const response = await axios.post(`${API}/auth/register`, userData);
    const { token: newToken, refresh_token: newRefresh, user: newUser } = response.data;

    setToken(newToken);
    setUser(newUser);
    localStorage.setItem('token', newToken);
    localStorage.setItem('refresh_token', newRefresh);
    localStorage.setItem('user', JSON.stringify(newUser));
    axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
    scheduleRefresh(newToken);

    return newUser;
  };

  const logout = async () => {
    const savedRefresh = localStorage.getItem('refresh_token');
    if (savedRefresh && token) {
      try {
        await axios.post(`${API}/auth/logout`, { refresh_token: savedRefresh });
      } catch {
        // Ignore errors during logout
      }
    }
    doLogout();
  };

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};
