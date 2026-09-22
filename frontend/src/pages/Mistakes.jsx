import { api } from "../api.js";
import Layout from "../components/Layout.jsx";
import { Empty } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

export default function Mistakes() {
  const { data, setData, error, setError } = useApi("/mistakes");
  const mistakes = data || [];

  async function master(id) {
    try {
      const updated = await api.patch(`/mistakes/${id}`, { mastered: true });
      setData((ms) => (ms || []).map((m) => (m.id === id ? updated : m)));
    } catch (e) {
      setError(e.message);
    }
  }

  if (error) return <Layout><Empty>{error}</Empty></Layout>;

  const open = mistakes.filter((m) => !m.mastered);
  const done = mistakes.filter((m) => m.mastered);

  return (
    <Layout>
      <h1 className="h1">Mistakes lab</h1>
      <p className="sub">Every slip is data. Master them and your DNA adapts with you.</p>

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
                  <span className="badge bad">×{m.occurrences}</span>
                  <button className="btn small" onClick={() => master(m.id)}>
                    Mastered ✓
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