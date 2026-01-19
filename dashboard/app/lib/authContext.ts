"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

interface AuthContextType {
  user: any | null;
  loading: boolean;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isClient, setIsClient] = useState(false);
  const [user] = useState({ email: "demo@org", role: "admin" });

  useEffect(() => {
    setIsClient(true);
  }, []);

  const logout = () => {
    console.log("Logout clicked");
  };

  // Provide context value immediately, don't wait for client render
  const value = { user, loading: false, logout };

  return React.createElement(
    AuthContext.Provider,
    { value },
    children
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
