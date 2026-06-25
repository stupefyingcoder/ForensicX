import { FirebaseError } from "firebase/app";
import {
  browserLocalPersistence,
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  setPersistence,
  signInWithEmailAndPassword,
  signOut,
} from "firebase/auth";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { authApi, setAuthErrorHandler, setTokenGetter } from "../api/client";
import type { ApiError } from "../api/types";
import { firebaseAuth } from "../config/firebase";

const BACKEND_TOKEN_KEY = "token";

interface AuthState {
  token: string | null;
  userEmail: string | null;
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

function getStoredBackendToken(): string | null {
  const stored = localStorage.getItem(BACKEND_TOKEN_KEY);
  if (stored && !isTokenExpired(stored)) return stored;
  localStorage.removeItem(BACKEND_TOKEN_KEY);
  return null;
}

function toAuthErrorMessage(err: unknown): string {
  if (err instanceof FirebaseError) {
    switch (err.code) {
      case "auth/email-already-in-use":
        return "This email is already registered. Please log in instead.";
      case "auth/invalid-email":
        return "Enter a valid email address.";
      case "auth/invalid-credential":
      case "auth/user-not-found":
      case "auth/wrong-password":
        return "Invalid email or password.";
      case "auth/weak-password":
        return "Password is too weak. Use at least 8 characters.";
      case "auth/network-request-failed":
        return "Network error while contacting Firebase. Check your connection and try again.";
      case "auth/too-many-requests":
        return "Too many failed attempts. Please wait a moment and try again.";
      case "auth/operation-not-allowed":
        return "Email/password sign-in is not enabled in Firebase Console.";
      default:
        return err.message;
    }
  }

  if (typeof err === "object" && err !== null && "message" in err) {
    return String((err as ApiError).message);
  }

  return String(err);
}

async function getBackendToken(email: string, password: string, mode: "login" | "register") {
  try {
    return mode === "register"
      ? await authApi.register(email, password)
      : await authApi.login(email, password);
  } catch (err) {
    const apiErr = err as ApiError;
    if (mode === "register" && apiErr.status === 409) {
      return authApi.login(email, password);
    }
    throw err;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => getStoredBackendToken());
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  useEffect(() => {
    setTokenGetter(() => getStoredBackendToken());
  }, []);

  const clearSession = useCallback(() => {
    setToken(null);
    setUserEmail(null);
    localStorage.removeItem(BACKEND_TOKEN_KEY);
    queryClient.clear();
  }, [queryClient]);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(firebaseAuth, (firebaseUser) => {
      setUserEmail(firebaseUser?.email ?? null);
      setToken(firebaseUser ? getStoredBackendToken() : null);
      setIsLoading(false);
    });

    return unsubscribe;
  }, []);

  useEffect(() => {
    setAuthErrorHandler(() => {
      void signOut(firebaseAuth);
      clearSession();
      navigate("/login", { replace: true });
    });
  }, [clearSession, navigate]);

  const login = useCallback(async (email: string, password: string) => {
    try {
      await setPersistence(firebaseAuth, browserLocalPersistence);
      const credential = await signInWithEmailAndPassword(firebaseAuth, email, password);
      const res = await getBackendToken(credential.user.email ?? email, password, "login");
      localStorage.setItem(BACKEND_TOKEN_KEY, res.access_token);
      setToken(res.access_token);
      setUserEmail(credential.user.email ?? email);
    } catch (err) {
      throw new Error(toAuthErrorMessage(err));
    }
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    try {
      await setPersistence(firebaseAuth, browserLocalPersistence);
      const credential = await createUserWithEmailAndPassword(firebaseAuth, email, password);
      const res = await getBackendToken(credential.user.email ?? email, password, "register");
      localStorage.setItem(BACKEND_TOKEN_KEY, res.access_token);
      setToken(res.access_token);
      setUserEmail(credential.user.email ?? email);
    } catch (err) {
      throw new Error(toAuthErrorMessage(err));
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      if (getStoredBackendToken()) await authApi.logout();
    } catch {
      // Server-side revocation is best-effort.
    } finally {
      await signOut(firebaseAuth);
      clearSession();
      navigate("/login", { replace: true });
    }
  }, [clearSession, navigate]);

  const value = useMemo(
    () => ({
      token,
      userEmail,
      isAuthenticated: Boolean(userEmail && token),
      isLoading,
      login,
      register,
      logout,
    }),
    [token, userEmail, isLoading, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
