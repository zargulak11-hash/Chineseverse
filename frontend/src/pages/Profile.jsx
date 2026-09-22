import { Link } from "react-router-dom";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
import Layout from "../components/Layout.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { useApi } from "../hooks/useApi.js";

export default function Profile() {
  const { data: me, error } = useApi("/me");
  const { dashboard } = useDashboard();
  const animal = dashboard?.animal;

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!me) return <Layout><Loading /></Layout>;

  return (
    <Layout>
      <div className="row spread">
        <div className="row">
          {animal && <AnimalAvatar slug={animal.slug} accentColor={animal.accent_color} size={56} />}
          <div>
            <h1 className="h1">@{me.user.username}</h1>
            <p className="sub">{me.user.email} · joined {new Date(me.user.created_at).toLocaleDateString()}</p>
          </div>
        </div>
        <Link to="/animals">
          <button className="btn ghost">Change companion</button>
        </Link>
      </div>

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", marginTop: 18 }}>
        <div className="card">
          <h2 className="h2">Profile</h2>
          <div className="col" style={{ marginTop: 10 }}>
            <div className="hbar">
              <span className="muted" style={{ width: 130 }}>Native language</span>
              <span>{me.profile.native_language || "—"}</span>
            </div>
            <div className="hbar">
              <span className="muted" style={{ width: 130 }}>Goal</span>
              <span>{me.profile.goal_text || "—"}</span>
            </div>
            <div className="hbar">
              <span className="muted" style={{ width: 130 }}>Daily goal</span>
              <span>{me.profile.daily_goal_minutes} min/day</span>
            </div>
            <div className="hbar">
              <span className="muted" style={{ width: 130 }}>Level test</span>
              <span>{me.profile.level_test_score != null ? me.profile.level_test_score + " pts" : "not taken"}</span>
            </div>
            <div className="hbar">
              <span className="muted" style={{ width: 130 }}>Bio</span>
              <span>{me.profile.bio || "—"}</span>
            </div>
          </div>
          <Link to="/settings">
            <button className="btn small" style={{ marginTop: 14 }}>Edit profile</button>
          </Link>
        </div>

        <div className="card">
          <h2 className="h2">Streak</h2>
          <div className="scores" style={{ marginTop: 10 }}>
            <div className="scorecard"><div className="num" style={{ color: "var(--accent)" }}>{me.streak.current_streak}</div><div className="lbl">current</div></div>
            <div className="scorecard"><div className="num">{me.streak.longest_streak}</div><div className="lbl">longest</div></div>
            <div className="scorecard"><div className="num">{me.streak.total_active_days}</div><div className="lbl">active days</div></div>
          </div>
          {me.streak.last_active_date && (
            <p className="sub" style={{ marginTop: 10 }}>Last active: {me.streak.last_active_date}</p>
          )}
          <h2 className="h2" style={{ marginTop: 18 }}>Rewards earned</h2>
          <div className="scores" style={{ marginTop: 10 }}>
            <div className="scorecard"><div className="num" style={{ color: "var(--accent)" }}>{me.user.total_xp}</div><div className="lbl">total xp</div></div>
            <div className="scorecard"><div className="num" style={{ color: "var(--warn)" }}>🪙 {me.user.coins}</div><div className="lbl">coins</div></div>
          </div>
        </div>
      </div>
    </Layout>
  );
}