const API_BASE = "/api";
const TOKEN_KEY = "linguaverse_token";
const USER_KEY = "linguaverse_user";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getSavedUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY));
  } catch {
    return null;
  }
}

export function saveToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
}

export function saveUser(user) {
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

async function request(method, path, body) {
  const options = { method, headers: {} };
  const token = getToken();
  if (token) options.headers["Authorization"] = `Bearer ${token}`;
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const res = await fetch(`${API_BASE}${path}`, options);
  if (res.status === 204) return null;
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const detail = data && data.detail;
    const message =
      typeof detail === "string" ? detail : `Request failed (${res.status})`;
    if (res.status === 401) clearSession();
    throw new Error(message);
  }
  return data;
}

export const api = {
  get: (path) => request("GET", path),
  post: (path, body) => request("POST", path, body),
  put: (path, body) => request("PUT", path, body),
  patch: (path, body) => request("PATCH", path, body),
  del: (path) => request("DELETE", path),
};

export async function register(payload) {
  const data = await request("POST", "/auth/register", payload);
  saveToken(data.access_token);
  saveUser(data.user);
  return data.user;
}

export async function login(payload) {
  const data = await request("POST", "/auth/login", payload);
  saveToken(data.access_token);
  saveUser(data.user);
  return data.user;
}