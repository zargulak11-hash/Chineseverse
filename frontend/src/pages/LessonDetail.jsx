import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.js";
import Layout from "../components/Layout.jsx";
import { Empty, Loading } from "../components/ui.jsx";

export default function LessonDetail() {
  const { lessonId } = useParams();
  const { user } = useAuth();
  const [lesson, setLesson] = useState(null);
  const [progressId, setProgressId] = useState(null);
  const [feedback, setFeedback] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      api.get(`/lessons/${lessonId}`),
      api.get("/progress").catch(() => []),
    ]).then(([l, ps]) => {
      setLesson(l);
      const mine = ps.find((p) => p.lesson_id === l.id);
      setProgressId(mine?.id || null);
    }).catch((e) => setError(e.message));
  }, [lessonId]);

  async function mark(status, score) {
    setFeedback("");
    try {
      if (progressId) {
        const p = await api.patch(`/progress/${progressId}`, { status, score });
        setProgressId(p.id);
      } else {
        const p = await api.post("/progress", {
          user_id: user.id,
          lesson_id: lesson.id,
          status,
          score,
        });
        setProgressId(p.id);
      }
      setFeedback("Saved — DNA updated.");
    } catch (err) {
      setFeedback(err.message);
    }
  }

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!lesson) return <Layout><Loading /></Layout>;

  return (
    <Layout>
      <Link to="/lessons" className="sub">← All lessons</Link>
      <div className="row spread" style={{ marginTop: 10 }}>
        <h1 className="h1">{lesson.title}</h1>
        <span className="badge accent">HSK {lesson.hsk_level}</span>
      </div>
      <p className="sub">{lesson.summary}</p>

      <div className="card flat" style={{ marginTop: 16, background: "transparent" }}>
        {lesson.content &&
          lesson.content.split("\n").map((line, i) =>
            line.trim() ? (
              <p key={i} style={{ fontSize: 15 }}>
                {line}
              </p>
            ) : (
              <div key={i} style={{ height: 8 }} />
            )
          )}
      </div>

      <div className="row" style={{ marginTop: 18 }}>
        <button className="btn primary" onClick={() => mark("completed", 100)}>
          Mark complete
        </button>
        <button className="btn" onClick={() => mark("in_progress", 50)}>
          Keep practicing
        </button>
        <Link to="/world">
          <button className="btn ghost">Try it in the world</button>
        </Link>
      </div>
      {feedback && <p className="sub" style={{ marginTop: 10 }}>{feedback}</p>}
    </Layout>
  );
}