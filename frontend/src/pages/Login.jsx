import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { login } from "../api.js";
import GoogleAuthButton from "../components/GoogleAuthButton.jsx";
import { useAuth } from "../auth.js";

export default function Login() {
  const { t } = useTranslation();
  const { setCurrentUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function afterAuth(user) {
    setCurrentUser(user);
    // A first Google sign-in creates the account here too: it starts in
    // onboarding like any new account (and so does one that left it unfinished).
    if (!user.onboarding_completed) {
      navigate("/onboarding", { replace: true });
      return;
    }
    // Back to exactly where the learner was sent from -- with its query, so
    // e.g. /real-chinese?place=tea_house reopens that place, not just the page.
    const from = location.state?.from;
    let dest = from?.pathname;
    if (!dest || dest === "/login") dest = "/dashboard";
    else dest += `${from.search || ""}${from.hash || ""}`;
    navigate(dest, { replace: true });
  }

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const user = await login({
        username: form.username,
        password: form.password,
      });
      afterAuth(user);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <div className="card formcard">
        <h1 className="h1">{t("auth.welcomeBack")}</h1>
        <p className="sub">{t("auth.welcomeBackSub")}</p>
        <form onSubmit={submit}>
          <div className="field">
            <label>{t("auth.username")}</label>
            <input
              className="input"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              required
            />
          </div>
          <div className="field">
            <label>{t("auth.password")}</label>
            <input
              className="input"
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
            />
          </div>
          {error && <p className="formerr">{error}</p>}
          <button className="btn primary" style={{ width: "100%" }} disabled={busy}>
            {busy ? "…" : t("auth.logIn")}
          </button>
        </form>
        <div className="divider" style={{ margin: "18px 0" }}>{t("auth.or")}</div>
        <GoogleAuthButton onSuccess={afterAuth} onError={setError} />
        <p className="sub" style={{ marginTop: 14 }}>
          {t("auth.newHere")} <Link to="/register">{t("auth.createAccount")}</Link>
        </p>
      </div>
    </div>
  );
}