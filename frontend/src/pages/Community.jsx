import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import UserAvatar from "../components/UserAvatar.jsx";
import { Empty, Loading, MotionButton } from "../components/ui.jsx";

// Find people and follow them. The page opens on the learner's own network
// -- the people they follow, and who follows them (the existing
// /users/{id}/following and /followers) -- with search on top; it used to
// be a search box on an empty page.

function FollowButton({ result, onChange }) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function toggle() {
    setBusy(true);
    setError("");
    try {
      const updated = result.is_following
        ? await api.del(`/users/${result.id}/follow`)
        : await api.post(`/users/${result.id}/follow`);
      onChange(updated);
    } catch {
      setError(t("pages.community.followError"));
    } finally {
      setBusy(false);
    }
  }

  if (result.is_self) return null;

  return (
    <div className="cm-follow">
      <MotionButton
        className={`btn small${result.is_following ? " ghost" : " primary"}`}
        disabled={busy}
        onClick={toggle}
      >
        {result.is_following ? t("pages.community.unfollow") : t("pages.community.follow")}
      </MotionButton>
      {error && <span role="alert" className="cm-follow-err">{error}</span>}
    </div>
  );
}

function Person({ r, onChange, compact = false }) {
  const { t } = useTranslation();
  return (
    <li className={`cm-person${compact ? " is-compact" : ""}`}>
      <Link to={`/u/${r.id}`} className="cm-person-link">
        <UserAvatar url={r.avatar_url} name={r.username} size={compact ? 32 : 44} />
        <span className="cm-person-text">
          <b>{r.username}</b>
          <span className="sub">{r.followers_count} {t("pages.profile.followers")} · {r.total_xp} XP</span>
        </span>
      </Link>
      <FollowButton result={r} onChange={onChange} />
    </li>
  );
}

export default function Community() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [q, setQ] = useState("");
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");
  const [following, setFollowing] = useState(null);
  const [followers, setFollowers] = useState(null);

  useEffect(() => {
    const query = q.trim();
    if (!query) {
      setResults(null);
      return undefined;
    }
    let cancelled = false;
    const timer = setTimeout(() => {
      api
        .get(`/users/search?q=${encodeURIComponent(query)}`)
        .then((r) => !cancelled && setResults(r))
        .catch((e) => !cancelled && setError(e.message));
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [q]);

  useEffect(() => {
    if (!user?.id) return;
    api.get(`/users/${user.id}/following`).then(setFollowing).catch(() => setFollowing([]));
    api.get(`/users/${user.id}/followers`).then(setFollowers).catch(() => setFollowers([]));
  }, [user?.id]);

  // One follow change shows everywhere the person appears.
  function patch(updated) {
    const swap = (rs) => (rs ? rs.map((r) => (r.id === updated.id ? updated : r)) : rs);
    setResults(swap);
    setFollowers(swap);
    setFollowing((rs) => {
      if (!rs) return rs;
      if (updated.is_following && !rs.some((r) => r.id === updated.id)) return [updated, ...rs];
      return swap(rs);
    });
  }

  const searching = !!q.trim();
  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="users" size={13} /> {t("nav.groupYou")}</div>
          <h1 className="h1">{t("pages.community.title")}</h1>
          <p className="sub">{t("pages.community.subtitle")}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi"><span className="kpi-value">{following ? following.filter((r) => r.is_following).length : "—"}</span><span className="kpi-label">{t("pages.profile.following")}</span></div>
          <div className="kpi"><span className="kpi-value">{followers ? followers.length : "—"}</span><span className="kpi-label">{t("pages.profile.followers")}</span></div>
        </div>
      </header>

      <div className="ws">
        <div className="ws-main">
          <label className="dict-search">
            <Icon name="search" size={18} />
            <input
              className="input"
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={t("pages.community.searchPlaceholder")}
              aria-label={t("pages.community.searchPlaceholder")}
              autoFocus
            />
          </label>
          {error && <p className="formerr">{error}</p>}

          {searching ? (
            <section className="cm-section" aria-live="polite">
              {results === null ? <Loading /> : results.length === 0 ? (
                <Empty>{t("pages.community.noMatch", { query: q })}</Empty>
              ) : (
                <ul className="cm-list">{results.map((r) => <Person key={r.id} r={r} onChange={patch} />)}</ul>
              )}
            </section>
          ) : (
            <section className="cm-section" aria-labelledby="cm-following">
              <h2 className="h2 section-title" id="cm-following">{t("pages.community.youFollow")}</h2>
              {following === null ? <Loading /> : following.length === 0 ? (
                <p className="sub">{t("pages.community.followNone")}</p>
              ) : (
                <ul className="cm-list">{following.map((r) => <Person key={r.id} r={r} onChange={patch} />)}</ul>
              )}
            </section>
          )}
        </div>

        <aside className="ws-side">
          <div className="card side-card">
            <p className="side-title">{t("pages.community.followYou")}</p>
            {followers === null ? <Loading /> : followers.length === 0 ? (
              <p className="sub" style={{ margin: 0 }}>{t("pages.community.followersNone")}</p>
            ) : (
              <ul className="cm-list is-side">{followers.map((r) => <Person key={r.id} r={r} onChange={patch} compact />)}</ul>
            )}
          </div>
          {user?.id && (
            <Link to={`/u/${user.id}`} className="btn ghost">
              <Icon name="user" size={14} /> {t("pages.community.myPublicPage")}
            </Link>
          )}
        </aside>
      </div>
    </Layout>
  );
}
