import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { checkResetLink, resetPassword } from "../api.js";
import { useAuth } from "../auth.js";
import AuthCardTools from "../components/AuthCardTools.jsx";
import { Loading } from "../components/ui.jsx";

// /reset-password#token=...: the link from the "forgot password" email.
// The token is in the fragment, which browsers never send to a server, and
// it is taken out of the address bar as soon as the page has read it, so it
// doesn't stay in the history or end up in a screenshot. The link is
// checked first, so an expired one says so before anything is typed.

function readToken() {
  const hash = typeof window === "undefined" ? "" : window.location.hash;
  return new URLSearchParams(hash.replace(/^#/, "")).get("token") || "";
}

// The same rules the server applies (services/password_reset.py); keys in
// apiErrors.*, the sentences the server's answer would show.
function problem({ next, confirm }) {
  if (next.length < 6) return "passwordTooShort";
  if (next.length > 128) return "passwordTooLong";
  if (next !== confirm) return "newPasswordMismatch";
  return null;
}

export default function ResetPassword() {
  const { t } = useTranslation();
  const { setCurrentUser } = useAuth();
  const navigate = useNavigate();
  const [token] = useState(readToken);
  const [state, setState] = useState(token ? "checking" : "bad"); // checking | bad | form | saving | done
  const [badMessage, setBadMessage] = useState(token ? "" : null);
  const [pw, setPw] = useState({ next: "", confirm: "" });
  const [error, setError] = useState(null); // { key } | { text }
  const [user, setUser] = useState(null);

  useEffect(() => {
    if (window.location.hash) {
      window.history.replaceState(null, "", window.location.pathname);
    }
    if (!token) return;
    let cancelled = false;
    checkResetLink(token)
      .then(() => !cancelled && setState("form"))
      .catch((err) => {
        if (cancelled) return;
        setBadMessage(err.message);
        setState("bad");
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function submit(e) {
    e.preventDefault();
    if (state === "saving") return;
    const key = problem(pw);
    if (key) {
      setError({ key });
      return;
    }
    setError(null);
    setState("saving");
    try {
      const signedIn = await resetPassword(token, pw);
      setPw({ next: "", confirm: "" });
      setUser(signedIn);
      setState("done");
    } catch (err) {
      // An expired or used link can't be retried; a refused password can.
      if (err.status === 400) {
        setBadMessage(err.message);
        setState("bad");
      } else {
        setError({ text: err.message });
        setState("form");
      }
    }
  }

  function enter() {
    setCurrentUser(user);
    navigate(user?.onboarding_completed ? "/dashboard" : "/onboarding", { replace: true });
  }

  let body;
  if (state === "checking") {
    body = <Loading>{t("auth.resetChecking")}</Loading>;
  } else if (state === "bad") {
    body = (
      <>
        <h1 className="h1">{t("auth.resetBadTitle")}</h1>
        <p className="sub" role="alert">{badMessage || t("auth.resetNoToken")}</p>
        <Link to="/forgot-password" className="btn primary auth-wide-btn">{t("auth.resetNewLink")}</Link>
        <Link to="/login" className="btn ghost auth-wide-btn">{t("auth.backToLogin")}</Link>
      </>
    );
  } else if (state === "done") {
    body = (
      <>
        <h1 className="h1">{t("auth.resetDoneTitle")}</h1>
        <p className="sub" role="status">{t("auth.resetDone")}</p>
        <button type="button" className="btn primary auth-wide-btn" onClick={enter}>
          {t("auth.resetContinue")}
        </button>
      </>
    );
  } else {
    body = (
      <>
        <h1 className="h1">{t("auth.resetTitle")}</h1>
        <p className="sub">{t("auth.resetSub")}</p>
        <form onSubmit={submit} noValidate>
          <div className="field">
            <label htmlFor="reset-new">{t("settings.newPassword")}</label>
            <input
              id="reset-new"
              className="input"
              type="password"
              autoComplete="new-password"
              maxLength={128}
              value={pw.next}
              onChange={(e) => setPw({ ...pw, next: e.target.value })}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="reset-confirm">{t("settings.confirmNewPassword")}</label>
            <input
              id="reset-confirm"
              className="input"
              type="password"
              autoComplete="new-password"
              maxLength={128}
              value={pw.confirm}
              onChange={(e) => setPw({ ...pw, confirm: e.target.value })}
              required
            />
          </div>
          {error && (
            <p className="formerr" role="alert">{error.key ? t(`apiErrors.${error.key}`) : error.text}</p>
          )}
          <button
            type="submit"
            className="btn primary"
            style={{ width: "100%" }}
            disabled={state === "saving"}
            aria-busy={state === "saving" || undefined}
          >
            {state === "saving" ? t("auth.resetSaving") : t("auth.resetSubmit")}
          </button>
        </form>
      </>
    );
  }

  return (
    <div className="page">
      <div className="card formcard">
        <AuthCardTools />
        {body}
      </div>
    </div>
  );
}
