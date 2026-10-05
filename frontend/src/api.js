import i18n from "./i18n.js";
import { localizeApiError } from "./apiErrors.js";

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

// The session token and the UI language, on every request. X-Locale lets
// the backend localize DB-driven content (lessons, vocab meanings,
// missions, ...) the same way the UI chrome already follows i18n.language
// — one header, every request, no per-call plumbing. "en" is the
// fallback default anyway, so it's harmless to always send it.
function sessionHeaders(extra = {}) {
  const headers = { ...extra };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (i18n.language) headers["X-Locale"] = i18n.language;
  return headers;
}

async function request(method, path, body) {
  const options = { method, headers: sessionHeaders() };
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
    const message = localizeApiError(detail, res.status);
    if (res.status === 401) clearSession();
    const err = new Error(message);
    // Some endpoints (duels) add a stable machine code next to `detail` so
    // the page can show the message in the learner's language.
    err.status = res.status;
    if (data && typeof data.code === "string") err.code = data.code;
    err.data = data; // the whole body (e.g. an exam's attempt_id / result)
    throw err;
  }
  return data;
}

async function upload(method, path, file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}${path}`, { method, headers: sessionHeaders(), body: form });
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const detail = data && data.detail;
    if (res.status === 401) clearSession();
    throw new Error(localizeApiError(detail, res.status));
  }
  return data;
}

// POST a JSON body and read a newline-delimited JSON response as it
// arrives, calling onEvent(event) per line (the assistant's streamed reply).
// `signal` (an AbortController's) stops it: fetch rejects with an AbortError,
// which the caller treats as "stopped", not as a failure.
async function stream(path, body, { signal, onEvent }) {
  const headers = sessionHeaders({ "Content-Type": "application/json" });
  const res = await fetch(`${API_BASE}${path}`, { method: "POST", headers, body: JSON.stringify(body), signal });
  if (!res.ok) {
    let data = null;
    try {
      data = await res.json();
    } catch {
      data = null;
    }
    if (res.status === 401) clearSession();
    const err = new Error(localizeApiError(data && data.detail, res.status));
    err.status = res.status;
    throw err;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let nl;
    while ((nl = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, nl).trim();
      buffer = buffer.slice(nl + 1);
      if (line) onEvent(JSON.parse(line));
    }
  }
  if (buffer.trim()) onEvent(JSON.parse(buffer));
}

// A POST that outlives the page (reload, close, navigation): keepalive
// instead of sendBeacon, which cannot carry the auth header. Never throws;
// resolves to the JSON body, or null when the request failed or the page
// was already gone. Used for the exam's integrity reports.
function beacon(path, body) {
  return fetch(`${API_BASE}${path}`, {
    method: "POST",
    keepalive: true,
    headers: sessionHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  })
    .then((r) => (r.ok ? r.json() : null))
    .catch(() => null);
}

export const api = {
  get: (path) => request("GET", path),
  post: (path, body) => request("POST", path, body),
  put: (path, body) => request("PUT", path, body),
  patch: (path, body) => request("PATCH", path, body),
  del: (path) => request("DELETE", path),
  // multipart/form-data upload — deliberately not funneled through
  // request() above, which always JSON-encodes the body.
  upload: (path, file) => upload("POST", path, file),
  stream: (path, body, options) => stream(path, body, options),
  beacon: (path, body) => beacon(path, body),
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

export async function loginWithGoogle(credential) {
  const data = await request("POST", "/auth/google", { credential });
  saveToken(data.access_token);
  saveUser(data.user);
  return data.user;
}