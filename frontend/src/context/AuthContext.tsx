import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { authApi, setAuthErrorHandler, setTokenGetter } from "../api/client";

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.exp * 1000 < Date.now();
  } catch {
    return true;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Initialize from localStorage
  useEffect(() => {
    const stored = localStorage.getItem("token");
    if (stored && !isTokenExpired(stored)) {
      setToken(stored);
    } else {
      localStorage.removeItem("token");
    }
    setIsLoading(false);
  }, []);

  // Wire up the API client's token getter — reads from localStorage
  // so it always has the latest token, even before React re-renders
  useEffect(() => {
    setTokenGetter(() => localStorage.getItem("token"));
  }, []);

  const clearSession = useCallback(() => {
    setToken(null);
    localStorage.removeItem("token");
    queryClient.clear();
  }, [queryClient]);

  // Wire up auto-logout on 401
  useEffect(() => {
    setAuthErrorHandler(() => {
      clearSession();
      navigate("/login", { replace: true });
    });
  }, [clearSession, navigate]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await authApi.login(email, password);
    localStorage.setItem("token", res.access_token);
    setToken(res.access_token);
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    const res = await authApi.register(email, password);
    localStorage.setItem("token", res.access_token);
    setToken(res.access_token);
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Server-side revocation is best-effort
    }
    clearSession();
    navigate("/login", { replace: true });
  }, [clearSession, navigate]);

  const value = useMemo(
    () => ({ token, isAuthenticated: token !== null, isLoading, login, register, logout }),
    [token, isLoading, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
