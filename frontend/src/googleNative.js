// Google sign-in inside the Android app. Google refuses its web sign-in in an
// embedded WebView ("disallowed_useragent"), so the app asks Android itself:
// Credential Manager (through @capgo/capacitor-social-login) shows the
// phone's own Google account picker and returns an ID token. That token goes
// to the same POST /api/auth/google as the website's, which verifies it
// (routers/auth.py) -- nothing about accounts or sessions differs.
//
// The token is requested for the server's WEB client id (Credential
// Manager's serverClientId), so its audience is exactly the one the backend
// already checks. Google only issues it if an Android OAuth client with this
// app's package name and signing-certificate SHA-1 exists in the same Google
// Cloud project (docs/MOBILE_APP.md); no client secret is involved.

// One initialize() per client id: the plugin keeps it for the app's life.
let initializedFor = null;

async function plugin() {
  // Loaded only in the app, so the website's bundle never carries it.
  const { SocialLogin } = await import("@capgo/capacitor-social-login");
  return SocialLogin;
}

// The ID token for the Google account the learner picks. Rejects with an
// Error whose `reason` is one of GOOGLE_NATIVE_REASONS.
export async function nativeGoogleCredential(clientId) {
  if (!clientId) throw reasonError("notConfigured");
  if (typeof navigator !== "undefined" && navigator.onLine === false) throw reasonError("network");
  try {
    const SocialLogin = await plugin();
    if (initializedFor !== clientId) {
      await SocialLogin.initialize({ google: { webClientId: clientId, mode: "online" } });
      initializedFor = clientId;
    }
    const res = await SocialLogin.login({ provider: "google", options: {} });
    const idToken = res?.result?.idToken;
    if (!idToken) throw reasonError("failed");
    return idToken;
  } catch (err) {
    if (err?.reason) throw err;
    throw reasonError(nativeGoogleReason(err), err);
  }
}

export const GOOGLE_NATIVE_REASONS = ["cancelled", "noAccount", "network", "notConfigured", "failed"];

// What went wrong, from the plugin's rejection (GoogleProvider.java's
// messages, which wrap Android's Credential Manager exceptions).
export function nativeGoogleReason(err) {
  const code = String(err?.code || "");
  const msg = String(err?.message || err || "");
  if (code === "USER_CANCELLED" || /cancel/i.test(msg)) return "cancelled";
  // Google Cloud has no Android client for this package + signing SHA-1
  // (or it's in another project than the web client id): status 10 /
  // 28444 "Developer console is not set up correctly".
  if (/not configured for this installed build|developer console|28444|\b10:|client id is not set/i.test(msg)) {
    return "notConfigured";
  }
  if (/network|timeout|timed out|unreachable|offline|\b7:/i.test(msg)) return "network";
  // NoCredentialException: no Google account on the phone (or none it may use).
  if (/no credential|no google accounts|no viable credential/i.test(msg)) return "noAccount";
  return "failed";
}

function reasonError(reason, cause) {
  const err = new Error(reason);
  err.reason = reason;
  if (cause) err.cause = cause;
  return err;
}
