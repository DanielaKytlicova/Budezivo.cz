import React, { createContext, useState, useEffect, useContext, useCallback, useRef } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

/**
 * Teacher auth context — independent from institutional admin AuthContext.
 *
 * State:
 *   teacher === null      → still checking session
 *   teacher === false     → not logged in
 *   teacher === { ... }   → logged in profile
 *
 * Token is stored in:
 *   - HttpOnly cookie (`teacher_token`) — set by backend on register/login
 *   - localStorage (`bz_teacher_token`) — fallback for environments where the
 *     httpOnly cookie does not survive the cross-subdomain preview proxy.
 *     We attach it as `Authorization: Bearer ...` when present.
 */
const TeacherAuthContext = createContext(null);

const LS_KEY = 'bz_teacher_token';

const formatErr = (detail) => {
  if (detail == null) return 'Něco se pokazilo. Zkuste to prosím znovu.';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map(e => e?.msg || JSON.stringify(e)).join(' ');
  return String(detail);
};

export const TeacherAuthProvider = ({ children }) => {
  const [teacher, setTeacher] = useState(null);          // null = checking, false = anon
  const tokenRef = useRef(localStorage.getItem(LS_KEY) || null);

  const authConfig = useCallback(() => {
    const cfg = { withCredentials: true };
    if (tokenRef.current) {
      cfg.headers = { Authorization: `Bearer ${tokenRef.current}` };
    }
    return cfg;
  }, []);

  const refreshMe = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API_URL}/api/teacher/auth/me`, authConfig());
      setTeacher(data);
      return data;
    } catch (_e) {
      setTeacher(false);
      return null;
    }
  }, [authConfig]);

  useEffect(() => {
    refreshMe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const register = async (payload) => {
    try {
      const { data } = await axios.post(`${API_URL}/api/teacher/auth/register`, payload, { withCredentials: true });
      if (data.access_token) {
        tokenRef.current = data.access_token;
        localStorage.setItem(LS_KEY, data.access_token);
      }
      const profile = { ...data };
      delete profile.access_token;
      setTeacher(profile);
      return { ok: true, profile };
    } catch (e) {
      return { ok: false, error: formatErr(e.response?.data?.detail) || e.message };
    }
  };

  const login = async (email, password) => {
    try {
      const { data } = await axios.post(`${API_URL}/api/teacher/auth/login`, { email, password }, { withCredentials: true });
      if (data.access_token) {
        tokenRef.current = data.access_token;
        localStorage.setItem(LS_KEY, data.access_token);
      }
      const profile = { ...data };
      delete profile.access_token;
      setTeacher(profile);
      return { ok: true, profile };
    } catch (e) {
      return { ok: false, error: formatErr(e.response?.data?.detail) || e.message };
    }
  };

  const logout = async () => {
    try {
      await axios.post(`${API_URL}/api/teacher/auth/logout`, {}, authConfig());
    } catch (_e) { /* noop */ }
    tokenRef.current = null;
    localStorage.removeItem(LS_KEY);
    setTeacher(false);
  };

  const updateProfile = async (payload) => {
    try {
      const { data } = await axios.patch(`${API_URL}/api/teacher/me`, payload, authConfig());
      setTeacher(data);
      return { ok: true, profile: data };
    } catch (e) {
      return { ok: false, error: formatErr(e.response?.data?.detail) || e.message };
    }
  };

  const value = {
    teacher,
    isLoading: teacher === null,
    isAuthenticated: teacher && teacher !== false,
    register,
    login,
    logout,
    updateProfile,
    authConfig,
    refreshMe,
  };

  return <TeacherAuthContext.Provider value={value}>{children}</TeacherAuthContext.Provider>;
};

export const useTeacherAuth = () => {
  const ctx = useContext(TeacherAuthContext);
  if (!ctx) throw new Error('useTeacherAuth must be used within TeacherAuthProvider');
  return ctx;
};

export default TeacherAuthContext;
