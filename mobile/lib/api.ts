/**
 * Minimal API client for the Wayfara Django backend.
 * Base URL comes from app config (extra.apiUrl) so dev/prod can differ.
 */
import Constants from "expo-constants";

const API_URL: string =
  (Constants.expoConfig?.extra?.apiUrl as string | undefined) ??
  "http://localhost:8000";

export interface Tokens {
  access: string;
  refresh: string;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

export function register(email: string, password: string) {
  return request<{ email: string }>("/api/auth/register/", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function login(email: string, password: string) {
  return request<Tokens>("/api/auth/token/", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function getProfile(access: string) {
  return request("/api/profile/", {
    headers: { Authorization: `Bearer ${access}` },
  });
}
