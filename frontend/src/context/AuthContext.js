import React, { createContext, useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { API } from '../config/api';

export const AuthContext = createContext();

// Configure axios to send cookies with every request
axios.defaults.withCredentials = true;

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const refreshTimerRef = useRef(null);

  const scheduleRefresh = useCallback((accessToken) => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    try {
      const payload = JSON.parse(atob(accessToken.split('.')[1]));
      const expiresAt = payload.exp * 1000;
      const refreshAt = expiresAt - 60_000; // 1 min before expiry
      const delay = Math.max(refreshAt - Date.now(), 5000);
      refreshTimerRef.current = setTimeout(() => refreshAccessToken(), delay);
    } catch {
      // Invalid token format
    }
  }, []);

  const refreshAccessToken = useCallback(async () => {
    const savedRefresh = localStorage.getItem('refresh_token');
    try {
      // Send refresh token in body AND as cookie (dual-mode)
      const res = await axios.post(`${API}/auth/refresh`, {
        refresh_token: savedRefresh || "",
      });
      const { token: newAccess, refresh_token: newRefresh, user: newUser } = res.data;
      applyTokens(newAccess, newRefresh, newUser);
    } catch {
      doLogout();
    }
  }, []);

  const applyTokens = useCallback((accessToken, refreshToken, userData) => {
    setToken(accessToken);
    setUser(userData);
    // Keep localStorage as fallback for Authorization header
    localStorage.setItem('token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
    localStorage.setItem('user', JSON.stringify(userData));
    axios.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;
    scheduleRefresh(accessToken);
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
          try {
            const savedRefresh = localStorage.getItem('refresh_token');
            const res = await axios.post(`${API}/auth/refresh`, {
              refresh_token: savedRefresh || "",
            });
            const { token: newAccess, refresh_token: newRefresh, user: newUser } = res.data;
            applyTokens(newAccess, newRefresh, newUser);
            originalRequest.headers['Authorization'] = `Bearer ${newAccess}`;
            return axios(originalRequest);
          } catch {
            doLogout();
          }
        }
        return Promise.reject(error);
      }
    );
    return () => axios.interceptors.response.eject(interceptor);
  }, [applyTokens, doLogout]);

  const login = async (email, password) => {
    const response = await axios.post(`${API}/auth/login`, { email, password });
    const { token: newToken, refresh_token: newRefresh, user: newUser } = response.data;
    applyTokens(newToken, newRefresh, newUser);
    return newUser;
  };

  const register = async (userData) => {
    const response = await axios.post(`${API}/auth/register`, userData);
    const { token: newToken, refresh_token: newRefresh, user: newUser } = response.data;
    applyTokens(newToken, newRefresh, newUser);
    return newUser;
  };

  const logout = async () => {
    const savedRefresh = localStorage.getItem('refresh_token');
    try {
      await axios.post(`${API}/auth/logout`, { refresh_token: savedRefresh || "" });
    } catch {
      // Ignore
    }
    doLogout();
  };

  // ---- Impersonation ----

  const applyImpersonationToken = useCallback(async (newToken) => {
    // Impersonation doesn't issue a fresh refresh token — we keep the existing one
    // so that when impersonation expires, the superadmin can still refresh back
    // into their real session seamlessly.
    const savedRefresh = localStorage.getItem('refresh_token') || '';
    localStorage.setItem('token', newToken);
    setToken(newToken);
    axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
    // Fetch the user's full profile + impersonation flag
    const meRes = await axios.get(`${API}/auth/me`, {
      headers: { Authorization: `Bearer ${newToken}` },
    });
    setUser(meRes.data);
    localStorage.setItem('user', JSON.stringify(meRes.data));
    scheduleRefresh(newToken);
    return { user: meRes.data, refreshToken: savedRefresh };
  }, [scheduleRefresh]);

  const startImpersonation = async (targetUserId, reason = '') => {
    const res = await axios.post(
      `${API}/superadmin/impersonate/start/${targetUserId}`,
      { reason },
    );
    await applyImpersonationToken(res.data.token);
    return res.data;
  };

  const stopImpersonation = async () => {
    const res = await axios.post(`${API}/superadmin/impersonate/stop`, {});
    await applyImpersonationToken(res.data.token);
    return res.data;
  };

  return (
    <AuthContext.Provider value={{
      user, token, login, register, logout, loading,
      startImpersonation, stopImpersonation,
    }}>
      {children}
    </AuthContext.Provider>
  );
};
