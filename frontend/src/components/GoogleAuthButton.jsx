import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { loginWithGoogle } from "../api.js";

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

// Renders Google's own "Continue with Google" button via Google Identity
// Services and exchanges the resulting ID token with our backend, which
// verifies it and issues our own session token. No credentials are ever
// invented here — if VITE_GOOGLE_CLIENT_ID isn't set, we say so instead of
// showing a decorative button that would silently fail.
export default function GoogleAuthButton({ onSuccess, onError }) {
  const { t } = useTranslation();
  const divRef = useRef(null);
  const [ready, setReady] = useState(false);
  const [unavailable, setUnavailable] = useState(false);
  // Login/Register pass a fresh afterAuth on every render (each keystroke in
  // their forms). With those as effect deps, google.accounts.id.initialize()
  // ran again on every render -- Google documents it as call-once, and a
  // re-initialized client can deliver one sign-in to its callback twice.
  // Holding the handlers in refs lets the effect run once per mount while
  // still calling the latest ones.
  const onSuccessRef = useRef(onSuccess);
  const onErrorRef = useRef(onError);
  onSuccessRef.current = onSuccess;
  onErrorRef.current = onError;
  // One exchange at a time: a duplicate callback for the same click would
  // otherwise race a second POST /auth/google against the first.
  const inFlight = useRef(false);

  useEffect(() => {
    if (!CLIENT_ID) return;
    let cancelled = false;
    let poll;
    let timeout;

    function init() {
      if (cancelled || !window.google?.accounts?.id || !divRef.current) return;
      window.google.accounts.id.initialize({
        client_id: CLIENT_ID,
        callback: async (response) => {
          if (inFlight.current) return;
          inFlight.current = true;
          try {
            const user = await loginWithGoogle(response.credential);
            onSuccessRef.current?.(user);
          } catch (err) {
            onErrorRef.current?.(err.message);
          } finally {
            inFlight.current = false;
          }
        },
      });
      window.google.accounts.id.renderButton(divRef.current, {
        theme: "filled_black",
        size: "large",
        shape: "pill",
        width: 320,
        text: "continue_with",
      });
      setReady(true);
    }

    if (window.google?.accounts?.id) {
      init();
    } else {
      poll = setInterval(() => {
        if (window.google?.accounts?.id) {
          clearInterval(poll);
          init();
        }
      }, 200);
      // The GSI script never arrived (offline, or blocked by a content
      // blocker): say so rather than leaving "Loading…" up forever.
      timeout = setTimeout(() => {
        clearInterval(poll);
        if (!cancelled && !window.google?.accounts?.id) setUnavailable(true);
      }, 8000);
    }

    return () => {
      cancelled = true;
      clearInterval(poll);
      clearTimeout(timeout);
    };
  }, []);

  if (!CLIENT_ID) {
    return (
      <p className="sub" style={{ opacity: 0.6, fontSize: 12 }}>
        {t("ui.googleNotConfigured")}
      </p>
    );
  }

  return (
    <div className="center" style={{ display: "flex", justifyContent: "center" }}>
      <div ref={divRef} />
      {!ready && (
        <p className="sub" style={{ fontSize: "var(--text-xs)" }}>
          {t(unavailable ? "ui.googleUnavailable" : "ui.googleLoading")}
        </p>
      )}
    </div>
  );
}
