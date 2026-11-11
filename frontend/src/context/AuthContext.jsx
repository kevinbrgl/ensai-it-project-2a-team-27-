import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import * as authApi from '../api/auth';
import { getToken, onUnauthorized, setToken } from '../api/client';
import { getMe } from '../api/users';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // checking: an existing token is being verified on first load
  // anonymous: no valid session (never signed in, or the token expired)
  // signedOut: the user just signed out on purpose
  const [status, setStatus] = useState(() => (getToken() ? 'checking' : 'anonymous'));

  const clearSession = useCallback((reason = 'anonymous') => {
    setToken(null);
    setUser(null);
    setStatus(reason);
  }, []);

  useEffect(() => {
    onUnauthorized(() => clearSession());
    if (!getToken()) return;
    getMe()
      .then((me) => {
        setUser(me);
        setStatus('authenticated');
      })
      .catch(() => clearSession());
  }, [clearSession]);

  // Night theme: tokens.css overrides the colour tokens under [data-theme='night'].
  useEffect(() => {
    document.documentElement.dataset.theme = user?.theme === 'night' ? 'night' : 'day';
  }, [user?.theme]);

  const login = useCallback(async (username, password) => {
    const { access_token: accessToken } = await authApi.login({ username, password });
    setToken(accessToken);
    try {
      const me = await getMe();
      setUser(me);
      setStatus('authenticated');
      return me;
    } catch (error) {
      setToken(null);
      throw error;
    }
  }, []);

  const register = useCallback(
    async ({ username, email, password }) => {
      await authApi.register({ username, email, password });
      return login(username, password);
    },
    [login],
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      clearSession('signedOut');
    }
  }, [clearSession]);

  const value = useMemo(
    () => ({ user, status, login, register, logout, setUser }),
    [user, status, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>');
  return context;
}