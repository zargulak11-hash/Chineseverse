import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { animalFace } from "../components/AnimalEmoji.jsx";
import Layout from "../components/Layout.jsx";
import { Bar, Badge, Empty, Ring, Stat } from "../components/ui.jsx";

export default function Dashboard() {
  const navigate = useNavigate();
  const [d, setD] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/dashboard").then(setD).catch((e) => setError(e.message));
  }, []);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!d) return <Layout><Empty>Loading your world…</Empty></Layout>;

  const skillAnchor = (code) => navigate(`/dna?focus=${code}`);

  return (
    <Layout>
      <div className="row spread">
        <div>
          <h1 className="h1">你好, {d.user.username}</h1>
          <p className="sub">
            HSK {d.hsk_level} · {d.mastery.toFixed(0)}% overall mastery
          </p>
        </div>
        <div className="row">
          <Badge tone="accent">🔥 {d.streak.current_streak}-day streak</Badge>
          <Badge tone="good">Goal {d.daily_goal.minutes ?? 20} min</Badge>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", marginTop: 20 }}>
        <div className="card">
          <div className="row">
            {d.animal ? (
              <>
                <span style={{ fontSize: 56 }}>{animalFace(d.animal.slug)}</span>
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
        <div className="card center">
          <Ring value={d.dna.overall} />
          <p className="sub">Learning DNA overall</p>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", marginTop: 16 }}>
        <div className="card">
          <h2 className="h2">Todays quests</h2>
          {d.quests_today.length === 0 && <Empty>No quests today — go explore.</Empty>}
          <div className="col">
            {d.quests_today.map((q) => (
              <div key={q.id} className="hbar">
                <span style={{ fontSize: 20 }}>{q.completed ? "✅" : "🎯"}</span>
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

        <div className="card">
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

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", marginTop: 16 }}>
        <div className="card">
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
        <div className="card">
          <h2 className="h2">Recommended mission</h2>
          {d.recommended_mission ? (
            <>
              <p className="sub">{d.recommended_mission.title}</p>
              <Link to={`/world/${d.next_location?.slug || ""}`}>
                <button className="btn small">Start it</button>
              </Link>
            </>
          ) : (
            <p className="sub">Youre on a roll — keep talking.</p>
          )}
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
      <div className="scores" style={{ marginTop: 20 }}>
        <Stat label="Words heard" value={d.dna.skills.find((s) => s.code === "vocabulary")?.mastery?.toFixed(0) ?? "—"} />
        <Stat label="Streak" value={`${d.streak.current_streak}d`} tone="var(--good)" />
        <Stat label="Badges" value={d.achievements.filter((a) => a.unlocked).length} tone="var(--accent)" />
        <Stat label="HSK level" value={d.hsk_level} tone="var(--accent2)" />
      </div>
    </Layout>
  );
}