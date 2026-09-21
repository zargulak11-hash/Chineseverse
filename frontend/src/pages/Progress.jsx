import { useEffect, useState } from "react";
import { api } from "../api.js";
import Layout from "../components/Layout.jsx";
import { Bar, Empty } from "../components/ui.jsx";

export default function Progress() {
  const [rows, setRows] = useState([]);
  const [lessons, setLessons] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.get("/progress").catch(() => []), api.get("/lessons").catch(() => [])])
      .then(([p, l]) => {
        setRows(p);
        setLessons(l);
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;

  const nameOf = (id) => lessons.find((l) => l.id === id)?.title || `Lesson ${id}`;
  const completed = rows.filter((r) => r.status === "completed").length;

  return (
    <Layout>
      <h1 className="h1">Lesson progress</h1>
      <p className="sub">{completed} of {lessons.length} completed</p>

      {rows.length === 0 && <Empty>Take the first lesson to start tracking here.</Empty>}

      <div className="col" style={{ marginTop: 16 }}>
        {[...rows].reverse().map((r) => {
          const pct = r.score ?? (r.status === "completed" ? 100 : 0);
          return (
            <div key={r.id} className="card">
              <div className="row spread">
                <div className="row">
                  <b>{nameOf(r.lesson_id)}</b>
                  <span className={`badge ${r.status === "completed" ? "good" : r.status === "in_progress" ? "accent" : ""}`}>
                    {r.status}
                  </span>
                </div>
                <span className="muted">{new Date(r.completed_at || r.created_at).toLocaleDateString()}</span>
              </div>
              <div className="hbar" style={{ marginTop: 10 }}>
                <Bar value={pct} />
                <span style={{ width: 36, textAlign: "right" }}>{pct}%</span>
              </div>
            </div>
          );
        })}
      </div>
    </Layout>
  );
}