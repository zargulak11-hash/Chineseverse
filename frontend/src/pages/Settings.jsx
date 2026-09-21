import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, clearSession } from "../api.js";
import { useAuth } from "../auth.js";
import Layout from "../components/Layout.jsx";
import { Empty } from "../components/ui.jsx";

export default function Settings() {
  const { user, setCurrentUser } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ native_language: "", goal_text: "", daily_goal_minutes: 20, bio: "" });
  const [ok, setOk] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/me").then((me) => {
      setForm({
        native_language: me.profile.native_language || "",
        goal_text: me.profile.goal_text || "",
        daily_goal_minutes: me.profile.daily_goal_minutes || 20,
        bio: me.profile.bio || "",
      });
    }).catch((e) => setError(e.message));
  }, []);

  async function save() {
    setOk("");
    setError("");
    try {
      const p = await api.patch("/me/profile", form);
      setOk("Profile saved. DNA keeps adapting.");
      const me = await api.get("/me");
      setCurrentUser(me.user);
    } catch (e) {
      setError(e.message);
    }
  }

  function logout() {
    clearSession();
    setCurrentUser(null);
    navigate("/");
  }

  return (
    <Layout>
      <h1 className="h1">Settings</h1>

      <div className="card formcard">
        <h2 className="h2">Learning profile</h2>
        <div className="field">
          <label>Native language</label>
          <input className="input" value={form.native_language}
            onChange={(e) => setForm({ ...form, native_language: e.target.value })} />
        </div>
        <div className="field">
          <label>What do you want to do in Chinese?</label>
          <input className="input" value={form.goal_text}
            onChange={(e) => setForm({ ...form, goal_text: e.target.value })}
            placeholder="e.g. survive a trip to Beijing" />
        </div>
        <div className="field">
          <label>Daily goal (minutes)</label>
          <input className="input" type="number" min={5} max={240} value={form.daily_goal_minutes}
            onChange={(e) => setForm({ ...form, daily_goal_minutes: Number(e.target.value) })} />
        </div>
        <div className="field">
          <label>Bio</label>
          <textarea className="input" rows={2} value={form.bio}
            onChange={(e) => setForm({ ...form, bio: e.target.value })} />
        </div>
        {error && <p className="formerr">{error}</p>}
        {ok && <p className="sub" style={{ color: "var(--good)", marginBottom: 10 }}>{ok}</p>}
        <button className="btn primary" style={{ width: "100%" }} onClick={save}>Save</button>
      </div>

      <div className="card formcard">
        <h2 className="h2">Account</h2>
        <p className="sub" style={{ marginBottom: 12 }}>Signed in as <b>{user?.username}</b></p>
        <button className="btn danger" style={{ width: "100%" }} onClick={logout}>Log out</button>
      </div>
    </Layout>
  );
}