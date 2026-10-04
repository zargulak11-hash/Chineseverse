import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { canSpeakChinese, speakChinese } from "../zhSpeech.js";

// One grammar point as a full textbook page (backend: services/grammar_lesson.py).
// The page always has the curriculum's own data -- pattern, every syllabus
// example with pinyin and a word-by-word gloss, the learner's real progress.
// The lesson itself (meaning, structure, mistakes, dialogue, exercises) is
// hand-written for core points, or an AI lesson generated once per topic
// and language; the page says which, and works without either.

function Speak({ text }) {
  const { t } = useTranslation();
  if (!canSpeakChinese()) return null;
  return (
    <button type="button" className="icon-btn gt-speak" aria-label={t("grammarPage.listen")} onClick={() => speakChinese(text, { whole: true })}>
      <Icon name="ear" size={15} />
    </button>
  );
}

function Zh({ zh, pinyin, tr, note, words }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  return (
    <li className="gt-ex">
      <div className="gt-ex-main">
        <div style={{ minWidth: 0 }}>
          <p className="gt-zh" lang="zh-CN">{zh}</p>
          {pinyin && <p className="gt-py">{pinyin}</p>}
          {tr && <p className="gt-tr">{tr}</p>}
          {note && <p className="gt-note"><Icon name="sparkles" size={13} /> {note}</p>}
        </div>
        <div className="gt-ex-tools">
          <Speak text={zh} />
          {words?.length > 0 && (
            <button type="button" className="btn small ghost" aria-expanded={open} onClick={() => setOpen(!open)}>
              {t(open ? "grammarPage.hideWords" : "grammarPage.words")}
            </button>
          )}
        </div>
      </div>
      {open && (
        <div className="gloss-row gt-words">
          {words.map((w, i) => (
            <span key={i} className="gloss-chip">
              <b lang="zh-CN">{w.text}</b>
              <span className="sub">{w.pinyin}</span>
              <span className="gloss-meaning">{w.meaning || "—"}</span>
            </span>
          ))}
        </div>
      )}
    </li>
  );
}

function Section({ title, icon, children }) {
  return (
    <section className="card gt-section">
      <h2 className="h2 gt-h"><Icon name={icon} size={17} /> {title}</h2>
      {children}
    </section>
  );
}

function ChooseExercise({ ex }) {
  const { t } = useTranslation();
  const [picked, setPicked] = useState(null);
  const done = picked !== null;
  return (
    <div className="gt-exercise">
      <p className="gt-exercise-q">{ex.prompt}</p>
      <div className="gt-options">
        {ex.options.map((o, i) => {
          const state = !done ? "" : i === ex.answer ? " good" : i === picked ? " bad" : "";
          return (
            <button key={i} type="button" className={`btn gt-option${state}`} disabled={done} lang="zh-CN" onClick={() => setPicked(i)}>
              {done && i === ex.answer && <Icon name="check" size={15} />}
              {done && i === picked && i !== ex.answer && <Icon name="x" size={15} />}
              {o}
            </button>
          );
        })}
      </div>
      {done && (
        <p className="gt-feedback" role="status">
          <b>{t(picked === ex.answer ? "grammarCheck.verdict.correct" : "grammarCheck.verdict.incorrect")}.</b> {ex.why}
          {" "}
          <button type="button" className="btn small ghost" onClick={() => setPicked(null)}>{t("grammarPage.again")}</button>
        </p>
      )}
    </div>
  );
}

