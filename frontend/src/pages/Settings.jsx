import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api, clearSession } from "../api.js";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { useAuth } from "../auth.js";
import { useDashboard } from "../context/DashboardContext.jsx";
import { SUPPORTED_LANGS } from "../i18n.js";
import { usePrefs } from "../prefs.jsx";
import { useTheme } from "../theme.jsx";

function Toggle({ checked, onChange, label, hint }) {
  return (
    <label className="row spread toggle-row" style={{ cursor: "pointer" }}>
      <span>
        <b style={{ display: "block" }}>{label}</b>
        {hint && <span className="sub" style={{ fontSize: 12.5 }}>{hint}</span>}
      </span>
      <span className={`switch${checked ? " on" : ""}`} onClick={() => onChange(!checked)}>
        <span className="switch-knob" />
      </span>
    </label>
  );
}

export default function Settings() {
  const { t, i18n } = useTranslation();
  const { user, setCurrentUser } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { soundEnabled, setSoundEnabled, notifEnabled, setNotifEnabled } = usePrefs() || {};
  const { dashboard, refresh } = useDashboard() || {};
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [form, setForm] = useState({ native_language: "", goal_text: "", daily_goal_minutes: 20, bio: "" });
  const [username, setUsername] = useState(user?.username || "");
  const [avatarUrl, setAvatarUrl] = useState(null);
  const [ok, setOk] = useState("");
  const [error, setError] = useState("");
  const [avatarBusy, setAvatarBusy] = useState(false);
  const [avatarError, setAvatarError] = useState("");

  useEffect(() => {
    api
      .get("/me")
      .then((me) => {
        setForm({
          native_language: me.profile.native_language || "",
          goal_text: me.profile.goal_text || "",
          daily_goal_minutes: me.profile.daily_goal_minutes || 20,
          bio: me.profile.bio || "",
        });
        setAvatarUrl(me.profile.avatar_url || null);
      })
      .catch((e) => setError(e.message));
  }, []);

  async function save() {
    setOk("");
    setError("");
    try {
      if (username && username !== user?.username) {
        const updatedUser = await api.patch("/me/account", { username });
        setCurrentUser(updatedUser);
      }
      await api.patch("/me/profile", form);
      setOk(t("settings.saved"));
      const me = await api.get("/me");
      setCurrentUser(me.user);
      refresh?.();
    } catch (e) {
      setError(e.message);
    }
  }

  async function onPickAvatar(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setAvatarBusy(true);
    setAvatarError("");
    try {
      const profile = await api.upload("/me/avatar", file);
      setAvatarUrl(profile.avatar_url);
      refresh?.();
    } catch (err) {
      setAvatarError(err.message);
    } finally {
      setAvatarBusy(false);
    }
  }

  async function removeAvatar() {
    setAvatarBusy(true);
    setAvatarError("");
    try {
      const profile = await api.del("/me/avatar");
      setAvatarUrl(profile.avatar_url);
      refresh?.();
    } catch (err) {
      setAvatarError(err.message);
    } finally {
      setAvatarBusy(false);
    }
  }

  function logout() {
    clearSession();
    setCurrentUser(null);
    navigate("/");
  }

  const animalSlug = dashboard?.animal?.slug;

  return (
    <Layout>
      <h1 className="h1">{t("settings.title")}</h1>

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", marginTop: 18, alignItems: "start" }}>
        <div className="col">
          <div className="card">
            <h2 className="h2">{t("settings.appearance")}</h2>
            <div className="field">
              <label>{t("settings.theme")}</label>
              <div className="row" style={{ marginTop: 4 }}>
                <button
                  type="button"
                  className={`btn small${theme === "ink" ? " primary" : " ghost"}`}
                  onClick={() => theme !== "ink" && toggleTheme()}
                >
                  <Icon name="droplet" size={13} /> {t("settings.themeInk")}
                </button>
                <button
                  type="button"
                  className={`btn small${theme === "paper" ? " primary" : " ghost"}`}
                  onClick={() => theme !== "paper" && toggleTheme()}
                >
                  <Icon name="droplet" size={13} /> {t("settings.themePaper")}
                </button>
              </div>
            </div>
            <div className="field">
              <label>{t("settings.language")}</label>
              <div className="row" style={{ marginTop: 4 }}>
                {SUPPORTED_LANGS.map((l) => (
                  <button
                    key={l.code}
                    type="button"
                    className={`btn small${i18n.language === l.code ? " primary" : " ghost"}`}
                    onClick={() => i18n.changeLanguage(l.code)}
                  >
                    {l.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="card" style={{ marginTop: 16 }}>
            <h2 className="h2">{t("settings.profilePicture")}</h2>
            <div className="row" style={{ marginTop: 10 }}>
              {avatarUrl ? (
                <img src={avatarUrl} alt="" className="avatar-preview" />
              ) : animalSlug ? (
                <AnimalAvatar slug={animalSlug} size={64} />
              ) : (
                <span className="sidebar-profile-fallback" style={{ width: 64, height: 64 }}>
                  <Icon name="user" size={26} />
                </span>
              )}
              <div className="col" style={{ gap: 8 }}>
                <div className="row">
                  <button
                    type="button"
                    className="btn small"
                    disabled={avatarBusy}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    {t("settings.uploadPhoto")}
                  </button>
                  {avatarUrl && (
                    <button type="button" className="btn small ghost" disabled={avatarBusy} onClick={removeAvatar}>
                      {t("settings.removePhoto")}
                    </button>
                  )}
                </div>
                <span className="sub" style={{ fontSize: 11.5 }}>{t("settings.uploadHint")}</span>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                style={{ display: "none" }}
                onChange={onPickAvatar}
              />
            </div>
            {avatarError && <p className="formerr">{avatarError}</p>}
          </div>

          <div className="card" style={{ marginTop: 16 }}>
            <h2 className="h2">{t("settings.preferences")}</h2>
            <Toggle
              checked={soundEnabled !== false}
              onChange={setSoundEnabled}
              label={t("settings.soundEnabled")}
              hint={t("settings.soundHint")}
            />
            <div style={{ height: 12 }} />
            <Toggle
              checked={notifEnabled !== false}
              onChange={setNotifEnabled}
              label={t("settings.notifEnabled")}
              hint={t("settings.notifHint")}
            />
          </div>
        </div>

        <div className="col">
          <div className="card">
            <h2 className="h2">{t("settings.account")}</h2>
            <p className="sub" style={{ marginBottom: 10 }}>
              {t("settings.signedInAs")} <b>{user?.username}</b>
            </p>
            <div className="field">
              <label>{t("auth.username")}</label>
              <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} />
            </div>
            <button className="btn danger" style={{ width: "100%" }} onClick={logout}>
              {t("common.logOut")}
            </button>
          </div>

          <div className="card formcard" style={{ marginTop: 16, maxWidth: "none !important" }}>
            <h2 className="h2">{t("settings.learningProfile")}</h2>
            <div className="field">
              <label>{t("settings.nativeLanguage")}</label>
              <input
                className="input"
                value={form.native_language}
                onChange={(e) => setForm({ ...form, native_language: e.target.value })}
              />
            </div>
            <div className="field">
              <label>{t("settings.goalText")}</label>
              <input
                className="input"
                value={form.goal_text}
                onChange={(e) => setForm({ ...form, goal_text: e.target.value })}
                placeholder={t("settings.goalPlaceholder")}
              />
            </div>
            <div className="field">
              <label>{t("settings.dailyGoal")}</label>
              <input
                className="input"
                type="number"
                min={5}
                max={240}
                value={form.daily_goal_minutes}
                onChange={(e) => setForm({ ...form, daily_goal_minutes: Number(e.target.value) })}
              />
            </div>
            <div className="field">
              <label>{t("settings.bio")}</label>
              <textarea
                className="input"
                rows={2}
                value={form.bio}
                onChange={(e) => setForm({ ...form, bio: e.target.value })}
              />
            </div>
            {error && <p className="formerr">{error}</p>}
            {ok && (
              <p className="sub" style={{ color: "var(--good)", marginBottom: 10 }}>
                {ok}
              </p>
            )}
            <button className="btn primary" style={{ width: "100%" }} onClick={save}>
              {t("settings.save")}
            </button>
          </div>
        </div>
      </div>
    </Layout>
  );
}
