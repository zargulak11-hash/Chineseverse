import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import UserAvatar from "../components/UserAvatar.jsx";
import { Empty, Loading, MotionButton } from "../components/ui.jsx";

function FollowRow({ u }) {
  const { t } = useTranslation();
  return (
    <Link to={`/u/${u.id}`} className="row spread" style={{ padding: "8px 0" }}>
      <span className="row" style={{ gap: 10 }}>
        <UserAvatar url={u.avatar_url} name={u.username} size={30} />
        <b style={{ fontSize: 13.5 }}>{u.username}</b>
      </span>
      <span className="muted" style={{ fontSize: 11.5 }}>{u.followers_count} {t("pages.profile.followers")}</span>
    </Link>
  );
}

export default function PublicProfile() {
  const { t, i18n } = useTranslation();
  const { userId } = useParams();
  const [profile, setProfile] = useState(null);
  const [tab, setTab] = useState(null); // "followers" | "following" | null
  const [list, setList] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [followError, setFollowError] = useState("");

  useEffect(() => {
    setProfile(null);
    setTab(null);
    api.get(`/users/${userId}/public`).then(setProfile).catch((e) => setError(e.message));
  }, [userId, i18n.language]);

  useEffect(() => {
    if (!tab) {
      setList(null);
      return;
    }
    api.get(`/users/${userId}/${tab}`).then(setList).catch(() => setList([]));
  }, [tab, userId]);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!profile) return <Layout><Loading /></Layout>;

  async function toggleFollow() {
    setBusy(true);
    setFollowError("");
    try {
      const updated = profile.is_following
        ? await api.del(`/users/${profile.id}/follow`)
        : await api.post(`/users/${profile.id}/follow`);
      setProfile(updated);
    } catch {
      // The profile keeps its real (unchanged) state; just say it failed.
      setFollowError(t("pages.community.followError"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Layout>
      {/* The same header band as every page, the list below at full width. */}
      <header className="page-head">
          <div className="row" style={{ gap: 14, margin: 0 }}>
            <UserAvatar url={profile.avatar_url} name={profile.username} size={64} />
            <div>
              <h1 className="h1">@{profile.username}</h1>
              <p className="sub">
                {profile.total_xp} XP · {t("pages.profile.joined")} {new Date(profile.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>
          <div className="kpi-row" style={{ alignItems: "center" }}>
            <button type="button" className={`kpi kpi-button${tab === "followers" ? " is-active" : ""}`}
                    aria-pressed={tab === "followers"} onClick={() => setTab(tab === "followers" ? null : "followers")}>
              <span className="kpi-value">{profile.followers_count}</span>
              <span className="kpi-label">{t("pages.profile.followers")}</span>
            </button>
            <button type="button" className={`kpi kpi-button${tab === "following" ? " is-active" : ""}`}
                    aria-pressed={tab === "following"} onClick={() => setTab(tab === "following" ? null : "following")}>
              <span className="kpi-value">{profile.following_count}</span>
              <span className="kpi-label">{t("pages.profile.following")}</span>
            </button>
            {!profile.is_self && (
              <MotionButton
                className={`btn${profile.is_following ? " ghost" : " primary"}`}
                disabled={busy}
                onClick={toggleFollow}
              >
                <Icon name={profile.is_following ? "check" : "userPlus"} size={14} />
                {profile.is_following ? t("pages.community.following") : t("pages.community.follow")}
              </MotionButton>
            )}
          </div>
      </header>
      {followError && (
        <p className="sub" role="alert" style={{ color: "var(--bad)", margin: "10px 0 0" }}>{followError}</p>
      )}

      <div className="card" style={{ marginTop: 16 }}>
        <p className="side-title">{tab === "following" ? t("pages.profile.following") : t("pages.profile.followers")}</p>
        {!tab && <p className="sub">{t("pages.publicProfile.pickList")}</p>}
        {tab && (
          <div className="col" style={{ marginTop: 10 }}>
            {list === null && <Loading />}
            {list && list.length === 0 && <Empty>{t("pages.publicProfile.nobodyHere")}</Empty>}
            {list && list.map((u) => <FollowRow key={u.id} u={u} />)}
          </div>
        )}
      </div>
    </Layout>
  );
}
