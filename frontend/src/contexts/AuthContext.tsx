import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import * as api from '../services/api';

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, name: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('auth_token'));
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (token) {
      api.getMe()
        .then(data => setUser({ id: data.id, email: data.email, name: data.name, role: data.role }))
        .catch(() => { localStorage.removeItem('auth_token'); setToken(null); })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await api.login({ email, password });
    localStorage.setItem('auth_token', data.access_token);
    setToken(data.access_token);
    const me = await api.getMe();
    setUser({ id: me.id, email: me.email, name: me.name, role: me.role });
  }, []);

  const register = useCallback(async (email: string, name: string, password: string) => {
    const data = await api.register({ email, name, password });
    localStorage.setItem('auth_token', data.access_token);
    setToken(data.access_token);
    const me = await api.getMe();
    setUser({ id: me.id, email: me.email, name: me.name, role: me.role });
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token');
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
