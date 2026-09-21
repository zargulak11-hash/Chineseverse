import { useEffect, useState } from "react";
import { api } from "../api.js";
import Layout from "../components/Layout.jsx";
import { Bar, Empty } from "../components/ui.jsx";

export default function Quests() {
  const [quests, setQuests] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/quests/today").then(setQuests).catch((e) => setError(e.message));
  }, []);

  async function claim(q) {
    try {
      const updated = await api.post(`/quests/${q.id}/claim`);
      setQuests((qs) => qs.map((x) => (x.id === q.id ? updated : x)));
    } catch (e) {
      setError(e.message);
    }
  }

  if (error) return <Layout><Empty>{error}</Empty></Layout>;

  return (
    <Layout>
      <h1 className="h1">Daily quests</h1>
      <p className="sub">
        Generated from your DNA every day. Complete them to feed your companion.
      </p>

      <div className="col" style={{ marginTop: 18 }}>
        {quests.map((q) => (
          <div key={q.id} className="card" style={{ borderColor: q.completed ? "var(--good)" : undefined }}>
            <div className="row spread">
              <div className="row">
                <span style={{ fontSize: 22 }}>{q.completed ? "✅" : "🎯"}</span>
                <div>
                  <b>{q.title}</b>
                  <p className="sub" style={{ fontSize: 12 }}>{q.description}</p>
                  {q.flavor && <p className="muted" style={{ fontSize: 11.5 }}>{q.flavor}</p>}
                </div>
              </div>
              <div className="row">
                <span className="ilb">+{q.reward_xp} xp</span>
                <span className="ilb">🪙 {q.reward_coins}</span>
              </div>
            </div>
            <div className="hbar" style={{ marginTop: 10 }}>
              <span className="muted" style={{ fontSize: 12 }}>
                {q.progress}/{q.target}
              </span>
              <Bar value={q.progress} max={q.target} />
            </div>
            {q.completed && (
              <button className="btn primary small" style={{ marginTop: 12 }} onClick={() => claim(q)}>
                Claim reward
              </button>
            )}
          </div>
        ))}
      </div>
      {quests.length === 0 && <Empty>Nothing today. Take a walk around the world.</Empty>}
    </Layout>
  );
}