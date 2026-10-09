import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api, changePassword } from "../api.js";
import Icon from "../components/Icon.jsx";
import UserAvatar from "../components/UserAvatar.jsx";
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

const EMPTY_PASSWORDS = { current: "", next: "", confirm: "" };

// The same rules the server applies (routers/me.py change_password), checked
// first so a typo doesn't cost a round trip. Returns an apiErrors.* key, so
// the message is the very one the server's answer would show.
function passwordProblem({ current, next, confirm }) {
  if (!current) return "currentPasswordMissing";
  if (next.length < 6) return "passwordTooShort";
  if (next.length > 128) return "passwordTooLong";
  if (next !== confirm) return "newPasswordMismatch";
  if (next === current) return "passwordSame";
  return null;
}

function ChangePassword({ user, onChanged }) {
  const { t, i18n } = useTranslation();
  const [pw, setPw] = useState(EMPTY_PASSWORDS);
  const [busy, setBusy] = useState(false);
  // A message is kept as a key where possible, so it follows a language
  // switch; the server's own (already translated) message is dropped then.
  const [problem, setProblem] = useState(null); // { key } | { text }
  const [done, setDone] = useState(false);

  useEffect(() => {
    setProblem((p) => (p?.text ? null : p));
  }, [i18n.language]);

  function edit(field, value) {
    setPw((cur) => ({ ...cur, [field]: value }));
    setDone(false);
  }

  async function submit(e) {
    e.preventDefault();
    if (busy) return; // one request at a time, even on a double Enter
    setDone(false);
    const key = passwordProblem(pw);
    if (key) {
      setProblem({ key });
      return;
    }
    setProblem(null);
    setBusy(true);
    try {
      onChanged(await changePassword(pw));
      setPw(EMPTY_PASSWORDS);
      setDone(true);
    } catch (err) {
      setProblem({ text: err.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card formcard is-inline" onSubmit={submit} noValidate>
      <h2 className="h2">{t("settings.changePassword")}</h2>
      <p className="sub" style={{ marginBottom: 12 }}>{t("settings.changePasswordSub")}</p>
      {/* For password managers: which account this new password belongs to. */}
      <input type="text" name="username" autoComplete="username" value={user?.username || ""} readOnly hidden />
      <div className="field">
        <label htmlFor="pw-current">{t("settings.currentPassword")}</label>
        <input
          id="pw-current"
          className="input"
          type="password"
          autoComplete="current-password"
          maxLength={128}
          value={pw.current}
          onChange={(e) => edit("current", e.target.value)}
          required
        />
      </div>
      <div className="field">
        <label htmlFor="pw-new">{t("settings.newPassword")}</label>
        <input
          id="pw-new"
          className="input"
          type="password"
          autoComplete="new-password"
          minLength={6}
          maxLength={128}
          value={pw.next}
          onChange={(e) => edit("next", e.target.value)}
          required
        />
      </div>
      <div className="field">
        <label htmlFor="pw-confirm">{t("settings.confirmNewPassword")}</label>
        <input
          id="pw-confirm"
          className="input"
          type="password"
          autoComplete="new-password"
          maxLength={128}
          value={pw.confirm}
          onChange={(e) => edit("confirm", e.target.value)}
          required
        />
      </div>
      {problem && (
        <p className="formerr" role="alert">
          {problem.key ? t(`apiErrors.${problem.key}`) : problem.text}
        </p>
      )}
      <p className="sub" role="status" aria-live="polite" style={{ color: "var(--good)", marginBottom: done ? 12 : 0 }}>
        {done ? t("settings.passwordChanged") : ""}
      </p>
      <button type="submit" className="btn primary" style={{ width: "100%" }} disabled={busy} aria-busy={busy || undefined}>
        {busy ? t("settings.changingPassword") : t("settings.changePasswordSubmit")}
      </button>
      <p className="sub" style={{ marginTop: 12, fontSize: "var(--text-xs)" }}>{t("settings.passwordProviderHint")}</p>
    </form>
  );
}

export default function Settings() {
  const { t, i18n } = useTranslation();
  const { user, setCurrentUser, logout: signOut } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { soundEnabled, setSoundEnabled, notifEnabled, setNotifEnabled } = usePrefs() || {};
  const { dashboard, refresh } = useDashboard() || {};
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [form, setForm] = useState({ native_language: "", goal_text: "", daily_goal_minutes: 10, bio: "" });
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
          // 10 is the model default; 20 here silently changed the goal on save.
          daily_goal_minutes: me.profile.daily_goal_minutes ?? 10,
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
    signOut();
    navigate("/", { replace: true });
  }


  return (
    <Layout>
      <h1 className="h1">{t("settings.title")}</h1>

      <div className="grid grid-2" style={{ marginTop: 18, alignItems: "start" }}>
        <div className="col">
          <div className="card">
            <h2 className="h2">{t("settings.appearance")}</h2>
            <div className="field">
              <label id="set-theme">{t("settings.theme")}</label>
              <div className="row" role="group" aria-labelledby="set-theme" style={{ marginTop: 4 }}>
                <button
                  type="button"
                  className={`btn small${theme === "ink" ? " primary" : " ghost"}`}
                  aria-pressed={theme === "ink"}
                  onClick={() => theme !== "ink" && toggleTheme()}
                >
                  <Icon name="droplet" size={13} /> {t("settings.themeInk")}
                </button>
                <button
                  type="button"
                  className={`btn small${theme === "paper" ? " primary" : " ghost"}`}
                  aria-pressed={theme === "paper"}
                  onClick={() => theme !== "paper" && toggleTheme()}
                >
                  <Icon name="droplet" size={13} /> {t("settings.themePaper")}
                </button>
              </div>
            </div>
            <div className="field">
              <label id="set-language">{t("settings.language")}</label>
              <div className="row" role="group" aria-labelledby="set-language" style={{ marginTop: 4 }}>
                {SUPPORTED_LANGS.map((l) => (
                  <button
                    key={l.code}
                    type="button"
                    className={`btn small${i18n.language === l.code ? " primary" : " ghost"}`}
                    aria-pressed={i18n.language === l.code}
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
              <UserAvatar url={avatarUrl} name={user?.username} size={64} />
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
              <label htmlFor="set-username">{t("auth.username")}</label>
              <input id="set-username" className="input" value={username} onChange={(e) => setUsername(e.target.value)} />
            </div>
            <button className="btn danger" style={{ width: "100%" }} onClick={logout}>
              {t("common.logOut")}
            </button>
          </div>

          <ChangePassword user={user} onChanged={setCurrentUser} />

          <div className="card formcard is-inline">
            <h2 className="h2">{t("settings.learningProfile")}</h2>
            <div className="field">
              <label htmlFor="set-native">{t("settings.nativeLanguage")}</label>
              <input
                id="set-native"
                className="input"
                value={form.native_language}
                onChange={(e) => setForm({ ...form, native_language: e.target.value })}
              />
            </div>
            <div className="field">
              <label htmlFor="set-goal">{t("settings.goalText")}</label>
              <input
                id="set-goal"
                className="input"
                value={form.goal_text}
                onChange={(e) => setForm({ ...form, goal_text: e.target.value })}
                placeholder={t("settings.goalPlaceholder")}
              />
            </div>
            <div className="field">
              <label htmlFor="set-daily">{t("settings.dailyGoal")}</label>
              <input
                id="set-daily"
                className="input"
                type="number"
                min={5}
                max={240}
                value={form.daily_goal_minutes}
                onChange={(e) => setForm({ ...form, daily_goal_minutes: Number(e.target.value) })}
              />
            </div>
            <div className="field">
              <label htmlFor="set-bio">{t("settings.bio")}</label>
              <textarea
                id="set-bio"
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
