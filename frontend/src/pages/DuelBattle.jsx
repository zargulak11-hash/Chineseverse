import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import Layout from "../components/Layout.jsx";
import { Empty } from "../components/ui.jsx";

export default function DuelBattle() {
  const { duelId } = useParams();
  const [duel, setDuel] = useState(null);
  const [idx, setIdx] = useState(0);
  const [feedback, setFeedback] = useState(null);
  const [score, setScore] = useState(0);
  const [timer, setTimer] = useState(100);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const answered = useRef(0);

  useEffect(() => {
    api.get(`/duels/${duelId}`).then(setDuel).catch((e) => setError(e.message));
  }, [duelId]);

  useEffect(() => {
    if (!duel || duel.finished) return;
    const t = setInterval(() => {
      setTimer((p) => Math.max(0, p - 2.5));
    }, 100);
    return () => clearInterval(t);
  }, [duel, idx]);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!duel) return <Layout><Empty>Loading duel…</Empty></Layout>;

  const q = duel.questions?.[idx];

  async function answer(option) {
    if (busy || !q) return;
    setBusy(true);
    try {
      const r = await api.post(`/duels/${duel.id}/answer`, {
        index: q.index,
        answer: option || q.prompt,
        response_time_ms: Math.round((100 - timer) * 1500),
      });
      setFeedback(r);
      setScore(r.my_score ?? score);
      answered.current += 1;
      setTimer(100);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function finish() {
    setBusy(true);
    try {
      const d = await api.post(`/duels/${duel.id}/finish`);
      setDuel(d);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (duel.finished) {
    const meWon = duel.winner && duel.winner !== duel.opponent && duel.opponent !== "__buddy_ai__";
    return (
      <Layout>
        <div className="card center" style={{ maxWidth: 520, margin: "40px auto" }}>
          <div style={{ fontSize: 52 }}>{meWon == null ? "🤝" : meWon ? "🏆" : "😤"}</div>
          <h1 className="h1">{meWon == null ? "It was a draw!" : meWon ? "Victory" : duel.opponent + " won"}</h1>
          <p className="sub">You {duel.my_score ?? 0} · {duel.opponent} {duel.opp_score ?? 0}</p>
          <Link to="/duels">
            <button className="btn primary" style={{ marginTop: 14 }}>Back to duels</button>
          </Link>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <Link to="/duels" className="sub">← Forfeit duel</Link>
      <div className="card" style={{ marginTop: 12 }}>
        <div className="row spread">
          <span className="badge accent">{duel.challenge_type || "weakest strand"}</span>
          <span className="muted">Your score · {score}</span>
        </div>
        <div className="timerbar" style={{ marginTop: 12 }}>
          <div style={{ width: `${timer}%` }} />
        </div>
      </div>

      {q ? (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="row spread">
            <span className="ilb">Round {idx + 1}/{duel.questions.length}</span>
            <span className="ilb">{q.type}</span>
          </div>
          <h2 className="h2" style={{ marginTop: 14, fontSize: 22 }}>{q.prompt}</h2>

          {feedback && (
            <p className={`sub ${feedback.correct ? "" : ""}`} style={{ marginTop: 10 }}>
              {feedback.correct ? "✅ Correct" : "❌ Wrong answer"}
            </p>
          )}

          <div className="col" style={{ marginTop: 14 }}>
            {(q.options || []).map((opt) => (
              <button
                key={opt}
                className={`option${feedback && feedback.answer === opt && feedback.correct ? " correct" : ""}${
                  feedback && feedback.answer === opt && !feedback.correct ? " wrong" : ""
                }`}
                onClick={() => answer(opt)}
                disabled={busy || !!feedback}
              >
                {opt}
              </button>
            ))}
            {!q.options && (
              <button className="option" onClick={() => answer("")} disabled={busy || !!feedback}>
                {q.type === "recognition" ? "Say it" : "Submit guess"}
              </button>
            )}
          </div>

          <div className="row" style={{ marginTop: 16 }}>
            {feedback && (
              <>
                {idx + 1 < duel.questions.length ? (
                  <button className="btn primary" onClick={() => { setIdx(idx + 1); setFeedback(null); }} disabled={busy}>
                    Next round
                  </button>
                ) : (
                  <button className="btn primary" onClick={finish} disabled={busy}>
                    Finish duel
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      ) : (
        <Empty>No questions loaded.</Empty>
      )}
    </Layout>
  );
}