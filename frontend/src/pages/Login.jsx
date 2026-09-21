import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { login } from "../api.js";
import { useAuth } from "../auth.js";

export default function Login() {
  const { setCurrentUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const user = await login({
        username: form.username,
        password: form.password,
      });
      setCurrentUser(user);
      let dest = location.state?.from?.pathname;
      // Skip onboarding gates on fresh login: /dashboard is the hub.
      if (!dest || dest === "/login") dest = "/dashboard";
      navigate(dest, { replace: true });
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <div className="card formcard">
        <h1 className="h1">Welcome back</h1>
        <p className="sub">Your companion missed you.</p>
        <form onSubmit={submit}>
          <div className="field">
            <label>Username</label>
            <input
              className="input"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              required
            />
          </div>
          <div className="field">
            <label>Password</label>
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
            {busy ? "Logging in…" : "Log in"}
          </button>
        </form>
        <p className="sub" style={{ marginTop: 14 }}>
          New here? <Link to="/register">Create an account</Link>
        </p>
      </div>
    </div>
  );
}