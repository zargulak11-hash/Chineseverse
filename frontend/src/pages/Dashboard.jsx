import { Link, useNavigate } from "react-router-dom";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
import Icon from "../components/Icon.jsx";
import InkBrush from "../components/InkBrush.jsx";
import Layout from "../components/Layout.jsx";
import { Bar, Badge, Empty, Loading, RingHero } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";

const QUICK_ACTIONS = [
  ["/world", "Explore the World", "world", "linear-gradient(135deg, #2b6f93, #4fc3f7)"],
  ["/dna", "View your DNA", "dna", "linear-gradient(135deg, #2f7a4c, #4cc26b)"],
  ["/duels", "Start a Duel", "swords", "linear-gradient(135deg, #b1501c, #ff8a3d)"],
  ["/missions", "Pick a Mission", "flag", "linear-gradient(135deg, var(--accent-soft), var(--accent-strong))"],
];

export default function Dashboard() {
  const navigate = useNavigate();
  const { dashboard: d, error } = useDashboard();

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!d) return <Layout><Loading>Loading your world…</Loading></Layout>;

  const skillAnchor = (code) => navigate(`/dna?focus=${code}`);
  const questsDone = d.quests_today.filter((q) => q.completed).length;
  const questsTotal = d.quests_today.length;
  const badgesUnlocked = d.achievements.filter((a) => a.unlocked).length;

  return (
    <Layout>
      <div className="hero-banner" style={{ position: "relative" }}>
        <InkBrush variant="hero" />
        <span className="kicker">Learn Chinese by living it</span>
        <h1>你好, {d.user.username}</h1>
        <p className="sub">
          HSK {d.hsk_level} · {d.mastery.toFixed(0)}% overall mastery · goal {d.daily_goal.minutes ?? 20} min/day
        </p>
        <div className="hero-stats-row">
          <div className="hero-stat-pill">
            <span className="ic"><Icon name="target" size={15} /></span>
            <div>
              <div className="num">{questsDone}/{questsTotal || 0}</div>
              <div className="lbl">Today's quests</div>
            </div>
          </div>
          <div className="hero-stat-pill">
            <span className="ic"><Icon name="flame" size={15} /></span>
            <div>
              <div className="num">{d.streak.current_streak}</div>
              <div className="lbl">Day streak</div>
            </div>
          </div>
          <div className="hero-stat-pill">
            <span className="ic"><Icon name="coin" size={15} /></span>
            <div>
              <div className="num">{d.user.coins}</div>
              <div className="lbl">Coins</div>
            </div>
          </div>
          <div className="hero-stat-pill">
            <span className="ic"><Icon name="trending" size={15} /></span>
            <div>
              <div className="num">HSK {d.hsk_level}</div>
              <div className="lbl">Level</div>
            </div>
          </div>
        </div>
      </div>

      <div className="quick-actions">
        {QUICK_ACTIONS.map(([to, label, icon, gradient]) => (
          <Link to={to} key={to} className="quick-action" style={{ background: gradient }}>
            <div className="qa-top">
              <span className="ic"><Icon name={icon} size={19} /></span>
              <Icon name="arrowRight" size={17} className="arrow" />
            </div>
            <span className="label">{label}</span>
          </Link>
        ))}
      </div>

      <div className="stat-grid">
        <div className="stat-card" style={{ "--stat-color": "#ff8a3d" }}>
          <span className="ic"><Icon name="flame" size={18} /></span>
          <div className="num">{d.streak.current_streak}</div>
          <div className="lbl">Day streak</div>
        </div>
        <div className="stat-card" style={{ "--stat-color": "var(--accent)" }}>
          <span className="ic"><Icon name="coin" size={18} /></span>
          <div className="num">{d.user.coins}</div>
          <div className="lbl">Coins earned</div>
        </div>
        <div className="stat-card" style={{ "--stat-color": "#3fb6a8" }}>
          <span className="ic"><Icon name="dna" size={18} /></span>
          <div className="num">{d.mastery.toFixed(0)}%</div>
          <div className="lbl">HSK mastery</div>
        </div>
        <div className="stat-card" style={{ "--stat-color": "#9b6fe0" }}>
          <span className="ic"><Icon name="award" size={18} /></span>
          <div className="num">{badgesUnlocked}</div>
          <div className="lbl">Achievements</div>
        </div>
      </div>

      <div className="bento" style={{ marginTop: 16 }}>
        <div className="card bento-2">
          <div className="row">
            {d.animal ? (
              <>
                <AnimalAvatar slug={d.animal.slug} size={64} />
                <div>
                  <h2 className="h2">{d.animal.name}</h2>
                  <p className="sub">{d.animal.species}</p>
                  <p className="sub">{d.animal.special_ability}</p>
                </div>
              </>
            ) : (
              <Link to="/animals">
                <button className="btn primary">Choose your companion</button>
              </Link>
            )}
          </div>
        </div>
        <div className="card bento-4 center dna-hero-card">
          <RingHero value={d.dna.overall} label="Learning DNA overall" />
        </div>
      </div>

      <div className="bento" style={{ marginTop: 16 }}>
        <div className="card bento-3">
          <h2 className="h2">Todays quests</h2>
          {d.quests_today.length === 0 && <Empty>No quests today — go explore.</Empty>}
          <div className="col">
            {d.quests_today.map((q) => (
              <div key={q.id} className="hbar">
                <span className="ic" style={{ width: 30, height: 30 }}>
                  <Icon name={q.completed ? "check" : "target"} size={14} />
                </span>
                <div style={{ flex: 1 }}>
                  <div className="row spread" style={{ margin: 0 }}>
                    <b>{q.title}</b>
                    <span className="muted">
                      {q.progress}/{q.target}
                    </span>
                  </div>
                  <Bar value={q.progress} max={q.target} />
                </div>
              </div>
            ))}
          </div>
          <Link to="/quests">
            <button className="btn small ghost" style={{ marginTop: 12 }}>All quests</button>
          </Link>
        </div>

        <div className="card bento-3">
          <h2 className="h2">Pros/cons DNA</h2>
          <div className="col">
            {d.dna.skills.slice(0, 6).map((s) => (
              <div key={s.code} className="hbar" onClick={() => skillAnchor(s.code)}>
                <span className="muted" style={{ width: 90, fontSize: 12.5 }}>
                  {s.name}
                </span>
                <Bar value={s.mastery} />
                <span style={{ width: 34, textAlign: "right" }}>{s.mastery.toFixed(0)}</span>
              </div>
            ))}
          </div>
          <Link to="/dna">
            <button className="btn small ghost" style={{ marginTop: 12 }}>Full DNA</button>
          </Link>
        </div>
      </div>

      <div className="bento" style={{ marginTop: 16 }}>
        <div className="card bento-3">
          <h2 className="h2">Next location</h2>
          {d.next_location ? (
            <Link to={`/world/${d.next_location.slug}`}>
              <button className="btn primary">
                {d.next_location.icon} {d.next_location.name}
              </button>
            </Link>
          ) : (
            <p className="sub">You can explore everything now.</p>
          )}
        </div>
        <div className="card bento-3">
          <h2 className="h2">Recommended mission</h2>
          {d.recommended_mission ? (
            <p className="sub">{d.recommended_mission.title}</p>
          ) : (
            <p className="sub">Youre on a roll — keep talking.</p>
          )}
          <Link to="/missions">
            <button className="btn small">View all missions</button>
          </Link>
        </div>
      </div>

      {d.recent_mistakes.length > 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <h2 className="h2">Needs work</h2>
          <div className="col">
            {d.recent_mistakes.slice(0, 4).map((m) => (
              <div key={m.id} className="row spread">
                <span className="muted">{m.answer_given || m.question_text}</span>
                <Badge tone="bad">×{m.occurrences}</Badge>
              </div>
            ))}
          </div>
          <Link to="/mistakes">
            <button className="btn small ghost" style={{ marginTop: 12 }}>Review mistakes</button>
          </Link>
        </div>
      )}
    </Layout>
  );
}
