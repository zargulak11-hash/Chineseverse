import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
import Icon from "../components/Icon.jsx";
import UserAvatar from "../components/UserAvatar.jsx";
import Layout from "../components/Layout.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { useApi } from "../hooks/useApi.js";
import { formatDate } from "../dates.js";

export default function Profile() {
  const { t, i18n } = useTranslation();
  // Dates in the UI language, not the browser's: created_at is naive UTC,
  // last_active_date a plain day ("YYYY-MM-DD", which new Date() would read
  // as UTC midnight -- the previous day west of Greenwich).
  const joined = (iso) => formatDate(iso, i18n.language);
  const day = (ymd) => {
    const [y, m, d] = ymd.split("-").map(Number);
    return formatDate(new Date(y, m - 1, d), i18n.language);
  };
  const { data: me, error } = useApi("/me");
  const { dashboard } = useDashboard();
  const animal = dashboard?.animal;
  const [social, setSocial] = useState(null);

  useEffect(() => {
    if (!me) return;
    api.get(`/users/${me.user.id}/public`).then(setSocial).catch(() => setSocial(null));
  }, [me]);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!me) return <Layout><Loading /></Layout>;

  return (
    <Layout>
      {/* The learner's identity card: who they are, since when, their
          companion, and where to go from here. */}
      <header className="page-head pf-head">
        <div className="pf-id">
          <UserAvatar url={dashboard?.avatar_url} name={me.user.username} size={88} className="pf-avatar" />
          <div style={{ minWidth: 0 }}>
            <div className="page-eyebrow"><Icon name="user" size={13} /> {t("nav.groupYou")}</div>
            <h1 className="h1 pf-name">@{me.user.username}</h1>
            <p className="sub">{me.user.email} · {t("pages.profile.joined")} {joined(me.user.created_at)}</p>
            <div className="pf-actions">
              <Link to="/passport" className="btn primary small"><Icon name="award" size={13} /> {t("nav.passport")}</Link>
              <Link to="/community" className="btn ghost small"><Icon name="users" size={13} /> {t("pages.profile.findPeople")}</Link>
              <Link to="/settings" className="btn ghost small"><Icon name="settings" size={13} /> {t("pages.profile.editProfile")}</Link>
            </div>
          </div>
        </div>
        {animal && (
          <div className="pf-companion">
            <AnimalAvatar slug={animal.slug} size={64} />
            <span className="pf-companion-name">{animal.name}</span>
            <Link to="/animals" className="btn ghost small">{t("pages.profile.changeCompanion")}</Link>
          </div>
        )}
      </header>

      <div className="grid grid-2" style={{ marginTop: 18 }}>
        <div className="card">
          <h2 className="h2">{t("pages.profile.title")}</h2>
          <div className="col" style={{ marginTop: 10 }}>
            <div className="hbar">
              <span className="muted" style={{ width: 130 }}>{t("pages.profile.nativeLanguage")}</span>
              {/* Registration stores "English" etc.; show the four app languages in
                  the reader's own language, anything typed by hand as typed. */}
              <span>{me.profile.native_language ? t(`common.languageNames.${me.profile.native_language}`, { defaultValue: me.profile.native_language }) : "—"}</span>
            </div>
            <div className="hbar">
              <span className="muted" style={{ width: 130 }}>{t("pages.profile.goal")}</span>
              <span>{me.profile.goal_text || "—"}</span>
            </div>
            <div className="hbar">
              <span className="muted" style={{ width: 130 }}>{t("pages.profile.dailyGoal")}</span>
              <span>{me.profile.daily_goal_minutes} {t("pages.profile.minPerDay")}</span>
            </div>
            <div className="hbar">
              <span className="muted" style={{ width: 130 }}>{t("pages.profile.levelTest")}</span>
              <span>{me.profile.level_test_score != null ? `${me.profile.level_test_score} ${t("pages.profile.pts")}` : t("pages.profile.notTaken")}</span>
            </div>
            <div className="hbar">
              <span className="muted" style={{ width: 130 }}>{t("pages.profile.bio")}</span>
              <span>{me.profile.bio || "—"}</span>
            </div>
          </div>
          <Link to="/settings">
            <button className="btn small" style={{ marginTop: 14 }}>{t("pages.profile.editProfile")}</button>
          </Link>
        </div>

        <div className="card">
          <h2 className="h2">{t("pages.profile.streak")}</h2>
          <div className="scores" style={{ marginTop: 10 }}>
            <div className="scorecard"><div className="num" style={{ color: "var(--accent)" }}>{me.streak.current_streak}</div><div className="lbl">{t("pages.profile.current")}</div></div>
            <div className="scorecard"><div className="num">{me.streak.longest_streak}</div><div className="lbl">{t("pages.profile.longest")}</div></div>
            <div className="scorecard"><div className="num">{me.streak.total_active_days}</div><div className="lbl">{t("pages.profile.activeDays")}</div></div>
          </div>
          {me.streak.last_active_date && (
            <p className="sub" style={{ marginTop: 10 }}>{t("pages.profile.lastActive")}: {day(me.streak.last_active_date)}</p>
          )}
          <h2 className="h2" style={{ marginTop: 18 }}>{t("pages.profile.rewardsEarned")}</h2>
          <div className="scores" style={{ marginTop: 10 }}>
            <div className="scorecard"><div className="num" style={{ color: "var(--accent)" }}>{me.user.total_xp}</div><div className="lbl">{t("pages.profile.totalXp")}</div></div>
            <div className="scorecard"><div className="num" style={{ color: "var(--warn)" }}><Icon name="coin" size={18} style={{ verticalAlign: -3 }} /> {me.user.coins}</div><div className="lbl">{t("common.coins")}</div></div>
          </div>
        </div>

        <div className="card">
          <h2 className="h2">{t("pages.profile.community")}</h2>
          {social ? (
            <Link to={`/u/${me.user.id}`}>
              <div className="scores" style={{ marginTop: 10 }}>
                <div className="scorecard"><div className="num">{social.followers_count}</div><div className="lbl">{t("pages.profile.followers")}</div></div>
                <div className="scorecard"><div className="num">{social.following_count}</div><div className="lbl">{t("pages.profile.following")}</div></div>
              </div>
            </Link>
          ) : (
            <p className="sub" style={{ marginTop: 10 }}>—</p>
          )}
          <Link to="/community">
            <button className="btn small ghost" style={{ marginTop: 12 }}>{t("pages.profile.findPeopleToFollow")}</button>
          </Link>
        </div>
      </div>
    </Layout>
  );
}
