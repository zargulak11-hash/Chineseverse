import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { loginWithGoogle } from "../api.js";
import { nativeGoogleCredential } from "../googleNative.js";

// Google's "G", in its four brand colours as Google's own button draws it.
// A logo, not a UI icon, so it lives here (like GitHubAuthButton's mark)
// rather than in Icon.jsx's line-icon set.
const G_PATHS = [
  ["#4285F4", "M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.4h6.5a5.5 5.5 0 0 1-2.4 3.6v3h3.9c2.2-2.1 3.5-5.1 3.5-8.7z"],
  ["#34A853", "M12 24c3.2 0 6-1.1 8-2.9l-3.9-3c-1.1.7-2.5 1.2-4.1 1.2-3.1 0-5.8-2.1-6.7-5H1.3v3.1A12 12 0 0 0 12 24z"],
  ["#FBBC05", "M5.3 14.3a7.2 7.2 0 0 1 0-4.6V6.6h-4a12 12 0 0 0 0 10.8l4-3.1z"],
  ["#EA4335", "M12 4.8c1.8 0 3.3.6 4.6 1.8l3.4-3.4A12 12 0 0 0 1.3 6.6l4 3.1c.9-2.8 3.6-4.9 6.7-4.9z"],
];

// googleNative.js's failure reasons -> what the learner reads.
const REASON_KEYS = {
  cancelled: "auth.googleAppCancelled",
  noAccount: "auth.googleAppNoAccount",
  network: "auth.googleAppNetwork",
  notConfigured: "auth.googleAppNotConfigured",
  failed: "auth.googleAppFailed",
};

// "Continue with Google" in the Android app: Android's own account picker
// (googleNative.js) instead of Google's web button, which the WebView can't
// run. Same contract as GoogleAuthButton: onSuccess(user) after signing in,
// or onCredential(idToken) to use the token for something else, and
// onError(text) with a sentence in the learner's language. Cancelling the
// picker says so quietly rather than as a failure.
export default function NativeGoogleButton({ clientId, onSuccess, onError, onCredential }) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  // A double tap must not open two pickers or post the token twice.
  const inFlight = useRef(false);

  async function start() {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    try {
      const credential = await nativeGoogleCredential(clientId);
      if (onCredential) {
        await onCredential(credential);
      } else {
        onSuccess?.(await loginWithGoogle(credential));
      }
    } catch (err) {
      // A plugin failure carries a reason; a server answer (api.js) is
      // already a translated sentence.
      onError?.(err?.reason ? t(REASON_KEYS[err.reason] || REASON_KEYS.failed) : err?.message || t(REASON_KEYS.failed));
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      className="btn oauth-btn"
      onClick={start}
      disabled={busy}
      aria-busy={busy || undefined}
    >
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">
        {G_PATHS.map(([fill, d]) => (
          <path key={fill} fill={fill} d={d} />
        ))}
      </svg>
      <span>{busy ? t("auth.googleAppSigningIn") : t("auth.continueGoogle")}</span>
    </button>
  );
}
