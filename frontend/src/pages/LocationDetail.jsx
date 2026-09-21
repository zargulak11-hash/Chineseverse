import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import Layout from "../components/Layout.jsx";
import { Empty } from "../components/ui.jsx";

export default function LocationDetail() {
  const { slug } = useParams();
  const [loc, setLoc] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get(`/world/locations/${slug}`).then(setLoc).catch((e) => setError(e.message));
  }, [slug]);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!loc) return <Layout><Empty>Entering…</Empty></Layout>;

  return (
    <Layout>
      <Link to="/world" className="sub">← World map</Link>
      <div className="row spread" style={{ marginTop: 10 }}>
        <div className="row">
          <span style={{ fontSize: 44 }}>{loc.icon}</span>
          <div>
            <h1 className="h1">{loc.name}</h1>
            <p className="sub">{loc.kind}</p>
          </div>
        </div>
      </div>
      <p className="sub" style={{ marginTop: 10 }}>{loc.description}</p>

      {loc.npcs?.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <h2 className="h2">People here</h2>
          <div className="grid cards">
            {loc.npcs.map((n) => (
              <div key={n.id} className="card">
                <b>{n.name}</b>
                <span className="badge accent">{n.role}</span>
                <p className="sub" style={{ fontSize: 12.5, marginTop: 8 }}>{n.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {loc.scenarios?.length > 0 && (
        <div style={{ marginTop: 22 }}>
          <h2 className="h2">Conversations</h2>
          <div className="col">
            {loc.scenarios.map((s) => (
              <div key={s.id} className="card hover"
                onClick={() => (s.is_case ? null : null)} style={{ cursor: "default" }}>
                <div className="row spread">
                  <div className="row">
                    <span style={{ fontSize: 22 }}>{s.is_case ? "🕵️" : "💬"}</span>
                    <div>
                      <b>{s.title}</b>
                      <p className="sub" style={{ fontSize: 12 }}>{s.description}</p>
                    </div>
                  </div>
                  <div className="row">
                    <span className="ilb">HSK {s.min_hsk_level}</span>
                    <span className="ilb">★{s.difficulty}</span>
                    {s.is_case ? (
                      <Link to={`/cases/${s.slug}`}>
                        <button className="btn small">Solve case</button>
                      </Link>
                    ) : (
                      <Link to={`/conversation/${s.slug}`}>
                        <button className="btn small primary">Talk</button>
                      </Link>
                    )}
                  </div>
                </div>
                {s.requires_voice && <p className="sub" style={{ fontSize: 11.5, marginTop: 6 }}>🎙️ This conversation uses voice.</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </Layout>
  );
}