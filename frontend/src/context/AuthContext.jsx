import { createContext, useContext, useCallback, useEffect, useMemo, useState } from "react";
import { api, tokenStore } from "../lib/api";

export const ROLES = {
  viewer: 10,
  operator: 20,
  auditor: 30,
  security_analyst: 40,
  admin: 50,
};

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const handleUnauthorized = useCallback(() => {
    setUser(null);
  }, []);

  useEffect(() => {
    window.addEventListener("aegis:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("aegis:unauthorized", handleUnauthorized);
  }, [handleUnauthorized]);

  useEffect(() => {
    let active = true;
    async function restore() {
      if (!tokenStore.getAccess()) {
        setLoading(false);
        return;
      }
      try {
        const { data } = await api.get("/auth/me");
        if (active) setUser(data);
      } catch {
        if (active) setUser(null);
      } finally {
        if (active) setLoading(false);
      }
    }
    restore();
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (username, password) => {
    const { data } = await api.post("/auth/login", { username, password });
    tokenStore.setTokens(data);
    const { data: me } = await api.get("/auth/me");
    setUser(me);
    return me;
  }, []);

  const logout = useCallback(async () => {
    const refresh = tokenStore.getRefresh();
    if (refresh) {
      try {
        await api.post("/auth/logout", { refresh_token: refresh });
      } catch {
        // ignore — local state still cleared
      }
    }
    tokenStore.clear();
    setUser(null);
  }, []);

  const hasRole = useCallback(
    (required) => {
      if (!user) return false;
      return ROLES[user.role] >= ROLES[required];
    },
    [user]
  );

  const value = useMemo(
    () => ({ user, loading, login, logout, hasRole }),
    [user, loading, login, logout, hasRole]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
