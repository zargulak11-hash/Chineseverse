import { useEffect, useRef, useState } from "react";
import { loginWithGoogle } from "../api.js";

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

// Renders Google's own "Continue with Google" button via Google Identity
// Services and exchanges the resulting ID token with our backend, which
// verifies it and issues our own session token. No credentials are ever
// invented here — if VITE_GOOGLE_CLIENT_ID isn't set, we say so instead of
// showing a decorative button that would silently fail.
export default function GoogleAuthButton({ onSuccess, onError }) {
  const divRef = useRef(null);
  const [ready, setReady] = useState(false);

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
          try {
            const user = await loginWithGoogle(response.credential);
            onSuccess?.(user);
          } catch (err) {
            onError?.(err.message);
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
      timeout = setTimeout(() => clearInterval(poll), 8000);
    }

    return () => {
      cancelled = true;
      clearInterval(poll);
      clearTimeout(timeout);
    };
  }, [onSuccess, onError]);

  if (!CLIENT_ID) {
    return (
      <p className="sub" style={{ opacity: 0.6, fontSize: 12 }}>
        Google Sign-In isn't configured for this deployment yet.
      </p>
    );
  }

  return (
    <div className="center" style={{ display: "flex", justifyContent: "center" }}>
      <div ref={divRef} />
      {!ready && <p className="sub" style={{ fontSize: 12 }}>Loading Google Sign-In…</p>}
    </div>
  );
}