function WriteExercise({ topicId, index, prompt, placeholder }) {
  const { t } = useTranslation();
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function check(e) {
    e.preventDefault();
    if (!answer.trim() || busy) return;
    setBusy(true);
    setError("");
    try {
      setResult(await api.post(`/grammar/${topicId}/check`, { answer: answer.trim(), exercise: index }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const tone = !result ? "" : ["correct", "acceptable"].includes(result.verdict) ? "good" : result.verdict === "unchecked" ? "" : result.verdict === "close" ? "accent" : "bad";
  return (
    <form className="gt-exercise" onSubmit={check}>
      <label className="gt-exercise-q" htmlFor={`gt-write-${index ?? "own"}`}>{prompt}</label>
      <div className="row gt-write-row">
        <input
          id={`gt-write-${index ?? "own"}`}
          className="input"
          lang="zh-CN"
          value={answer}
          onChange={(e) => { setAnswer(e.target.value); setResult(null); }}
          placeholder={placeholder}
          maxLength={120}
        />
        <button type="submit" className="btn primary" disabled={busy || !answer.trim()}>
          {busy ? t("grammarPage.checking") : t("grammarPage.check")}
        </button>
      </div>
      {error && <p className="formerr">{error}</p>}
      {result && (
        <div className={`pt-verdict ${tone}`} role="status">
          <Icon name={tone === "good" ? "check" : tone === "bad" ? "x" : "sparkles"} size={15} />
          <div style={{ minWidth: 0 }}>
            <b>{t(`grammarCheck.verdict.${result.verdict}`)}</b>
            {result.feedback && <p>{result.feedback}</p>}
            {result.issues.map((code) => <p key={code}>{t(`grammarCheck.issue.${code}`)}</p>)}
            {result.verdict === "unchecked" && !result.issues.length && <p>{t("grammarPage.uncheckedNote")}</p>}
            {result.uses_pattern === false && index == null && <p>{t("grammarPage.patternMissing")}</p>}
            {result.expected && !["correct", "acceptable"].includes(result.verdict) && (
              <p>{t("grammarPage.expected")}: <b lang="zh-CN">{result.expected}</b></p>
            )}
          </div>
        </div>
      )}
    </form>
  );
}

export default function GrammarTopic() {
  const { t, i18n } = useTranslation();
  const { topicId } = useParams();
  const { data: fetched, error } = useApi(`/grammar/${topicId}`);
  const key = `${topicId}:${i18n.language}`;
  // The generated page is kept apart from the GET's data and keyed by topic
  // and language, so a GET that lands after it can't wipe the new lesson.
  const [generated, setGenerated] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState("");
  const asked = useRef("");
  const data = generated?.key === key ? generated.page : fetched?.id === Number(topicId) ? fetched : null;

  // No authored or cached lesson yet: ask for the AI one once per topic and
  // language. The curriculum part of the page is already on screen.
  useEffect(() => {
    // No cleanup flag: StrictMode's second effect run would drop the only
    // request. A stale answer is harmless -- `data` only shows a generated
    // page whose key matches the current topic and language.
    if (!data?.can_generate || asked.current === key) return;
    asked.current = key;
    setGenerating(true);
    setGenError("");
    api.post(`/grammar/${topicId}/lesson`)
      .then((page) => setGenerated({ key, page }))
      .catch((e) => setGenError(e.message))
      .finally(() => setGenerating(false));
  }, [data?.can_generate, key, topicId]);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading /></Layout>;

  const lesson = data.lesson;
  const p = data.progress;
  const exercises = lesson?.exercises || [];
  const practiceTo = `/practice?source=grammar&level=${data.hsk_level}&topic=${data.id}`;

  return (
    <Layout>
      <div className="row" style={{ marginBottom: 16 }}>
        <Link to="/grammar" className="btn ghost small"><Icon name="arrowLeft" size={15} /> {t("grammarPage.back")}</Link>
      </div>
      <header className="page-head">
        <div style={{ minWidth: 0 }}>
          <div className="page-eyebrow">
            <Icon name="book" size={13} /> HSK {data.hsk_level === 7 ? "7–9" : data.hsk_level}
            {data.category ? ` · ${data.category}` : ""}
          </div>
          <h1 className="h1 gt-title">{lesson?.name || data.title}</h1>
          {lesson?.name && data.title !== lesson.name && <p className="sub" lang="zh-CN">{data.title}</p>}
          {(lesson?.summary || data.explanation) && <p className="gt-summary">{lesson?.summary || data.explanation}</p>}
          {/* Some syllabus "patterns" are only labels (主谓句2); a lesson's own
              structure formula says more, so it wins when there is one. */}
          {(lesson?.structure?.[0]?.formula || (data.pattern && data.pattern !== data.title && data.pattern)) && (
            <p className="gt-pattern" lang="zh-CN">{lesson?.structure?.[0]?.formula || data.pattern}</p>
          )}
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">{Math.round(p.mastery)}%</span>
            <span className="kpi-label">{t("grammarPage.mastery")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{p.times_practiced}</span>
            <span className="kpi-label">{t("grammarPage.practiced")}</span>
          </div>
        </div>
      </header>

      <div className="ws">
        <div className="ws-main">
          {generating && (
            <div className="card gt-section" role="status">
              <Loading>{t("grammarPage.preparing")}</Loading>
            </div>
          )}
          {!lesson && !generating && (
            <div className="card gt-section">
              <p className="sub">{genError || t("grammarPage.noLesson")}</p>
            </div>
          )}

          {lesson?.structure?.length > 0 && (
            <Section title={t("grammarPage.structure")} icon="route">
              <ul className="gt-structure">
                {lesson.structure.map((s, i) => (
                  <li key={i}>
                    <span className="gt-formula">{s.formula}</span>
                    {s.zh && (
                      <span className="gt-formula-ex">
                        <span lang="zh-CN">{s.zh}</span>
                        {s.pinyin && <span className="gt-py"> {s.pinyin}</span>}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {(lesson?.when_to_use?.length > 0 || lesson?.when_not?.length > 0) && (
            <div className="grid grid-2">
              {lesson.when_to_use?.length > 0 && (
                <section className="card gt-section gt-when good">
                  <h2 className="h2 gt-h"><Icon name="check" size={17} /> {t("grammarPage.whenToUse")}</h2>
                  <ul>{lesson.when_to_use.map((w, i) => <li key={i}>{w}</li>)}</ul>
                </section>
              )}
              {lesson.when_not?.length > 0 && (
                <section className="card gt-section gt-when bad">
                  <h2 className="h2 gt-h"><Icon name="x" size={17} /> {t("grammarPage.whenNot")}</h2>
                  <ul>{lesson.when_not.map((w, i) => <li key={i}>{w}</li>)}</ul>
                </section>
              )}
            </div>
          )}

          {lesson?.explanation?.length > 0 && (
            <Section title={t("grammarPage.explanation")} icon="bookOpen">
              <div className="gt-prose">{lesson.explanation.map((para, i) => <p key={i}>{para}</p>)}</div>
              {lesson.deeper?.length > 0 && (
                <details className="gt-deeper">
                  <summary>{t("grammarPage.deeper")}</summary>
                  <div className="gt-prose">{lesson.deeper.map((para, i) => <p key={i}>{para}</p>)}</div>
                </details>
              )}
              {lesson.register && <p className="gt-note"><Icon name="chat" size={13} /> {lesson.register}</p>}
            </Section>
          )}

          {lesson?.examples?.length > 0 && (
            <Section title={t("grammarPage.examples")} icon="sparkles">
              <ul className="gt-list">{lesson.examples.map((e, i) => <Zh key={i} {...e} />)}</ul>
            </Section>
          )}

          {(lesson?.negative?.length > 0 || lesson?.questions?.length > 0) && (
            <div className="grid grid-2">
              {lesson.negative?.length > 0 && (
                <Section title={t("grammarPage.negative")} icon="minus">
                  <ul className="gt-list">{lesson.negative.map((e, i) => <Zh key={i} {...e} />)}</ul>
                </Section>
              )}
              {lesson.questions?.length > 0 && (
                <Section title={t("grammarPage.questions")} icon="chat">
                  <ul className="gt-list">{lesson.questions.map((e, i) => <Zh key={i} {...e} />)}</ul>
                </Section>
              )}
            </div>
          )}

          {lesson?.mistakes?.length > 0 && (
            <Section title={t("grammarPage.mistakes")} icon="alert">
              <ul className="gt-mistakes">
                {lesson.mistakes.map((m, i) => (
                  <li key={i}>
                    <p className="gt-wrong"><Icon name="x" size={15} /> <s lang="zh-CN">{m.wrong}</s></p>
                    <p className="gt-right"><Icon name="check" size={15} /> <span lang="zh-CN">{m.right}</span>
                      {m.right_pinyin && <span className="gt-py"> {m.right_pinyin}</span>}</p>
                    <p className="gt-why">{m.why}</p>
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {lesson?.dialogue?.length > 0 && (
            <Section title={t("grammarPage.dialogue")} icon="users">
              <div className="chat gt-dialogue">
                {lesson.dialogue.map((d, i) => (
                  <div key={i} className={`bubble ${d.speaker === "B" ? "me" : "npc"}`}>
                    <span lang="zh-CN">{d.zh}</span>
                    {d.pinyin && <span className="pinyin">{d.pinyin}</span>}
                    {d.tr && <span className="english">{d.tr}</span>}
                  </div>
                ))}
              </div>
              <div className="row" style={{ marginTop: 12 }}>
                {canSpeakChinese() && (
                  <button type="button" className="btn small" onClick={() => speakChinese(lesson.dialogue.map((d) => d.zh).join(" "), { whole: true })}>
                    <Icon name="ear" size={15} /> {t("grammarPage.listenDialogue")}
                  </button>
                )}
              </div>
            </Section>
          )}

          {lesson?.similar?.length > 0 && (
            <Section title={t("grammarPage.similar")} icon="crosshair">
              <ul className="gt-similar">
                {lesson.similar.map((s, i) => (
                  <li key={i}>
                    {s.topic_id ? <Link to={`/grammar/${s.topic_id}`} className="gt-formula" lang="zh-CN">{s.pattern}</Link>
                      : <span className="gt-formula" lang="zh-CN">{s.pattern}</span>}
                    <p className="sub">{s.difference}</p>
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {data.examples.length > 0 && (
            <Section title={t("grammarPage.syllabus")} icon="flag">
              <ul className="gt-list">
                {data.examples.map((b, i) =>
                  b.kind === "heading" ? <li key={i} className="gt-sub" lang="zh-CN">{b.text}</li>
                    : b.kind === "phrases" ? (
                      <li key={i} className="gloss-row">{b.items.map((x) => <span key={x} className="gloss-chip" lang="zh-CN"><b>{x}</b></span>)}</li>
                    ) : <Zh key={i} zh={b.zh} pinyin={b.pinyin} words={b.words} />
                )}
              </ul>
            </Section>
          )}

          <Section title={t("grammarPage.tryIt")} icon="pen">
            {exercises.map((ex, i) => ex.type === "choose"
              ? <ChooseExercise key={i} ex={ex} />
              : <WriteExercise key={i} topicId={data.id} index={i} prompt={ex.prompt} placeholder={t("grammarPage.writePlaceholder")} />)}
            <WriteExercise
              topicId={data.id}
              index={null}
              prompt={t("grammarPage.ownSentence", { pattern: lesson?.structure?.[0]?.formula || data.pattern || data.title })}
              placeholder={t("grammarPage.writePlaceholder")}
            />
          </Section>
        </div>

        <aside className="ws-side">
          <div className="card side-card">
            <p className="side-title">{t("grammarPage.yourProgress")}</p>
            <Bar value={p.mastery} alt />
            <p className="sub" style={{ marginTop: 8 }}>
              {p.times_practiced === 0 ? t("grammarPage.notPracticed") : t("grammarPage.practicedTimes", { count: p.times_practiced })}
              {p.due ? ` · ${t("pages.vocabulary.due")}` : ""}
            </p>
            <Link to={practiceTo} className="btn primary" style={{ marginTop: 12 }}>
              <Icon name="target" size={15} /> {t("grammarPage.practice")}
            </Link>
            <p className="sub gt-note" style={{ marginTop: 8 }}>{t("grammarPage.practiceNote")}</p>
          </div>

          {data.vocabulary.length > 0 && (
            <div className="card side-card">
              <p className="side-title">{t("grammarPage.vocabulary")}</p>
              <ul className="gt-vocab">
                {data.vocabulary.map((v) => (
                  <li key={v.id}>
                    <b lang="zh-CN">{v.simplified}</b> <span className="sub">{v.pinyin}</span>
                    <span className="gloss-meaning"> {v.meaning}</span>
                    {v.status !== "new" && <span className={`badge${v.status === "mastered" ? " good" : ""}`}>{t(`grammarPage.wordStatus.${v.status}`, v.status)}</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {data.related.length > 0 && (
            <div className="card side-card">
              <p className="side-title">{t("grammarPage.related")}</p>
              <ul className="gt-related">
                {data.related.map((r) => (
                  <li key={r.id}><Link to={`/grammar/${r.id}`} lang="zh-CN">{r.title}</Link></li>
                ))}
              </ul>
            </div>
          )}

          <div className="card side-card">
            <p className="side-title">{t("grammarPage.more")}</p>
            <div className="side-links">
              <Link to={`/assistant?grammar=${data.id}`} className="btn"><Icon name="chat" size={15} /> {t("grammarPage.askAssistant")}</Link>
              {data.pet_teacher_cases > 0 && (
                <Link to="/pet-teacher" className="btn ghost"><Icon name="teach" size={15} /> {t("nav.petTeacher")}</Link>
              )}
            </div>
            {data.lesson_source && (
              <p className="sub gt-note" style={{ marginTop: 12 }}>
                {t(data.lesson_source === "ai" ? "grammarPage.sourceAi" : "grammarPage.sourceAuthored")}
              </p>
            )}
          </div>
        </aside>
      </div>
    </Layout>
  );
}
