import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { loginWithGoogle } from "../api.js";

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

// Renders Google's own "Continue with Google" button via Google Identity
// Services and exchanges the resulting ID token with our backend, which
// verifies it and issues our own session token. No credentials are ever
// invented here — if VITE_GOOGLE_CLIENT_ID isn't set, there is no button
// rather than a decorative one that would silently fail.
export const GOOGLE_CONFIGURED = Boolean(CLIENT_ID);

export default function GoogleAuthButton({ onSuccess, onError }) {
  const { t, i18n } = useTranslation();
  // Google's button speaks the browser's language unless told otherwise;
  // drawing reads the current UI language each time.
  const langRef = useRef(i18n.language);
  langRef.current = i18n.language;
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
    let redraw;
    let resizeObserver;

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
      draw();
      setReady(true);
      // Google draws the button at a fixed pixel width, so it is redrawn
      // when the card's width changes (a phone rotated, a window narrowed):
      // drawn once at 400px, it ran 40px off a 360px screen.
      const box = divRef.current.parentElement;
      if (box && "ResizeObserver" in window) {
        let last = box.clientWidth;
        resizeObserver = new ResizeObserver(() => {
          if (Math.abs(box.clientWidth - last) < 8) return;
          last = box.clientWidth;
          clearTimeout(redraw);
          redraw = setTimeout(draw, 150);
        });
        resizeObserver.observe(box);
      }
    }

    // Google's limits are 200-400px; inside them, the card's own width.
    function draw() {
      if (cancelled || !divRef.current) return;
      const room = divRef.current.parentElement?.clientWidth || 320;
      window.google.accounts.id.renderButton(divRef.current, {
        theme: "filled_black",
        size: "large",
        shape: "pill",
        width: Math.max(200, Math.min(400, Math.floor(room))),
        text: "continue_with",
        locale: langRef.current,
      });
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
      clearTimeout(redraw);
      resizeObserver?.disconnect();
    };
  }, []);

  // Not configured for this build: no button rather than a setup note
  // meant for the operator (SocialAuth drops the "or" too).
  if (!CLIENT_ID) return null;

  return (
    <div className="google-auth">
      <div ref={divRef} />
      {!ready && (
        <p className="sub" style={{ fontSize: "var(--text-xs)" }}>
          {t(unavailable ? "ui.googleUnavailable" : "ui.googleLoading")}
        </p>
      )}
    </div>
  );
}
