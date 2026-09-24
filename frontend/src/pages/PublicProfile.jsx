import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Empty, Loading, MotionButton } from "../components/ui.jsx";

function FollowRow({ u }) {
  const { t } = useTranslation();
  return (
    <Link to={`/u/${u.id}`} className="row spread" style={{ padding: "8px 0" }}>
      <span className="row" style={{ gap: 10 }}>
        {u.avatar_url ? (
          <img src={u.avatar_url} alt="" className="avatar-preview" style={{ width: 30, height: 30 }} />
        ) : (
          <Icon name="user" size={18} />
        )}
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
    try {
      const updated = profile.is_following
        ? await api.del(`/users/${profile.id}/follow`)
        : await api.post(`/users/${profile.id}/follow`);
      setProfile(updated);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Layout>
      <div className="card" style={{ maxWidth: 520 }}>
        <div className="row spread">
          <div className="row" style={{ gap: 14 }}>
            {profile.avatar_url ? (
              <img src={profile.avatar_url} alt="" className="avatar-preview" style={{ width: 64, height: 64 }} />
            ) : (
              <span className="sidebar-profile-fallback" style={{ width: 64, height: 64 }}>
                <Icon name="user" size={26} />
              </span>
            )}
            <div>
              <h1 className="h1">@{profile.username}</h1>
              <p className="sub">
                {profile.total_xp} XP · {t("pages.profile.joined")} {new Date(profile.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>
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

        <div className="row" style={{ marginTop: 18, gap: 24 }}>
          <button
            type="button"
            className="voice-feedback-text"
            style={{ background: "none", border: "none", cursor: "pointer", padding: 0, textAlign: "left" }}
            onClick={() => setTab(tab === "followers" ? null : "followers")}
          >
            <b style={{ fontSize: 18 }}>{profile.followers_count}</b>
            <div className="sub" style={{ fontSize: 12 }}>{t("pages.profile.followers")}</div>
          </button>
          <button
            type="button"
            style={{ background: "none", border: "none", cursor: "pointer", padding: 0, textAlign: "left" }}
            onClick={() => setTab(tab === "following" ? null : "following")}
          >
            <b style={{ fontSize: 18 }}>{profile.following_count}</b>
            <div className="sub" style={{ fontSize: 12 }}>{t("pages.profile.following")}</div>
          </button>
        </div>

        {tab && (
          <div className="col" style={{ marginTop: 14, borderTop: "1px solid var(--border)", paddingTop: 10 }}>
            {list === null && <Loading />}
            {list && list.length === 0 && <Empty>{t("pages.publicProfile.nobodyHere")}</Empty>}
            {list && list.map((u) => <FollowRow key={u.id} u={u} />)}
          </div>
        )}
      </div>
    </Layout>
  );
}
