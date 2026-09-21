import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import Layout from "../components/Layout.jsx";
import { Empty } from "../components/ui.jsx";

export default function WorldMap() {
  const [locations, setLocations] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/world/locations").then(setLocations).catch((e) => setError(e.message));
  }, []);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;

  return (
    <Layout>
      <h1 className="h1">Chinese World</h1>
      <p className="sub">
        A living city. Walk into a place, meet an NPC, and hold a real conversation.
        Everything is unlocked with HSK progress.
      </p>

      <div className="mapgrid" style={{ marginTop: 18 }}>
        {locations.map((loc) => (
          <Link key={loc.slug} to={`/world/${loc.slug}`} className={loc.locked ? "locked" : ""}>
            <div className="card hover spot" style={{ borderColor: loc.locked ? undefined : loc.accent + "55" }}>
              <div className="ic">{loc.icon || "📍"}</div>
              <b>{loc.name}</b>
              <span className="sub">{loc.kind}</span>
              <p className="sub" style={{ fontSize: 12 }}>{loc.description}</p>
              {loc.locked ? (
                <span className="badge bad">Unlocks HSK {loc.unlock_level}</span>
              ) : (
                <span className="badge good">Open</span>
              )}
            </div>
          </Link>
        ))}
      </div>
    </Layout>
  );
}