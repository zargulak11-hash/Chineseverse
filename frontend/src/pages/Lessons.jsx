import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

// The lesson path. Every state here (completed / current / available /
// locked) comes from GET /api/lessons/path -- the backend also refuses to
// open, practice or complete a locked lesson, so this page only explains the
// path; it is not what enforces it. One HSK level is shown at a time so the
// learner sees their next step, not a wall of 100+ lessons.
const NODE_CLASS = { completed: "is-done", current: "is-current", locked: "is-locked", available: "" };

export default function Lessons() {
  const { t } = useTranslation();
  const { data: path, error } = useApi("/lessons/path");
  const [level, setLevel] = useState(null);
  // ?level=N (from the journey page) opens that level; otherwise the current one.
  const [params] = useSearchParams();
  const wanted = Number(params.get("level")) || null;

  useEffect(() => {
    if (path && level === null) {
      const last = path.levels[path.levels.length - 1];
      const asked = wanted && path.levels.some((lv) => lv.level === wanted) ? wanted : null;
      setLevel(asked ?? path.current_level ?? last?.level ?? 1);
    }
  }, [path, level, wanted]);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!path) return <Layout><Loading /></Layout>;
  if (path.levels.length === 0) return <Layout><Empty>{t("pages.lessons.empty")}</Empty></Layout>;

  const allLessons = path.levels.flatMap((lv) => lv.lessons);
  const current = allLessons.find((l) => l.id === path.current_lesson_id) || null;
  const shown = path.levels.find((lv) => lv.level === level) || path.levels[0];
  const currentLevel = path.levels.find((lv) => lv.level === path.current_level);
  const pct = (done, total) => (total ? (done / total) * 100 : 0);

  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow">
            <Icon name="book" size={13} /> {t("pages.lessons.eyebrow")}
          </div>
          <h1 className="h1">{t("pages.lessons.title")}</h1>
          <p className="sub">{t("pages.lessons.subtitle")}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">{path.completed}/{path.total}</span>
            <span className="kpi-label">{t("pages.lessons.completedKpi")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{path.current_level ? `HSK ${path.current_level}` : "—"}</span>
            <span className="kpi-label">{t("pages.lessons.currentLevel")}</span>
          </div>
          {currentLevel && (
            <div className="kpi">
              <span className="kpi-value">{currentLevel.completed}/{currentLevel.total}</span>
              <span className="kpi-label">{t("pages.lessons.levelKpi")}</span>
            </div>
          )}
        </div>
      </header>

      <div className="ws">
        <div className="ws-main">
          <h2 className="h2 section-title">{t("pages.lessons.upNext")}</h2>
          {path.exam_level ? (
            // Every lesson of this level is done: its final exam opens the next one.
            <div className="card lesson-next">
              <div className="roadmap-card-head">
                <div className="row" style={{ gap: 8 }}>
                  <span className="badge accent">HSK {path.exam_level}</span>
                  <span className="badge accent">{t("exam.eyebrow")}</span>
                </div>
              </div>
              <h3 className="h2" style={{ marginTop: 12 }}>{t("exam.title", { level: path.exam_level })}</h3>
              <p className="sub">
                {path.exam_level < 9
                  ? t("exam.lessonsReady", { level: path.exam_level, next: path.exam_level + 1 })
                  : t("exam.lessonsReadyLast")}
              </p>
              <div className="row" style={{ marginTop: 16 }}>
                <Link to={`/exam/${path.exam_level}`} className="btn primary">
                  <Icon name="award" size={15} /> {t("exam.takeExam")}
                </Link>
              </div>
            </div>
          ) : current ? (
            <div className="card lesson-next">
              <div className="roadmap-card-head">
                <div className="row" style={{ gap: 8 }}>
                  <span className="badge accent">HSK {path.current_level}</span>
                  <span className="badge accent">{t("pages.lessons.status.current")}</span>
                </div>
              </div>
              <h3 className="h2" style={{ marginTop: 12 }}>{current.title}</h3>
              {current.summary && <p className="sub lesson-clamp">{current.summary}</p>}
              <div className="row" style={{ marginTop: 16 }}>
                <Link to={`/lessons/${current.id}`} className="btn primary">
                  <Icon name="play" size={15} /> {t("pages.lessons.start")}
                </Link>
              </div>
            </div>
          ) : (
            <div className="card lesson-next">
              <div className="row">
                <Icon name="trophy" size={20} />
                <p className="sub" style={{ margin: 0 }}>{t("pages.lessons.pathDone")}</p>
              </div>
            </div>
          )}

          <div className="row lesson-levels" role="group" aria-label={t("pages.lessons.chooseLevel")}>
            {path.levels.map((lv) => (
              <button
                key={lv.level}
                type="button"
                className={`btn small${lv.level === shown.level ? " primary" : " ghost"}`}
                aria-pressed={lv.level === shown.level}
                onClick={() => setLevel(lv.level)}
              >
                {lv.status === "completed" && <Icon name="check" size={13} />}
                {lv.status === "locked" && <Icon name="lock" size={13} />}
                HSK {lv.level}
              </button>
            ))}
          </div>

          <h2 className="h2 section-title">
            HSK {shown.level} · {t("pages.lessons.lessonsInLevel", { done: shown.completed, total: shown.total })}
          </h2>
          {shown.status === "locked" && (
            <p className="sub lesson-level-note">
              <Icon name="lock" size={15} /> {t("pages.lessons.levelLocked", { level: shown.level - 1 })}
            </p>
          )}

          <ol className="roadmap-track lesson-path">
            {shown.lessons.map((l, i) => (
              <LessonStep key={l.id} lesson={l} index={i + 1} />
            ))}
          </ol>
        </div>

        <aside className="ws-side">
          <div className="card side-card">
            <p className="side-title">{t("pages.lessons.hskProgress")}</p>
            <div className="col">
              {path.levels.map((lv) => (
                <div key={lv.level} className="metric">
                  <div className="metric-head">
                    <span className="row" style={{ gap: 4 }}>
                      {lv.status === "completed" && <Icon name="check" size={13} />}
                      {lv.status === "locked" && <Icon name="lock" size={13} />}
                      HSK {lv.level}
                    </span>
                    <b>{lv.completed}/{lv.total}</b>
                  </div>
                  <Bar value={pct(lv.completed, lv.total)} alt={lv.status !== "current"} />
                </div>
              ))}
            </div>
          </div>

          <div className="card side-card">
            <p className="side-title">{t("pages.lessons.keepSharp")}</p>
            <div className="side-links">
              <Link to="/review" className="btn"><Icon name="clock" size={15} /> {t("nav.review")}</Link>
              <Link to="/mistakes" className="btn ghost"><Icon name="alert" size={15} /> {t("pages.lessons.reviewMistakes")}</Link>
            </div>
          </div>
        </aside>
      </div>
    </Layout>
  );
}

