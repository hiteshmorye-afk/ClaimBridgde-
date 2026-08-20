import { useEffect, useState } from "react";

const STORAGE_KEY = "claimbridge_demo_user";
const AUTH_CHANGE_EVENT = "claimbridge-auth-change";

export type DemoUser = {
  id: string;
  email: string;
};

function loadDemoUser(): DemoUser | null {
  if (typeof window === "undefined") return null;
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (!stored) return null;
    return JSON.parse(stored) as DemoUser;
  } catch {
    return null;
  }
}

function saveDemoUser(user: DemoUser) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
  window.dispatchEvent(new Event(AUTH_CHANGE_EVENT));
}

function clearDemoUser() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
  window.dispatchEvent(new Event(AUTH_CHANGE_EVENT));
}

export function signInDemoUser(email: string) {
  saveDemoUser({ id: `demo-${Date.now()}`, email });
}

export function signOutDemoUser() {
  clearDemoUser();
}

export function useAuth() {
  const [user, setUser] = useState<DemoUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const updateAuth = () => setUser(loadDemoUser());
    updateAuth();
    window.addEventListener(AUTH_CHANGE_EVENT, updateAuth);
    setLoading(false);
    return () => window.removeEventListener(AUTH_CHANGE_EVENT, updateAuth);
  }, []);

  return { user, loading };
}
