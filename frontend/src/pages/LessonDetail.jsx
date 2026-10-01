import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { speakChinese } from "../zhSpeech.js";

// A lesson is read here and completed by its practice round: the backend
// marks it completed only when that server-graded round scores >= 70%
// (services/practice.py), so there is no self-awarded "mark complete".
export default function LessonDetail() {
  const { t, i18n } = useTranslation();
  const { lessonId } = useParams();
  const [lesson, setLesson] = useState(null);
  const [items, setItems] = useState(null);
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState("");
  const [locked, setLocked] = useState(false);

  useEffect(() => {
    setError("");
    setLocked(false);
    setLesson(null);
    Promise.all([
      api.get(`/lessons/${lessonId}`),
      api.get(`/lessons/${lessonId}/items`),
      api.get(`/progress?lesson_id=${lessonId}`),
    ])
      .then(([l, it, ps]) => {
        setLesson(l);
        setItems(it);
        setProgress(ps[0] || null);
      })
      // The lesson path is enforced by the server: a lesson the learner has
      // not reached yet comes back 403 lesson_locked (URL typed by hand, an
      // old bookmark, search...), and this page explains it instead.
      .catch((e) => (e.code === "lesson_locked" ? setLocked(true) : setError(e.message)));
  }, [lessonId, i18n.language]);

  if (locked) {
    return (
      <Layout>
        <div className="card lesson-locked">
          <Icon name="lock" size={28} />
          <h1 className="h1" style={{ marginTop: 12 }}>{t("pages.lessonDetail.lockedTitle")}</h1>
          <p className="sub">{t("pages.lessonDetail.lockedText")}</p>
          <div className="row" style={{ marginTop: 16 }}>
            <Link to="/lessons" className="btn primary">{t("pages.lessonDetail.backToPath")}</Link>
          </div>
        </div>
      </Layout>
    );
  }
  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!lesson || !items) return <Layout><Loading /></Layout>;

  const status = progress?.status || "not_started";
  const practicable = items.vocab.length + items.grammar.length > 0;

  return (
    <Layout>
      <Link to="/lessons" className="sub">← {t("pages.lessonDetail.allLessons")}</Link>
      <div className="row spread" style={{ marginTop: 10, flexWrap: "wrap", gap: 8 }}>
        <h1 className="h1">{lesson.title}</h1>
        <span className="row" style={{ gap: 6 }}>
          <span className="badge accent">HSK {lesson.hsk_level}</span>
          <span className={`badge ${status === "completed" ? "good" : ""}`}>
            {t(`lessonStatus.${status}`)}
            {progress?.score != null && status !== "not_started" ? ` · ${progress.score}%` : ""}
          </span>
        </span>
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

      {items.vocab.length > 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <h2 className="h2">{t("pages.lessonDetail.wordsInLesson", { count: items.vocab.length })}</h2>
          <div className="lesson-words">
            {items.vocab.map((w) => (
              <button key={w.id} type="button" className="lesson-word" onClick={() => speakChinese(w.simplified)}>
                <b>{w.simplified}</b>
                <span className="sub" style={{ color: "var(--accent2)" }}>{w.pinyin}</span>
                <span className="sub">{w.meanings}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {items.grammar.length > 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <h2 className="h2">{t("pages.lessonDetail.grammarInLesson", { count: items.grammar.length })}</h2>
          <ul style={{ margin: "8px 0 0", paddingLeft: 18, lineHeight: 1.8 }}>
            {items.grammar.map((g) => (
              <li key={g.id}>
                <b>{g.title}</b> {g.pattern && <span className="sub">— {g.pattern}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="row" style={{ marginTop: 18, flexWrap: "wrap" }}>
        {practicable ? (
          <Link to={`/practice?lesson=${lesson.id}`}>
            <button className="btn primary">
              <Icon name="target" size={15} style={{ verticalAlign: -2, marginRight: 6 }} />
              {status === "completed" ? t("pages.lessonDetail.practiceAgain") : t("pages.lessonDetail.practiceToComplete")}
            </button>
          </Link>
        ) : (
          <p className="sub">{t("pages.lessonDetail.noPractice")}</p>
        )}
        <Link to="/world">
          <button className="btn ghost">{t("pages.lessonDetail.tryInWorld")}</button>
        </Link>
      </div>
      {practicable && status !== "completed" && (
        <p className="sub" style={{ marginTop: 8, fontSize: 12 }}>{t("pages.lessonDetail.passHint")}</p>
      )}
    </Layout>
  );
}
