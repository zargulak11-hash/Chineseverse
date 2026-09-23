import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import Layout from "../components/Layout.jsx";
import { Empty } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

// Where to actually re-earn mastery of each mistake type — mastery is
// never set by a click here, only by answering correctly again on one of
// these surfaces (see reinforce_mistake() in the backend).
const PRACTICE_ROUTE = {
  word: "/vocabulary",
  pinyin: "/duels",
  tone: "/duels",
  character: "/duels",
  grammar: "/world",
};

export default function Mistakes() {
  const navigate = useNavigate();
  const { data, setData, error, setError } = useApi("/mistakes");
  const mistakes = data || [];

  async function practice(m) {
    try {
      const updated = await api.patch(`/mistakes/${m.id}`, { request_retest: true });
      setData((ms) => (ms || []).map((x) => (x.id === m.id ? updated : x)));
    } catch (e) {
      setError(e.message);
    }
    navigate(PRACTICE_ROUTE[m.mistake_type] || "/vocabulary");
  }

  if (error) return <Layout><Empty>{error}</Empty></Layout>;

  const open = mistakes.filter((m) => !m.mastered);
  const done = mistakes.filter((m) => m.mastered);

  return (
    <Layout>
      <h1 className="h1">Mistakes lab</h1>
      <p className="sub">
        Every slip is data. Mastery is earned by getting it right again through
        voice, vocab review, a case, or a duel — not by a click here.
      </p>

      <div className="ranges" style={{ marginTop: 16 }}>
        <h2 className="h2">Still working on ({open.length})</h2>
        <div className="col">
          {open.map((m) => (
            <div key={m.id} className="card">
              <div className="row spread">
                <div>
                  <b>{m.question_text || m.reference}</b>
                  <p className="sub" style={{ marginTop: 4, fontSize: 13 }}>
                    You said: <em>{m.answer_given || "—"}</em>
                    {m.correct_answer && <> · correct: <b>{m.correct_answer}</b></>}
                  </p>
                </div>
                <div className="col" style={{ gap: 6, alignItems: "flex-end" }}>
                  <span className={`badge ${m.due_for_review ? "accent" : "bad"}`}>
                    {m.due_for_review ? "due now" : `×${m.occurrences}`}
                  </span>
                  <button className="btn small" onClick={() => practice(m)}>
                    Practice this →
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {done.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <h2 className="h2">Mastered ({done.length})</h2>
          <div className="grid cards">
            {done.map((m) => (
              <div key={m.id} className="card" style={{ opacity: 0.7 }}>
                <span className="badge good">✓ mastered</span>
                <p className="sub" style={{ marginTop: 8 }}>{m.question_text || m.reference}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      {mistakes.length === 0 && <Empty>No mistakes recorded yet. Go make some.</Empty>}
    </Layout>
  );
}
