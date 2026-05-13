// api.js — All backend calls in one place.
// Base URL is injected from Vite env, falls back to empty string for k8s.

const BASE = import.meta.env.VITE_API_URL ?? "";

// ---------------------------------------------------------------------------
// Token management
// In-memory storage — avoids localStorage which isn't available in all envs.
// The token is lost on page refresh, which is acceptable for this app.
// ---------------------------------------------------------------------------
let _token = null;

export const setToken = (token) => { _token = token; };
export const getToken = () => _token;
export const clearToken = () => { _token = null; };
export const isAuthenticated = () => _token !== null;

// ---------------------------------------------------------------------------
// Core request helper
// ---------------------------------------------------------------------------
async function request(method, path, body, requiresAuth = false) {
  const headers = { "Content-Type": "application/json" };

  if (_token) {
    headers["Authorization"] = `Bearer ${_token}`;
  } else if (requiresAuth) {
    throw new Error("Not authenticated.");
  }

  const res = await fetch(`${BASE}/api${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Unknown error");
  }

  if (res.status === 204) return null;
  return res.json();
}

// Form-encoded request helper — used for OAuth2 login
async function requestForm(path, formData) {
  const res = await fetch(`${BASE}/api${path}`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Unknown error");
  }

  return res.json();
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------
export const register = (email, password) =>
  request("POST", "/auth/register", { email, password });

export const login = async (email, password) => {
  // OAuth2PasswordRequestForm expects form-encoded data, not JSON
  const formData = new FormData();
  formData.append("username", email); // OAuth2 spec uses "username"
  formData.append("password", password);
  return requestForm("/auth/login", formData);
};

export const getMe = () =>
  request("GET", "/auth/me", null, true);

// ---------------------------------------------------------------------------
// Pokemon
// ---------------------------------------------------------------------------
export const listPokemon = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return request("GET", `/pokemon${qs ? `?${qs}` : ""}`);
};

// ---------------------------------------------------------------------------
// Sessions
// ---------------------------------------------------------------------------
export const createSession = (filters, targetRemaining) =>
  request("POST", "/sessions", { filters, target_remaining: targetRemaining });

export const getSession = (sessionId) =>
  request("GET", `/sessions/${sessionId}`);

export const abandonSession = (sessionId) =>
  request("DELETE", `/sessions/${sessionId}`);

export const getUserSessions = () =>
  request("GET", "/sessions/history", null, true);

// ---------------------------------------------------------------------------
// Matchups
// ---------------------------------------------------------------------------
export const getNextMatchup = (sessionId) =>
  request("GET", `/sessions/${sessionId}/next`);

export const submitPick = (sessionId, matchupId, winnerId) =>
  request("POST", `/sessions/${sessionId}/matchups/${matchupId}`, {
    winner_id: winnerId,
  });

// ---------------------------------------------------------------------------
// Results
// ---------------------------------------------------------------------------
export const getResults = (sessionId) =>
  request("GET", `/sessions/${sessionId}/results`);