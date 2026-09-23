import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../api.js";
import GoogleAuthButton from "../components/GoogleAuthButton.jsx";
import { useAuth } from "../auth.js";

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
    navigate("/animals", { replace: true });
  }

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (form.password !== form.confirm) {
      setError("Passwords do not match");
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
        <h1 className="h1">{t("auth.register")}</h1>
        <p className="sub">{t("auth.registerSub")}</p>
        <form onSubmit={submit}>
          <div className="field">
            <label>{t("auth.username")}</label>
            <input
              className="input"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              minLength={3}
              required
            />
          </div>
          <div className="field">
            <label>{t("auth.email")}</label>
            <input
              className="input"
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
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
              minLength={6}
              required
            />
          </div>
          <div className="field">
            <label>{t("auth.confirmPassword")}</label>
            <input
              className="input"
              type="password"
              value={form.confirm}
              onChange={(e) => setForm({ ...form, confirm: e.target.value })}
              minLength={6}
              required
            />
          </div>
          {error && <p className="formerr">{error}</p>}
          <button className="btn primary" style={{ width: "100%" }} disabled={busy}>
            {busy ? "…" : t("auth.register")}
          </button>
        </form>
        <div className="divider" style={{ margin: "18px 0" }}>{t("auth.or")}</div>
        <GoogleAuthButton onSuccess={afterAuth} onError={setError} />
        <p className="sub" style={{ marginTop: 14 }}>
          {t("auth.haveAccount")} <Link to="/login">{t("auth.logIn")}</Link>
        </p>
      </div>
    </div>
  );
}