import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { speakChinese } from "../zhSpeech.js";

// A lesson's start screen (backend services/lesson_flow.py, GET
// /lessons/{id}/flow). The lesson itself is ONE played sequence of short
// screens (/practice?source=lesson_play): each phrase taught on its own
// screen and practised at once, earlier ones brought back, then recall and
// use. Finishing it with >= 70% of the graded answers completes the lesson
// on the server, exactly like the lesson's round (services/practice.py) --
// opening this page or reading a teaching screen completes nothing.
//
// This page only says what the lesson is for, shows what it teaches, and
// starts it. Everything else stays one tap away in "Lesson reference":
// the phrases with their words, the words, the grammar, the original
// text, and single-skill drills (practice source "lesson_step").

const EXAMPLE = /^\s*([^()=]*[㐀-鿿][^()=]*?)\s*[(（]([^)）]+)[)）]\s*=\s*(.+?)\s*$/;
const CJK_RUN = /([㐀-鿿][㐀-鿿，。！？、]*)/;
const DRILLS = ["listen", "build", "recall", "apply"];
const DRILL_ICON = { listen: "ear", build: "type", recall: "clock", apply: "chat" };
const PREVIEW = 4;

function Spoken({ text, plain = false }) {
  // Prose with its Chinese runs made audible (plain: inside something that
  // is itself a button, they are only marked as Chinese).
  const { t } = useTranslation();
  return text.split(CJK_RUN).map((part, i) =>
    i % 2 === 1 && plain ? (
      <span key={i} lang="zh-CN">{part}</span>
    ) : i % 2 === 1 ? (
      <button key={i} type="button" className="ld-zh-run" lang="zh-CN" onClick={() => speakChinese(part)}
              aria-label={`${t("pages.hanzi.hear")}: ${part}`}>
        {part}
      </button>
    ) : part
  );
}

// The lesson text as it always was (examples, prose, paragraph breaks).
function LessonText({ content }) {
  const { t } = useTranslation();
  const blocks = [];
  for (const raw of (content || "").split("\n")) {
    const line = raw.trim();
    if (!line) {
      blocks.push({ kind: "gap" });
      continue;
    }
    const m = line.match(EXAMPLE);
    if (m) {
      const last = blocks[blocks.length - 1];
      const ex = { zh: m[1].trim(), py: m[2].trim(), gloss: m[3].replace(/\.$/, "").trim() };
      if (last?.kind === "examples") last.items.push(ex);
      else blocks.push({ kind: "examples", items: [ex] });
    } else {
      blocks.push({ kind: "text", text: line });
    }
  }
  return (
    <div className="ld-content">
      {blocks.map((b, i) =>
        b.kind === "gap" ? (
          <div key={i} className="ld-gap" />
        ) : b.kind === "text" ? (
          <p key={i} className="ld-text"><Spoken text={b.text} /></p>
        ) : (
          <ul key={i} className="ld-examples">
            {b.items.map((ex, k) => (
              <li key={k}>
                <button type="button" className="ld-example" onClick={() => speakChinese(ex.zh)}
                        aria-label={`${t("pages.hanzi.hear")}: ${ex.zh}`}>
                  <span className="ld-ex-zh" lang="zh-CN">{ex.zh}</span>
                  <span className="ld-ex-py">{ex.py}</span>
                  <span className="ld-ex-gloss"><Spoken text={ex.gloss} plain /></span>
                  <span className="ld-ex-say" aria-hidden="true"><Icon name="volume" size={15} /></span>
                </button>
              </li>
            ))}
          </ul>
        )
      )}
    </div>
  );
}

