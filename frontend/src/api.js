// api.js — All backend calls in one place.
// Base URL is injected from Vite env, falls back to localhost for dev.

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request(method, path, body) {
  const res = await fetch(`${BASE}/api${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Unknown error");
  }

  if (res.status === 204) return null;
  return res.json();
}

// Pokemon
export const listPokemon = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return request("GET", `/pokemon${qs ? `?${qs}` : ""}`);
};

// Sessions
export const createSession = (filters, targetRemaining) =>
  request("POST", "/sessions", { filters, target_remaining: targetRemaining });

export const getSession = (sessionId) =>
  request("GET", `/sessions/${sessionId}`);

export const abandonSession = (sessionId) =>
  request("DELETE", `/sessions/${sessionId}`);

// Matchups
export const getNextMatchup = (sessionId) =>
  request("GET", `/sessions/${sessionId}/next`);

export const submitPick = (sessionId, matchupId, winnerId) =>
  request("POST", `/sessions/${sessionId}/matchups/${matchupId}`, {
    winner_id: winnerId,
  });

// Results
export const getResults = (sessionId) =>
  request("GET", `/sessions/${sessionId}/results`);
