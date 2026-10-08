import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { githubStartUrl } from "../api.js";

// GitHub's mark, drawn from the brand's published path. It is a logo, not
// a UI icon, so it lives here (filled, like the "G" Google's own button
// draws) rather than in Icon.jsx's line-icon set.
const GITHUB_MARK =
  "M12 .3a12 12 0 0 0-3.8 23.4c.6.1.8-.3.8-.6v-2c-3.3.7-4-1.6-4-1.6-.6-1.4-1.4-1.8-1.4-1.8-1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.8 1.3 3.5 1 0-.8.4-1.3.7-1.6-2.7-.3-5.5-1.3-5.5-6 0-1.2.5-2.3 1.3-3.1-.2-.4-.6-1.6 0-3.2 0 0 1-.3 3.4 1.2a11.5 11.5 0 0 1 6 0C17.3 4.6 18.3 5 18.3 5c.7 1.6.2 2.9.1 3.2.8.8 1.3 1.9 1.3 3.2 0 4.6-2.8 5.6-5.5 5.9.5.4.9 1 .9 2.2v3.3c0 .3.1.7.8.6A12 12 0 0 0 12 .3";

// "Continue with GitHub": a plain link to the backend, which runs the whole
// OAuth flow (routers/auth.py). A link -- not a popup or a fetch -- because
// the browser has to leave for github.com and come back: it works with the
// keyboard, can't be popup-blocked and needs no window.opener, the same in
// every browser.
export default function GitHubAuthButton({ page, available }) {
  const { t } = useTranslation();
  const [leaving, setLeaving] = useState(false);

  // Back from GitHub's page, Firefox and Safari restore this page from their
  // back/forward cache exactly as it was left -- "Redirecting…" and
  // disabled. A restored page gets its button back.
  useEffect(() => {
    function onShow(e) {
      if (e.persisted) setLeaving(false);
    }
    window.addEventListener("pageshow", onShow);
    return () => window.removeEventListener("pageshow", onShow);
  }, []);

  // A server without a GitHub app can't complete the sign-in: offer nothing
  // rather than a button that fails, or a setup note meant for the operator.
  if (available === false) return null;

  function onClick(e) {
    // One flow at a time: a second click would start a second state and
    // make the first come back as a mismatch.
    if (leaving) {
      e.preventDefault();
      return;
    }
    setLeaving(true);
  }

  return (
    <a
      className="btn oauth-btn"
      href={githubStartUrl(page)}
      onClick={onClick}
      aria-disabled={leaving || undefined}
      aria-busy={leaving || undefined}
    >
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">
        <path fill="currentColor" d={GITHUB_MARK} />
      </svg>
      <span>{leaving ? t("auth.githubRedirecting") : t("auth.continueGithub")}</span>
    </a>
  );
}
