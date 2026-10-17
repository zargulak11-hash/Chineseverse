import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api, requestPasswordReset } from "../api.js";
import AuthCardTools from "../components/AuthCardTools.jsx";

// /forgot-password: ask for an emailed link to choose a new password
// (services/password_reset.py). The server answers the same for every
// address, so this page does too -- it never says whether an account
// exists. When the server can't send email it says so (503, or
// /auth/providers password_reset: false) instead of pretending to.
export default function ForgotPassword() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [state, setState] = useState("form"); // form | sending | sent | unavailable
  const [sentTo, setSentTo] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .get("/auth/providers")
      .then((p) => !cancelled && p?.password_reset === false && setState("unavailable"))
      // Unknown: keep the form; the request itself still answers honestly.
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  async function submit(e) {
    e.preventDefault();
    if (state === "sending") return;
    setError("");
    setState("sending");
    try {
      await requestPasswordReset(email.trim());
      setSentTo(email.trim());
      setState("sent");
    } catch (err) {
      if (err.status === 503) {
        setState("unavailable");
        return;
      }
      setError(err.message);
      setState("form");
    }
  }

  return (
    <div className="page">
      <div className="card formcard">
        <AuthCardTools />
        {state === "unavailable" ? (
          <>
            <h1 className="h1">{t("auth.forgotUnavailableTitle")}</h1>
            <p className="sub">{t("auth.forgotUnavailable")}</p>
            <Link to="/login" className="btn primary auth-wide-btn">{t("auth.backToLogin")}</Link>
          </>
        ) : state === "sent" ? (
          <>
            <h1 className="h1">{t("auth.forgotSentTitle")}</h1>
            <p className="sub" role="status">{t("auth.forgotSent", { email: sentTo })}</p>
            <Link to="/login" className="btn primary auth-wide-btn">{t("auth.backToLogin")}</Link>
            <button type="button" className="btn ghost auth-wide-btn" onClick={() => setState("form")}>
              {t("auth.forgotAgain")}
            </button>
          </>
        ) : (
          <>
            <h1 className="h1">{t("auth.forgotTitle")}</h1>
            <p className="sub">{t("auth.forgotSub")}</p>
            <form onSubmit={submit}>
              <div className="field">
                <label htmlFor="forgot-email">{t("auth.email")}</label>
                <input
                  id="forgot-email"
                  className="input"
                  type="email"
                  autoComplete="email"
                  autoCapitalize="none"
                  spellCheck={false}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              {error && <p className="formerr" role="alert">{error}</p>}
              <button
                type="submit"
                className="btn primary"
                style={{ width: "100%" }}
                disabled={state === "sending"}
                aria-busy={state === "sending" || undefined}
              >
                {state === "sending" ? t("auth.forgotSending") : t("auth.forgotSubmit")}
              </button>
            </form>
            <p className="sub" style={{ marginTop: 16 }}>
              <Link to="/login">{t("auth.backToLogin")}</Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
