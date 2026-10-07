import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { completeGitHubSignIn, getSavedUser, getToken } from "../api.js";
import { useAuth } from "../auth.js";
import { Loading } from "../components/ui.jsx";

// The ticket works once (the backend clears its cookie), so the swap must
// happen once per arrival even though React's StrictMode runs effects
// twice in development: both runs share this one request.
let pending = null;

function exchangeOnce() {
  if (!pending) {
    pending = completeGitHubSignIn().finally(() => {
      pending = null;
    });
  }
  return pending;
}

// Where the backend sends the browser after a successful GitHub callback
// (routers/auth.py). It turns the one-time ticket into the normal session
// and opens onboarding or the app -- the server's onboarding flag decides,
// exactly as after a password or Google sign-in.
export default function GitHubCallback() {
  const { t } = useTranslation();
  const { setCurrentUser } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    exchangeOnce()
      .then((user) => {
        if (cancelled) return;
        setCurrentUser(user);
        navigate(user.onboarding_completed ? "/dashboard" : "/onboarding", { replace: true });
      })
      .catch((err) => {
        if (cancelled) return;
        // Reloaded after it already worked (the ticket is spent): the
        // session from the first time is still here, so just go in.
        const saved = getToken() && getSavedUser();
        if (saved) {
          navigate(saved.onboarding_completed ? "/dashboard" : "/onboarding", { replace: true });
          return;
        }
        setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="page">
      <div className="card formcard center" role={error ? "alert" : "status"}>
        {error ? (
          <>
            <h1 className="h1">{t("auth.githubFailedTitle")}</h1>
            <p className="formerr">{error}</p>
            <Link to="/login" className="btn primary" replace>
              {t("auth.backToLogin")}
            </Link>
          </>
        ) : (
          <Loading>{t("auth.githubCompleting")}</Loading>
        )}
      </div>
    </div>
  );
}