function LessonStep({ lesson, index }) {
  const { t } = useTranslation();
  const { status } = lesson;
  const locked = status === "locked";
  return (
    <li className={`roadmap-step ${NODE_CLASS[status]}`}>
      <div className="roadmap-node" aria-hidden="true">
        {status === "completed" ? <Icon name="check" size={18} /> : locked ? <Icon name="lock" size={16} /> : index}
      </div>
      <div className="card">
        <div className="roadmap-card-head">
          <b className="lesson-step-title">{lesson.title}</b>
          <span className={`badge${status === "completed" ? " good" : status === "current" ? " accent" : ""}`}>
            {t(`pages.lessons.status.${status}`)}
          </span>
        </div>
        {lesson.summary && <p className="sub lesson-step-summary lesson-clamp">{lesson.summary}</p>}
        <div className="row spread lesson-step-foot">
          <span className="sub">
            {locked
              ? t("pages.lessons.lockedReason")
              : !lesson.practicable
                ? t("pages.lessons.readingHint")
                : lesson.score > 0
                  ? t("pages.lessons.best", { score: lesson.score })
                  : ""}
          </span>
          {!locked && (
            <Link
              to={`/lessons/${lesson.id}`}
              className={`btn small${status === "current" ? " primary" : " ghost"}`}
            >
              {status === "completed"
                ? t("pages.lessons.review")
                : status === "current"
                  ? t("pages.lessons.start")
                  : t("pages.lessons.open")}
            </Link>
          )}
        </div>
      </div>
    </li>
  );
}
