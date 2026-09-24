import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { useApi } from "../hooks/useApi.js";

export default function Profile() {
  const { t } = useTranslation();
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
      <div className="row spread">
        <div className="row">
          {dashboard?.avatar_url ? (
            <img src={dashboard.avatar_url} alt="" className="avatar-preview" style={{ width: 56, height: 56 }} />
          ) : (
            animal && <AnimalAvatar slug={animal.slug} size={56} />
          )}
          <div>
            <h1 className="h1">@{me.user.username}</h1>
            <p className="sub">{me.user.email} · {t("pages.profile.joined")} {new Date(me.user.created_at).toLocaleDateString()}</p>
          </div>
        </div>
        <div className="row">
          <Link to="/community">
            <button className="btn ghost"><Icon name="users" size={13} /> {t("pages.profile.findPeople")}</button>
          </Link>
          <Link to="/animals">
            <button className="btn ghost">{t("pages.profile.changeCompanion")}</button>
          </Link>
        </div>
      </div>

      <div className="grid grid-2" style={{ marginTop: 18 }}>
        <div className="card">
          <h2 className="h2">{t("pages.profile.title")}</h2>
          <div className="col" style={{ marginTop: 10 }}>
            <div className="hbar">
              <span className="muted" style={{ width: 130 }}>{t("pages.profile.nativeLanguage")}</span>
              <span>{me.profile.native_language || "—"}</span>
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
            <p className="sub" style={{ marginTop: 10 }}>{t("pages.profile.lastActive")}: {me.streak.last_active_date}</p>
          )}
          <h2 className="h2" style={{ marginTop: 18 }}>{t("pages.profile.rewardsEarned")}</h2>
          <div className="scores" style={{ marginTop: 10 }}>
            <div className="scorecard"><div className="num" style={{ color: "var(--accent)" }}>{me.user.total_xp}</div><div className="lbl">{t("pages.profile.totalXp")}</div></div>
            <div className="scorecard"><div className="num" style={{ color: "var(--warn)" }}>🪙 {me.user.coins}</div><div className="lbl">{t("common.coins")}</div></div>
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