// Everything the lesson contains, for looking things up -- not the way through it.
function Reference({ flow, lesson }) {
  const { t } = useTranslation();
  return (
    <details className="card ld-ref" style={{ marginTop: 16 }}>
      <summary>{t("lessonPlay.reference")}</summary>
      <p className="sub">{t("lessonPlay.referenceBody")}</p>
      {flow.phrases.length > 0 && (
        <ul className="lf-grammar">
          {flow.phrases.map((p) => (
            <li key={p.zh}>
              <button type="button" className="ld-zh-run" lang="zh-CN" onClick={() => speakChinese(p.zh.replace(/…/g, ""))}>{p.zh}</button>
              <span className="sub">{[p.pinyin, p.meaning].filter(Boolean).join(" — ")}</span>
              <span className="sub">{p.words.filter((w) => w.meaning).map((w) => `${w.text} ${w.meaning}`).join(" · ")}</span>
            </li>
          ))}
        </ul>
      )}
      {flow.words.length > 0 && (
        <>
          <h2 className="h2" style={{ marginTop: 16 }}>{t("pages.lessonDetail.wordsInLesson", { count: flow.words.length })}</h2>
          <div className="lesson-words">
            {flow.words.map((w) => (
              <button key={w.id} type="button" className="lesson-word" onClick={() => speakChinese(w.zh)}>
                <b lang="zh-CN">{w.zh}</b>
                <span className="lesson-word-py">{w.pinyin}</span>
                <span className="sub">{w.meaning}</span>
              </button>
            ))}
          </div>
        </>
      )}
      {flow.grammar.length > 0 && (
        <>
          <h2 className="h2" style={{ marginTop: 16 }}>{t("pages.lessonDetail.grammarInLesson", { count: flow.grammar.length })}</h2>
          <ul className="lf-grammar">
            {flow.grammar.map((g) => (
              <li key={g.id}>
                <div className="row spread" style={{ margin: 0, gap: 8, flexWrap: "wrap" }}>
                  <b>{g.title}</b>
                  {g.pattern && <span className="ld-pattern" lang="zh-CN">{g.pattern}</span>}
                </div>
                {g.explanation && <p className="sub">{g.explanation}</p>}
                <Link to={`/grammar/${g.id}`} className="btn small ghost">{t("lessonFlow.openGrammar")} <Icon name="arrowRight" size={13} /></Link>
              </li>
            ))}
          </ul>
        </>
      )}
      {lesson.content && (
        <>
          <h2 className="h2" style={{ marginTop: 16 }}>{t("lessonFlow.wholeText")}</h2>
          <LessonText content={lesson.content} />
        </>
      )}
      {flow.stages.some((s) => s.available) && (
        <>
          <h2 className="h2" style={{ marginTop: 16 }}>{t("lessonPlay.drills")}</h2>
          <p className="sub">{t("lessonPlay.drillsBody")}</p>
          <div className="row" style={{ gap: 8, flexWrap: "wrap", margin: 0 }}>
            {DRILLS.map((key) => {
              const s = flow.stages.find((x) => x.key === key);
              if (!s?.available) return null;
              return (
                <Link key={key} to={`/practice?source=lesson_step&lesson=${lesson.id}&step=${key}`} className="btn small ghost">
                  <Icon name={DRILL_ICON[key]} size={13} /> {t(`lessonFlow.stage.${key}`)}
                  {s.played > 0 ? ` · ${Math.round(s.best)}%` : ""}
                </Link>
              );
            })}
          </div>
        </>
      )}
    </details>
  );
}

