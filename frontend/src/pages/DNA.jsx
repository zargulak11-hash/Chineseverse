import { useSearchParams } from "react-router-dom";
import Layout from "../components/Layout.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

const CATS = {
  listening: "👂",
  speaking: "🗣️",
  reading: "👀",
  writing: "✍️",
  grammar_usage: "🧩",
  vocabulary_retention: "📚",
};

export default function DNA() {
  const [params] = useSearchParams();
  const focus = params.get("focus");
  const { data: dna, error } = useApi("/dna");

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!dna) return <Layout><Loading>Sequencing your DNA…</Loading></Layout>;

  return (
    <Layout>
      <h1 className="h1">Your Learning DNA</h1>
      <p className="sub">
        Nine strands measured from every interaction. Build the weak ones —
        daily quests and companions will adapt.
      </p>

      <div className="card" style={{ marginTop: 18, textAlign: "center" }}>
        <div className="h1" style={{ fontSize: 42 }}>{dna.overall.toFixed(1)}</div>
        <p className="sub">overall</p>
        <div className="col" style={{ maxWidth: 520, margin: "0 auto" }}>
          <div className="hbar">
            <span className="badge warn">Weak · {dna.weak_areas.join(", ") || "none"}</span>
          </div>
          <div className="hbar">
            <span className="badge good">Strong · {dna.strong_areas.join(", ") || "none"}</span>
          </div>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", marginTop: 18 }}>
        {dna.skills.map((s) => {
          const cat = CATS[s.code] || "🧬";
          return (
            <div
              key={s.code}
              className="card"
              style={
                focus === s.code
                  ? { borderColor: "var(--accent)", boxShadow: "0 0 0 2px rgba(245,158,11,.25)" }
                  : {}
              }
            >
              <div className="row spread">
                <div className="row">
                  <span style={{ fontSize: 22 }}>{cat}</span>
                  <div>
                    <b>{s.name}</b>
                    <div className="muted" style={{ fontSize: 11.5 }}>
                      {s.code} · {s.xp} xp
                    </div>
                  </div>
                </div>
                <BadgeTone s={s} />
              </div>
              <Bar value={s.mastery} alt={s.status === "weak"} />
              <div className="muted" style={{ fontSize: 11.5, marginTop: 6 }}>
                {s.mastery.toFixed(0)}% · {s.status}
              </div>
            </div>
          );
        })}
      </div>
    </Layout>
  );
}

function BadgeTone({ s }) {
  const tone = s.status === "strong" ? "good" : s.status === "weak" ? "bad" : "accent";
  return <span className={`badge ${tone}`}>{s.status}</span>;
}