import { useCallback, useEffect, useMemo, useState } from 'react';
import type { PropsWithChildren } from 'react';

import {
  apiRequest,
  clearAdminSession,
  hasAdminSession,
  loginRequest,
  saveAdminSession,
} from '../lib/api';
import type { AdminUser } from '../types';
import { AuthContext } from './authContext';

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<AdminUser | null>(null);
  const [loading, setLoading] = useState(hasAdminSession);

  const logout = useCallback(() => {
    clearAdminSession();
    setUser(null);
  }, []);

  useEffect(() => {
    const handleUnauthorized = () => logout();
    window.addEventListener('omeong-admin-unauthorized', handleUnauthorized);
    return () => window.removeEventListener('omeong-admin-unauthorized', handleUnauthorized);
  }, [logout]);

  useEffect(() => {
    if (!hasAdminSession()) {
      return;
    }
    apiRequest<AdminUser>('/admin/me')
      .then(setUser)
      .catch(logout)
      .finally(() => setLoading(false));
  }, [logout]);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await loginRequest(email, password);
    saveAdminSession(tokens);
    try {
      setUser(await apiRequest<AdminUser>('/admin/me'));
    } catch (error) {
      clearAdminSession();
      throw error;
    }
  }, []);

  const value = useMemo(() => ({ user, loading, login, logout }), [user, loading, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