export default function LessonDetail() {
  const { t, i18n } = useTranslation();
  const { lessonId } = useParams();
  const [lesson, setLesson] = useState(null);
  const [flow, setFlow] = useState(null);
  const [error, setError] = useState("");
  const [locked, setLocked] = useState(false);

  useEffect(() => {
    setError("");
    setLocked(false);
    setLesson(null);
    setFlow(null);
    Promise.all([api.get(`/lessons/${lessonId}`), api.get(`/lessons/${lessonId}/flow`)])
      .then(([l, f]) => {
        setLesson(l);
        setFlow(f);
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
  if (!lesson || !flow) return <Layout><Loading /></Layout>;

  const status = flow.check.status;
  const done = status === "completed";
  const play = flow.play;
  const preview = flow.phrases.filter((p) => !p.template).slice(0, PREVIEW);
  const playTo = `/practice?source=lesson_play&lesson=${lesson.id}`;
  const checkTo = `/practice?lesson=${lesson.id}`;

  return (
    <Layout>
      <header className="page-head">
        <div>
          <Link to="/lessons" className="page-eyebrow ld-back"><Icon name="arrowLeft" size={13} /> {t("pages.lessonDetail.allLessons")}</Link>
          <h1 className="h1">{lesson.title}</h1>
          {lesson.summary && <p className="sub">{t("lessonFlow.goal", { goal: lesson.summary, interpolation: { escapeValue: false } })}</p>}
        </div>
        <div className="kpi-row">
          <div className="kpi"><span className="kpi-value">HSK {lesson.hsk_level}</span><span className="kpi-label">{t("pages.lessonDetail.level")}</span></div>
          <div className="kpi">
            <span className="kpi-value">{flow.check.score != null && status !== "not_started" ? `${flow.check.score}%` : "—"}</span>
            <span className="kpi-label">{t(`lessonStatus.${status}`)}</span>
          </div>
        </div>
      </header>

      <div className="ws">
        <div className="ws-main">
          {flow.pinyin_first && (
            <div className="card lf-note">
              <Icon name="ear" size={18} />
              <div>
                <b>{t("lessonFlow.pinyinFirstTitle")}</b>
                <p className="sub" style={{ margin: "4px 0 8px" }}>{t("lessonFlow.pinyinFirstBody")}</p>
                <Link to="/foundation" className="btn small">{t("lessonFlow.pinyinFirstGo")}</Link>
              </div>
            </div>
          )}

          <section className={`card ld-start${done ? " is-done" : ""}`} aria-labelledby="ld-start-title">
            <h2 className="h2" id="ld-start-title">{t("lessonPlay.youWillLearn")}</h2>
            {preview.length > 0 ? (
              <ul className="ld-preview">
                {preview.map((p) => (
                  <li key={p.zh}>
                    <b lang="zh-CN">{p.zh}</b>
                    {p.meaning && <span className="sub"> — {p.meaning}</span>}
                  </li>
                ))}
              </ul>
            ) : (
              flow.words.length > 0 && (
                <ul className="ld-preview">
                  {flow.words.slice(0, 6).map((w) => (
                    <li key={w.id}><b lang="zh-CN">{w.zh}</b> <span className="sub">{w.meaning}</span></li>
                  ))}
                </ul>
              )
            )}
            {play.available ? (
              <>
                <p className="sub">{t("lessonPlay.howItGoes", { screens: play.screens })}</p>
                <div className="row" style={{ gap: 8, flexWrap: "wrap", margin: 0 }}>
                  <Link to={playTo} className="btn primary">
                    <Icon name="play" size={15} />
                    {done ? t("lessonPlay.playAgain") : play.played ? t("lessonPlay.tryAgain") : t("lessonPlay.start")}
                  </Link>
                  {flow.known_level && !done && flow.check.practicable && (
                    <Link to={checkTo} className="btn ghost"><Icon name="award" size={15} /> {t("lessonPlay.testOut")}</Link>
                  )}
                </div>
                {play.best != null && <p className="sub">{t("lessonFlow.best", { score: Math.round(play.best) })}</p>}
                {flow.known_level && !done && <p className="sub">{t("lessonPlay.testOutBody")}</p>}
              </>
            ) : flow.check.practicable ? (
              // Too little material for a played lesson: its own round, as before.
              <div className="row" style={{ gap: 8, flexWrap: "wrap", margin: 0 }}>
                <Link to={checkTo} className="btn primary">
                  <Icon name="target" size={15} />
                  {done ? t("pages.lessonDetail.practiceAgain") : t("pages.lessonDetail.practiceToComplete")}
                </Link>
              </div>
            ) : (
              <p className="sub">{t("pages.lessonDetail.noPractice")}</p>
            )}
            {!done && (play.available || flow.check.practicable) && (
              <p className="sub" style={{ fontSize: "var(--text-xs)" }}>{t("pages.lessonDetail.passHint")}</p>
            )}
          </section>

          <Reference flow={flow} lesson={lesson} />
        </div>

        <aside className="ws-side">
          <div className={`card side-card ld-status${done ? " is-done" : ""}`}>
            <p className="side-title">{t("pages.lessonDetail.yourLesson")}</p>
            <span className={`badge ${done ? "good" : status === "in_progress" ? "accent" : ""}`}>
              {t(`lessonStatus.${status}`)}
              {flow.check.score != null && status !== "not_started" ? ` · ${flow.check.score}%` : ""}
            </span>
            <p className="sub" style={{ marginTop: 8 }}>{t("lessonPlay.sideHow")}</p>
          </div>
          <Link to="/real-chinese" className="btn ghost">{t("pages.lessonDetail.tryInWorld")}</Link>
          <Link to="/lessons" className="btn ghost">
            <Icon name="arrowLeft" size={14} /> {t("pages.lessonDetail.allLessons")}
          </Link>
        </aside>
      </div>
    </Layout>
  );
}
