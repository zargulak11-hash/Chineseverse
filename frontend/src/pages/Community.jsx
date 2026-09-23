import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Empty, MotionButton } from "../components/ui.jsx";

function FollowButton({ result, onChange }) {
  const [busy, setBusy] = useState(false);

  async function toggle() {
    setBusy(true);
    try {
      const updated = result.is_following
        ? await api.del(`/users/${result.id}/follow`)
        : await api.post(`/users/${result.id}/follow`);
      onChange(updated);
    } finally {
      setBusy(false);
    }
  }

  if (result.is_self) return null;

  return (
    <MotionButton
      className={`btn small${result.is_following ? " ghost" : " primary"}`}
      disabled={busy}
      onClick={toggle}
    >
      {result.is_following ? "Unfollow" : "Follow"}
    </MotionButton>
  );
}

export default function Community() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const query = q.trim();
    if (!query) {
      setResults(null);
      return undefined;
    }
    let cancelled = false;
    const t = setTimeout(() => {
      api
        .get(`/users/search?q=${encodeURIComponent(query)}`)
        .then((r) => !cancelled && setResults(r))
        .catch((e) => !cancelled && setError(e.message));
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [q]);

  function patchResult(updated) {
    setResults((rs) => rs.map((r) => (r.id === updated.id ? updated : r)));
  }

  return (
    <Layout>
      <h1 className="h1">Find people</h1>
      <p className="sub">Search for other learners by username and follow the ones you want to keep up with.</p>

      <div className="field" style={{ maxWidth: 420, marginTop: 16 }}>
        <input
          className="input"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search by username…"
          autoFocus
        />
      </div>

      {error && <p className="formerr">{error}</p>}

      {results && results.length === 0 && <Empty>No learners match "{q}".</Empty>}

      <div className="col" style={{ marginTop: 16, maxWidth: 520 }}>
        {(results || []).map((r) => (
          <div key={r.id} className="card row spread">
            <Link to={`/u/${r.id}`} className="row" style={{ gap: 12 }}>
              {r.avatar_url ? (
                <img src={r.avatar_url} alt="" className="avatar-preview" style={{ width: 40, height: 40 }} />
              ) : r.animal_id ? (
                <Icon name="userPlus" size={24} />
              ) : (
                <Icon name="user" size={24} />
              )}
              <div>
                <b>{r.username}</b>
                <p className="sub" style={{ fontSize: 12, margin: 0 }}>
                  {r.followers_count} followers · {r.total_xp} XP
                </p>
              </div>
            </Link>
            <FollowButton result={r} onChange={patchResult} />
          </div>
        ))}
      </div>
    </Layout>
  );
}
