import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Empty } from "../components/ui.jsx";

export default function Lessons() {
  const [lessons, setLessons] = useState([]);
  const [progress, setProgress] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      api.get("/lessons"),
      api.get("/progress").catch(() => []),
    ])
      .then(([ls, ps]) => {
        setLessons(ls);
        setProgress(ps);
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;

  const statusFor = (id) => {
    const p = progress.filter((x) => x.lesson_id === id).sort((a, b) => b.id - a.id)[0];
    return p?.status || "not_started";
  };

  const grouped = lessons.reduce((acc, l) => {
    (acc[l.hsk_level || 1] = acc[l.hsk_level || 1] || []).push(l);
    return acc;
  }, {});
  const levels = [...lessons.map((l) => l.hsk_level || 1)]
    .filter((v, i, a) => a.indexOf(v) === i)
    .sort((a, b) => a - b);

  return (
    <Layout>
      <h1 className="h1">Lessons</h1>
      <p className="sub">Structured lessons to build the grammar behind every conversation.</p>
      {levels.map((lvl) => (
        <div key={lvl} style={{ marginTop: 18 }}>
          <h2 className="h2">HSK {lvl}</h2>
          <div className="grid cards" style={{ marginTop: 10 }}>
            {grouped[lvl].map((l) => {
              const s = statusFor(l.id);
              const icon =
                s === "completed" ? "check" : s === "in_progress" ? "book" : "book";
              return (
                <Link to={`/lessons/${l.id}`} key={l.id}>
                  <div className="card hover" style={{ minHeight: 130 }}>
                    <div className="ic">
                      <Icon name={icon} size={17} />
                    </div>
                    <b style={{ display: "block", marginTop: 6 }}>{l.title}</b>
                    {l.summary && (
                      <p className="sub" style={{ fontSize: 12, marginTop: 6 }}>
                        {l.summary}
                      </p>
                    )}
                    <span className={`badge ${s === "completed" ? "good" : ""}`}>{s}</span>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      ))}
      {lessons.length === 0 && <Empty>No lessons yet.</Empty>}
    </Layout>
  );
}