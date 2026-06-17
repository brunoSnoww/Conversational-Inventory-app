import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { login as apiLogin, register as apiRegister } from '../api/inventory';
import type { AuthSession } from '../api/types';
import { routes } from '../routes';
import { disconnectPowerSync } from '../sync/db';

const STORAGE_KEY = 'inventory.auth';

type AuthContextValue = {
  session: AuthSession | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function loadSession(): AuthSession | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as AuthSession & { userId?: string | number };
    if (typeof parsed.userId !== 'string') {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

async function persistSession(load: () => Promise<AuthSession>): Promise<AuthSession> {
  await disconnectPowerSync(true);
  return load();
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(loadSession);

  const authenticate = useCallback(async (load: () => Promise<AuthSession>) => {
    const next = await persistSession(load);
    setSession(next);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  }, []);

  const login = useCallback(
    (email: string, password: string) => authenticate(() => apiLogin(email, password)),
    [authenticate],
  );

  const register = useCallback(
    (email: string, password: string) => authenticate(() => apiRegister(email, password)),
    [authenticate],
  );

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setSession(null);
    void disconnectPowerSync(true).finally(() => {
      window.location.assign(routes.login);
    });
  }, []);

  const value = useMemo(() => ({ session, login, register, logout }), [session, login, register, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth outside AuthProvider');
  }
  return ctx;
}
