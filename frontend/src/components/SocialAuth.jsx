import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { api } from "../api.js";
import GitHubAuthButton from "./GitHubAuthButton.jsx";
import GoogleAuthButton from "./GoogleAuthButton.jsx";

// Reasons the backend's GitHub callback can send a learner back with
// (?auth_error=..., routers/auth.py); anything else gets the generic one.
const OAUTH_ERRORS = new Set([
  "github_cancelled",
  "github_failed",
  "github_state",
  "github_code",
  "github_no_email",
  "github_unreachable",
  "github_not_configured",
  "github_other_account",
  "deactivated",
]);

// The "or continue with" block shared by Login and Register, so both pages
// offer the same providers with the same behaviour. `page` is where a
// GitHub failure returns to; `onSuccess(user)` runs after a Google sign-in
// (GitHub finishes on /auth/github instead, see GitHubCallback.jsx).
export default function SocialAuth({ page, onSuccess, onError }) {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [providers, setProviders] = useState(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get("/auth/providers")
      .then((p) => !cancelled && setProviders(p))
      // Unknown: keep the buttons; the backend still answers a sign-in it
      // can't complete with a clear reason.
      .catch(() => !cancelled && setProviders(null));
    return () => {
      cancelled = true;
    };
  }, []);

  // A GitHub round trip that failed comes back here with a reason: show it
  // in the learner's language, then drop it from the address bar so a
  // refresh or a shared link doesn't show it again.
  const authError = searchParams.get("auth_error");
  useEffect(() => {
    if (!authError) return;
    onError?.(t(`auth.oauthErrors.${OAUTH_ERRORS.has(authError) ? authError : "unknown"}`));
    const next = new URLSearchParams(searchParams);
    next.delete("auth_error");
    setSearchParams(next, { replace: true });
  }, [authError]);

  return (
    <div className="social-auth">
      <div className="divider">{t("auth.or")}</div>
      <GoogleAuthButton onSuccess={onSuccess} onError={onError} />
      <GitHubAuthButton page={page} available={providers ? providers.github : undefined} />
    </div>
  );
}
