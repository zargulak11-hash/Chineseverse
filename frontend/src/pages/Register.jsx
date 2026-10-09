import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../api.js";
import SocialAuth from "../components/SocialAuth.jsx";
import { useAuth } from "../auth.js";
import LanguagePicker from "../components/LanguagePicker.jsx";

export default function Register() {
  const { t } = useTranslation();
  const { setCurrentUser } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    confirm: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function afterAuth(user) {
    setCurrentUser(user);
    // "Continue with Google" here can also sign in an existing, already
    // onboarded account -- that one goes straight into the app. (GitHub
    // finishes on /auth/github, which applies the same rule.)
    navigate(user.onboarding_completed ? "/dashboard" : "/onboarding", { replace: true });
  }

  async function submit(e) {
    e.preventDefault();
    if (busy) return;
    setError("");
    if (form.password !== form.confirm) {
      setError(t("auth.passwordMismatch"));
      return;
    }
    setBusy(true);
    try {
      const user = await register({
        username: form.username,
        email: form.email,
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
        <div className="formcard-tools"><LanguagePicker /></div>
        <h1 className="h1">{t("auth.register")}</h1>
        <p className="sub">{t("auth.registerSub")}</p>
        <form onSubmit={submit}>
          <div className="field">
            <label htmlFor="reg-username">{t("auth.username")}</label>
            <input
              id="reg-username"
              autoComplete="username"
              className="input"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              minLength={3}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="reg-email">{t("auth.email")}</label>
            <input
              id="reg-email"
              autoComplete="email"
              className="input"
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="reg-password">{t("auth.password")}</label>
            <input
              id="reg-password"
              autoComplete="new-password"
              className="input"
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              minLength={6}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="reg-confirm">{t("auth.confirmPassword")}</label>
            <input
              id="reg-confirm"
              autoComplete="new-password"
              className="input"
              type="password"
              value={form.confirm}
              onChange={(e) => setForm({ ...form, confirm: e.target.value })}
              minLength={6}
              required
            />
          </div>
          {error && <p className="formerr">{error}</p>}
          <button type="submit" className="btn primary" style={{ width: "100%" }} disabled={busy} aria-busy={busy || undefined}>
            {busy ? t("auth.creatingAccount") : t("auth.register")}
          </button>
        </form>
        <SocialAuth page="register" onSuccess={afterAuth} onError={setError} />
        <p className="sub" style={{ marginTop: 14 }}>
          {t("auth.haveAccount")} <Link to="/login">{t("auth.logIn")}</Link>
        </p>
      </div>
    </div>
  );
}