import { useEffect, useState } from "react";
import { api } from "../api.js";
import Layout from "../components/Layout.jsx";
import { Empty } from "../components/ui.jsx";

const CAT_ICON = {
  voice: "🎙️",
  social: "⚔️",
  progress: "📈",
  case_skill: "🕵️",
  default: "🏅",
};

export default function Achievements() {
  const [badges, setBadges] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/achievements").then(setBadges).catch((e) => setError(e.message));
  }, []);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;

  const unlocked = badges.filter((b) => b.unlocked);

  return (
    <Layout>
      <h1 className="h1">Achievements</h1>
      <p className="sub">
        {unlocked.length}/{badges.length} earned
      </p>

      <div className="grid cards" style={{ marginTop: 18 }}>
        {badges.map((b) => (
          <div key={b.id} className={`card hover${b.unlocked ? "" : ""}`}
            style={b.unlocked ? { borderColor: "var(--accent)" } : { opacity: 0.55 }}>
            <div style={{ fontSize: 30 }}>{b.unlocked ? (CAT_ICON[b.category] || "🏅") : "🔒"}</div>
            <b style={{ display: "block", marginTop: 6 }}>{b.title}</b>
            <p className="sub" style={{ fontSize: 12, marginTop: 4 }}>{b.description}</p>
            <span className={`badge ${b.unlocked ? "good" : ""}`}>
              {b.unlocked ? "Unlocked" : b.category || "hidden"}
            </span>
            {b.unlocked_at && (
              <p className="muted" style={{ fontSize: 11, marginTop: 8 }}>
                {new Date(b.unlocked_at).toLocaleDateString()}
              </p>
            )}
          </div>
        ))}
      </div>
    </Layout>
  );
}