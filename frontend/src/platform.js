import { Capacitor } from "@capacitor/core";

// Where this copy of the app is running: the website (any browser) or the
// Android / iOS app (Capacitor, see capacitor.config.json). The website keeps
// calling its own origin's /api, exactly as before -- nginx (production) and
// Vite (development) proxy it. The app is served from the phone itself
// (https://localhost on Android, capacitor://localhost on iOS), so a relative
// /api would ask the phone; it has to name the real server instead, and the
// backend allows those two origins (config.py: mobile_app_origins).
export const isNativeApp = Capacitor.isNativePlatform();
export const nativePlatform = Capacitor.getPlatform(); // "android" | "ios" | "web"

// Build-time override for testing the app against another server, e.g. a
// laptop on the same Wi-Fi: VITE_MOBILE_API_ORIGIN=http://192.168.1.20:8000
// in frontend/.env.mobile, read by `npm run mobile:sync` (docs/MOBILE_APP.md).
// Unset, the app talks to production.
const MOBILE_API_ORIGIN = (import.meta.env.VITE_MOBILE_API_ORIGIN || "https://chineseverse.qobus.tj").replace(/\/+$/, "");

export const API_ORIGIN = isNativeApp ? MOBILE_API_ORIGIN : "";

// Server-relative files the API hands out (uploaded avatars: "/static/...")
// resolve against the API's origin. On the website that is a no-op.
export function assetUrl(url) {
  if (!url || !API_ORIGIN || !url.startsWith("/") || url.startsWith("//")) return url;
  return `${API_ORIGIN}${url}`;
}
