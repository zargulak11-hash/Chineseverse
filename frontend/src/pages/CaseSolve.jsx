import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Empty, Loading } from "../components/ui.jsx";

export default function CaseSolve() {
  const { scenarioId } = useParams();
  const navigate = useNavigate();
  const [sc, setSc] = useState(null);
  const [conclusion, setConclusion] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);

  useEffect(() => {
    api.get(`/world/scenarios/${scenarioId}`).then(setSc).catch((e) => setError(e.message));
  }, [scenarioId]);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!sc) return <Layout><Loading>Opening the file…</Loading></Layout>;

  const dialogs = sc.dialogues || [];

  async function solve() {
    if (!conclusion.trim() || sent) return;
    setSent(true);
    setResult(null);
    try {
      const r = await api.post(`/world/scenarios/${sc.slug}/solve`, { conclusion: conclusion.trim() });
      setResult(r);
    } catch (e) {
      setResult({ error: e.message });
    } finally {
      setSent(false);
    }
  }

  return (
    <Layout>
      <button className="btn ghost small" onClick={() => navigate(-1)}>← Back</button>
      <div className="row spread" style={{ marginTop: 10 }}>
        <div>
          <h1 className="h1"><Icon name="search" size={20} style={{ verticalAlign: -3, marginRight: 6 }} />{sc.title}</h1>
          <p className="sub">{sc.description}</p>
        </div>
        <span className="ilb">Case file</span>
      </div>

      {sc.case_data?.clues?.length > 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <h2 className="h2">🔍 Clues</h2>
          <ul style={{ marginTop: 8, paddingLeft: 18 }}>
            {sc.case_data.clues.map((clue, i) => (
              <li key={i} className="sub" style={{ marginTop: 4 }}>{clue}</li>
            ))}
          </ul>
        </div>
      )}

      {sc.case_data?.contradiction_text && (
        <div className="card" style={{ marginTop: 16, borderColor: "var(--bad)" }}>
          <h2 className="h2" style={{ color: "var(--bad)" }}>⚠️ Contradiction</h2>
          <p className="sub" style={{ marginTop: 8 }}>{sc.case_data.contradiction_text}</p>
        </div>
      )}

      <div className="card" style={{ marginTop: 16 }}>
        <h2 className="h2">Witness statements</h2>
        {dialogs.map((d) => (
          <div key={d.id} className="bubble npc" style={{ marginTop: 10 }}>
            <span className="speaker">🧑 {d.speaker}</span>
            {d.text}
            {d.pinyin && <span className="pinyin">{d.pinyin}</span>}
            {d.english && <span className="english">{d.english}</span>}
          </div>
        ))}
        {dialogs.length === 0 && <p className="sub">No statements recorded.</p>}
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h2 className="h2">Your verdict</h2>
        <p className="sub">Who is responsible, and why? Write your answer in Chinese.</p>
        <textarea
          className="input"
          rows={3}
          value={conclusion}
          onChange={(e) => setConclusion(e.target.value)}
          placeholder="e.g. 小王忘了锁门"
        />
        <button className="btn primary" style={{ marginTop: 12 }} onClick={solve} disabled={sent || !conclusion.trim()}>
          {sent ? "Checking…" : "Submit verdict"}
        </button>
      </div>

      {result && (
        <div className="card" style={{ marginTop: 16, borderColor: result.solved ? "var(--good)" : "var(--bad)" }}>
          <b className="sub" style={{ color: result.solved ? "var(--good)" : "var(--bad)" }}>
            <Icon name={result.solved ? "check" : "x"} size={14} style={{ verticalAlign: -2, marginRight: 4 }} />
            {result.solved ? "CASE SOLVED" : "Not quite right"}
          </b>
          <p className="sub" style={{ marginTop: 8, whiteSpace: "pre-wrap" }}>
            {typeof result.feedback === "string" ? result.feedback : JSON.stringify(result.feedback)}
          </p>
          {!result.solved && result.correct_answer && (
            <p className="sub" style={{ marginTop: 6 }}>Hint: {result.correct_answer}</p>
          )}
        </div>
      )}
    </Layout>
  );
}