"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useRouter, usePathname } from "next/navigation";

interface User {
  username: string;
  role: "USER" | "ADMIN";
  last_login: string | null;
  password_reset_required?: boolean;
}

interface AuthContextType {
  user: User | null;
  accessToken: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
  fetchWithAuth: (url: string, options?: RequestInit) => Promise<Response>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  // Use a ref for the token to provide a stable reference for fetchWithAuth
  const tokenRef = React.useRef<string | null>(null);
  useEffect(() => {
    tokenRef.current = accessToken;
  }, [accessToken]);

  // Lock to prevent multiple concurrent refresh requests
  const refreshPromise = React.useRef<Promise<string | null> | null>(null);

  const router = useRouter();
  const pathname = usePathname();

  const logout = useCallback(() => {
    setUser(null);
    setAccessToken(null);
    localStorage.removeItem("refresh_token");
    router.push("/login");
  }, [router]);

  const refreshAccessToken = useCallback(async () => {
    // If a refresh is already in progress, return the existing promise
    if (refreshPromise.current) return refreshPromise.current;

    refreshPromise.current = (async () => {
      const refreshToken = localStorage.getItem("refresh_token");
      if (!refreshToken) {
        logout();
        return null;
      }

      try {
        const res = await fetch("http://localhost:8000/api/auth/refresh", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (!res.ok) throw new Error("Refresh failed");

        const data = await res.json();
        setAccessToken(data.access_token);
        return data.access_token;
      } catch (err) {
        logout();
        return null;
      } finally {
        refreshPromise.current = null;
      }
    })();

    return refreshPromise.current;
  }, [logout]);

  const fetchWithAuth = useCallback(async (url: string, options: RequestInit = {}) => {
    let token = tokenRef.current;
    
    // If no token, try to refresh once
    if (!token) {
      token = await refreshAccessToken();
    }

    const headers = {
      ...options.headers,
      Authorization: `Bearer ${token}`,
    };

    try {
      console.log(`[fetchWithAuth] Requesting: ${url}`);
      let res = await fetch(url, { ...options, headers });

      if (res.status === 401) {
        console.log(`[fetchWithAuth] 401 Unauthorized, attempting token refresh...`);
        token = await refreshAccessToken();
        if (token) {
          console.log(`[fetchWithAuth] Refresh successful, retrying...`);
          res = await fetch(url, {
            ...options,
            headers: { ...options.headers, Authorization: `Bearer ${token}` },
          });
        }
      }
      return res;
    } catch (err) {
      console.error(`[fetchWithAuth] Network error for ${url}:`, err);
      return new Response(JSON.stringify({ detail: "Network error" }), {
        status: 503,
        headers: { "Content-Type": "application/json" },
      });
    }
  }, [refreshAccessToken]); // accessToken removed from dependencies!

  const login = useCallback(async (username: string, password: string) => {
    const res = await fetch("http://localhost:8000/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Login failed");
    }

    const data = await res.json();
    setUser(data.user);
    setAccessToken(data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    router.push("/");
  }, [router]);

  const hasInited = React.useRef(false);
  useEffect(() => {
    if (hasInited.current) return;
    hasInited.current = true;

    const initAuth = async () => {
      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) {
        const token = await refreshAccessToken();
        if (token) {
          // Fetch user info
          try {
            const res = await fetch("http://localhost:8000/api/auth/me", {
              headers: { Authorization: `Bearer ${token}` },
            });
            if (res.ok) {
              const userData = await res.json();
              setUser(userData);
            }
          } catch (err) {
            console.error("Failed to fetch user", err);
          }
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, [refreshAccessToken]);

  // Route protection
  useEffect(() => {
    if (!isLoading) {
      if (!user && pathname !== "/login") {
        router.push("/login");
      } else if (user && user.role !== "ADMIN" && pathname.startsWith("/admin")) {
        router.push("/");
      }
    }
  }, [user, isLoading, pathname, router]);

  const value = React.useMemo(() => ({
    user,
    accessToken,
    login,
    logout,
    isLoading,
    fetchWithAuth
  }), [user, accessToken, login, logout, isLoading, fetchWithAuth]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
