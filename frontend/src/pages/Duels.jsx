import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { animalFace } from "../components/AnimalEmoji.jsx";
import Layout from "../components/Layout.jsx";
import { Empty } from "../components/ui.jsx";

export default function Duels() {
  const navigate = useNavigate();
  const [duels, setDuels] = useState([]);
  const [open, setOpen] = useState(false);
  const [opponent, setOpponent] = useState("Buddy");
  const [my, setMy] = useState(null);
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    api.get("/duels").then(setDuels).catch((e) => setError(e.message));
    api.get("/dashboard").then(setMy).catch(() => {});
  }, []);

  async function start() {
    setError("");
    setStarting(true);
    try {
      const d = await api.post("/duels", {
        opponent_username: opponent === "Buddy" ? "Buddy" : opponent,
      });
      navigate(`/duels/${d.id}`);
    } catch (e) {
      setError(e.message);
    } finally {
      setStarting(false);
    }
  }

  const mySlug = my?.animal?.slug;

  return (
    <Layout>
      <div className="row spread">
        <div>
          <h1 className="h1">DNA duels</h1>
          <p className="sub">
            Rapid-fire word battles. The questions are picked from your weakest strand.
          </p>
        </div>
        <button className="btn primary" onClick={() => setOpen(true)}>⚔️ New duel</button>
      </div>

      {open && (
        <div className="modal">
          <div className="card">
            <h2 className="h2">Challenge someone</h2>
            <div className="field" style={{ marginTop: 12 }}>
              <label>Opponent</label>
              <input
                className="input"
                value={opponent}
                onChange={(e) => setOpponent(e.target.value)}
                placeholder="Buddy or a friend's username"
              />
            </div>
            {error && <p className="formerr">{error}</p>}
            <div className="row">
              <button className="btn primary" onClick={start} disabled={starting}>
                {starting ? "Creating…" : "Start"}
              </button>
              <button className="btn ghost" onClick={() => setOpen(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      <div className="col" style={{ marginTop: 18 }}>
        {duels.map((d) => (
          <div key={d.id} className="card">
            <div className="duelbanner" style={{ padding: "0 0 14px" }}>
              <div className="row">
                <span style={{ fontSize: 40 }}>{mySlug ? animalFace(mySlug) : "🐾"}</span>
                <div className="col" style={{ gap: 2 }}>
                  <b>You</b>
                  <span className="ilb">{d.my_score ?? 0}</span>
                </div>
              </div>
              <span className="ilb">vs</span>
              <div className="row">
                <div className="col" style={{ gap: 2 }}>
                  <b>{d.opponent}</b>
                  <span className="ilb">{d.opp_score ?? 0}</span>
                </div>
                <span style={{ fontSize: 40 }}>🤖</span>
              </div>
            </div>
            <div className="row spread">
              <span className={`badge ${d.finished ? "good" : "accent"}`}>
                {d.finished ? (d.winner === d.opponent ? "Opponent won" : d.winner ? "You won 🎉" : "Draw") : "In progress"}
              </span>
              <Link to={`/duels/${d.id}`}>
                <button className="btn small">Open</button>
              </Link>
            </div>
          </div>
        ))}
      </div>
      {duels.length === 0 && <Empty>No duels yet. Challenge the Buddy to a first battle.</Empty>}
    </Layout>
  );
}