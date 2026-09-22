import { Link } from "react-router-dom";
import Layout from "../components/Layout.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

export default function Roadmap() {
  const { data: r, error } = useApi("/hsk/roadmap");

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!r) return <Layout><Loading>Loading roadmap…</Loading></Layout>;

  const stateIcon = (s) =>
    s === "locked" ? "🔒" : s === "current" ? "⭐" : "✅";

  return (
    <Layout>
      <h1 className="h1">HSK roadmap</h1>
      <p className="sub">{r.note}</p>
      <div className="hbar" style={{ marginTop: 14 }}>
        <span className="muted">Overall</span>
        <Bar value={r.overall_mastery} />
        <span>{r.overall_mastery.toFixed(0)}%</span>
      </div>

      <div className="grid" style={{ marginTop: 20 }}>
        {r.levels.map((lvl) => (
          <div key={lvl.level} className="card"
            style={lvl.status === "locked" ? { opacity: 0.6 } : {}}>
            <div className="row spread">
              <div className="row">
                <span style={{ fontSize: 22 }}>{stateIcon(lvl.status)}</span>
                <h2 className="h2">HSK {lvl.level}</h2>
                <span className={`badge ${lvl.status === "current" ? "accent" : ""}`}>
                  {lvl.status}
                </span>
              </div>
              <span className="muted">
                {lvl.vocab_mastered}/{lvl.vocab_total} words
              </span>
            </div>
            <div className="hbar">
              <span className="muted" style={{ width: 90, fontSize: 12 }}>
                Mastery
              </span>
              <Bar value={lvl.mastery} max={100} />
              <span style={{ width: 40, textAlign: "right" }}>{lvl.mastery.toFixed(0)}%</span>
            </div>
            <div className="hbar" style={{ marginTop: 6 }}>
              <span className="muted" style={{ width: 90, fontSize: 12 }}>
                Lessons
              </span>
              <Bar value={lvl.lessons_completed} max={10} alt />
              <span style={{ width: 40, textAlign: "right" }}>{lvl.lessons_completed}</span>
            </div>
            {lvl.ready_for_next ? (
              <BadgeOK>{lvl.level + 1 <= 6 ? "Ready for HSK " + (lvl.level + 1) : "Max level reached"}</BadgeOK>
            ) : (
              lvl.reason && <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>{lvl.reason}</p>
            )}
          </div>
        ))}
      </div>
      <Link to="/vocabulary">
        <button className="btn primary" style={{ marginTop: 18 }}>Practice vocabulary</button>
      </Link>
    </Layout>
  );
}

function BadgeOK({ children }) {
  return <p className="badge good" style={{ marginTop: 10 }}>{children}</p>;
}