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
//
// It reads as a sequence -- learn, the words, the grammar, practise -- on
// the same numbered rail as Foundation. Lesson text lines written as
// "你好 (nǐ hǎo) = hello" are shown as examples (Chinese, pinyin, meaning,
// listen); any other Chinese in the text can be tapped to hear it.

const EXAMPLE = /^\s*([^()=]*[㐀-鿿][^()=]*?)\s*[(（]([^)）]+)[)）]\s*=\s*(.+?)\s*$/;
const CJK_RUN = /([㐀-鿿][㐀-鿿，。！？、]*)/;

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

function Step({ n, title, children, done = false, now = false }) {
  return (
    <section className={`card fd-step${done ? " is-done" : ""}${now ? " is-now" : ""}`} aria-labelledby={`ld-step-${n}`}>
      <span className="fd-step-n" aria-hidden="true">{done ? <Icon name="check" size={16} /> : n}</span>
      <div className="fd-step-body">
        <h2 className="h2" id={`ld-step-${n}`}>{title}</h2>
        {children}
      </div>
    </section>
  );
}

export default function LessonDetail() {
  const { t, i18n } = useTranslation();
  const { lessonId } = useParams();
  const [lesson, setLesson] = useState(null);
  const [items, setItems] = useState(null);
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState("");
  const [locked, setLocked] = useState(false);
  const [playing, setPlaying] = useState(null);

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

  function say(text, id) {
    speakChinese(text, { onStart: () => setPlaying(id), onEnd: () => setPlaying(null) });
  }

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
  const done = status === "completed";

  // The lesson text, line by line: examples, prose, and paragraph breaks.
  const blocks = [];
  for (const raw of (lesson.content || "").split("\n")) {
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
  let n = 0;

  return (
    <Layout>
      <header className="page-head">
        <div>
          <Link to="/lessons" className="page-eyebrow ld-back"><Icon name="arrowLeft" size={13} /> {t("pages.lessonDetail.allLessons")}</Link>
          <h1 className="h1">{lesson.title}</h1>
          <p className="sub">{lesson.summary}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi"><span className="kpi-value">HSK {lesson.hsk_level}</span><span className="kpi-label">{t("pages.lessonDetail.level")}</span></div>
          <div className="kpi">
            <span className="kpi-value">{progress?.score != null && status !== "not_started" ? `${progress.score}%` : "—"}</span>
            <span className="kpi-label">{t(`lessonStatus.${status}`)}</span>
          </div>
        </div>
      </header>

      <div className="ws">
        <div className="ws-main fd-path">
          {lesson.content && (
            <Step n={++n} title={t("pages.lessonDetail.stepLearn")}>
              <div className="ld-content">
                {blocks.map((b, i) =>
                  b.kind === "gap" ? (
                    <div key={i} className="ld-gap" />
                  ) : b.kind === "text" ? (
                    <p key={i} className="ld-text"><Spoken text={b.text} /></p>
                  ) : (
                    <ul key={i} className="ld-examples">
                      {b.items.map((ex, k) => {
                        const id = `ex${i}-${k}`;
                        return (
                          <li key={k}>
                            <button type="button" className={`ld-example${playing === id ? " is-playing" : ""}`} onClick={() => say(ex.zh, id)}
                                    aria-label={`${t("pages.hanzi.hear")}: ${ex.zh}`}>
                              <span className="ld-ex-zh" lang="zh-CN">{ex.zh}</span>
                              <span className="ld-ex-py">{ex.py}</span>
                              <span className="ld-ex-gloss"><Spoken text={ex.gloss} plain /></span>
                              <span className="ld-ex-say" aria-hidden="true"><Icon name="volume" size={15} /></span>
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  )
                )}
              </div>
            </Step>
          )}

          {items.vocab.length > 0 && (
            <Step n={++n} title={t("pages.lessonDetail.wordsInLesson", { count: items.vocab.length })}>
              <div className="lesson-words">
                {items.vocab.map((w) => (
                  <button key={w.id} type="button" className={`lesson-word${playing === `w${w.id}` ? " is-playing" : ""}`}
                          onClick={() => say(w.simplified, `w${w.id}`)}>
                    <b lang="zh-CN">{w.simplified}</b>
                    <span className="lesson-word-py">{w.pinyin}</span>
                    <span className="sub">{w.meanings}</span>
                  </button>
                ))}
              </div>
            </Step>
          )}

          {items.grammar.length > 0 && (
            <Step n={++n} title={t("pages.lessonDetail.grammarInLesson", { count: items.grammar.length })}>
              <ul className="ld-grammar">
                {items.grammar.map((g) => (
                  <li key={g.id}>
                    <Link to={`/grammar/${g.id}`} className="ld-grammar-row">
                      <span className="ld-grammar-title">{g.title}</span>
                      {g.pattern && <span className="ld-pattern" lang="zh-CN">{g.pattern}</span>}
                      <Icon name="arrowRight" size={15} />
                    </Link>
                  </li>
                ))}
              </ul>
            </Step>
          )}

          <Step n={++n} title={t("pages.lessonDetail.stepPractise")} done={done} now={!done}>
            <div className="row" style={{ flexWrap: "wrap", margin: 0 }}>
              {practicable ? (
                <Link to={`/practice?lesson=${lesson.id}`} className="btn primary">
                  <Icon name="target" size={15} />
                  {done ? t("pages.lessonDetail.practiceAgain") : t("pages.lessonDetail.practiceToComplete")}
                </Link>
              ) : (
                <p className="sub">{t("pages.lessonDetail.noPractice")}</p>
              )}
              <Link to="/real-chinese" className="btn ghost">{t("pages.lessonDetail.tryInWorld")}</Link>
            </div>
            {practicable && !done && (
              <p className="sub" style={{ marginTop: 8, fontSize: "var(--text-xs)" }}>{t("pages.lessonDetail.passHint")}</p>
            )}
          </Step>
        </div>

        <aside className="ws-side">
          <div className={`card side-card ld-status${done ? " is-done" : ""}`}>
            <p className="side-title">{t("pages.lessonDetail.yourLesson")}</p>
            <span className={`badge ${done ? "good" : status === "in_progress" ? "accent" : ""}`}>
              {t(`lessonStatus.${status}`)}
              {progress?.score != null && status !== "not_started" ? ` · ${progress.score}%` : ""}
            </span>
            {practicable && !done && <p className="sub" style={{ marginTop: 8 }}>{t("pages.lessonDetail.passHint")}</p>}
            <ul className="ld-contents">
              {lesson.content && <li><Icon name="bookOpen" size={13} /> {t("pages.lessonDetail.stepLearn")}</li>}
              {items.vocab.length > 0 && <li><Icon name="type" size={13} /> {t("pages.lessonDetail.wordsInLesson", { count: items.vocab.length })}</li>}
              {items.grammar.length > 0 && <li><Icon name="seal" size={13} /> {t("pages.lessonDetail.grammarInLesson", { count: items.grammar.length })}</li>}
            </ul>
          </div>
          <Link to="/lessons" className="btn ghost">
            <Icon name="arrowLeft" size={14} /> {t("pages.lessonDetail.allLessons")}
          </Link>
        </aside>
      </div>
    </Layout>
  );
}
