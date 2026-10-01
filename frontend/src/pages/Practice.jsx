import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api.js";
import CompanionFigure from "../components/CompanionFigure.jsx";
import CompanionReaction from "../components/CompanionReaction.jsx";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Bar, Celebration, Empty, Loading, RingHero } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { speakChinese } from "../zhSpeech.js";

// One practice/review round. Everything that counts -- which option is
// correct, mastery, mistakes, Learning DNA, XP, lesson completion -- is
// decided by the backend (/api/practice); this page only shows what the
// server generated and posts back which option id was picked.
export default function Practice({ forceSource }) {
  const { t, i18n } = useTranslation();
  const [params] = useSearchParams();
  const { dashboard, refresh } = useDashboard();
  const source = forceSource || params.get("source") || (params.get("lesson") ? "lesson" : "vocab");
  const level = params.get("level") ? Number(params.get("level")) : null;
  const lessonId = params.get("lesson") ? Number(params.get("lesson")) : null;

  const [session, setSession] = useState(null);
  const [index, setIndex] = useState(0);
  const [result, setResult] = useState(null); // grading response for the current question
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [celebrating, setCelebrating] = useState(false);
  // index -> graded correct/incorrect, straight from each /answer response;
  // display only (round tracker + progress), never sent anywhere.
  const [outcomes, setOutcomes] = useState({});
  const shownAt = useRef(Date.now());
  // Language the current round was rendered in (see the effect below).
  const renderedLang = useRef(i18n.language);

  const start = useCallback(() => {
    setSession(null);
    setSummary(null);
    setResult(null);
    setIndex(0);
    setOutcomes({});
    setError("");
    const body = { source, size: source === "review" ? 12 : 10 };
    if (level) body.hsk_level = level;
    if (lessonId) body.lesson_id = lessonId;
    api
      .post("/practice/sessions", body)
      .then((s) => {
        renderedLang.current = i18n.language;
        setSession(s);
        shownAt.current = Date.now();
      })
      // A lesson the learner hasn't reached on the path is refused by the
      // server with code lesson_locked; explain it in their language.
      .catch((e) => setError(e.code === "lesson_locked" ? i18n.t("pages.lessonDetail.lockedText") : e.message));
  }, [source, level, lessonId, i18n]);

  useEffect(start, [start]);

  // The round is fetched once, so a language switch used to leave its
  // meanings/options (and the answer card and missed list) in the language
  // it was created in. GET re-renders the SAME stored round -- same
  // questions, same answers, nothing regraded -- with the new X-Locale.
  const sessionId = session?.id;
  useEffect(() => {
    if (!sessionId || renderedLang.current === i18n.language) return undefined;
    let cancelled = false;
    const lang = i18n.language;
    api
      .get(`/practice/sessions/${sessionId}`)
      .then((s) => {
        if (cancelled) return;
        renderedLang.current = lang;
        setSession(s);
        setResult((r) => r && { ...r, card: s.questions[r.index]?.answer?.card || r.card });
        setSummary((sum) =>
          sum && {
            ...sum,
            missed: s.questions
              .filter((q) => q.answer && !q.answer.correct)
              .map((q) => ({ item_type: q.item_type, ...q.answer.card })),
          }
        );
      })
      .catch(() => {}); // keep showing the round in the previous language
    return () => {
      cancelled = true;
    };
  }, [sessionId, i18n.language]);

  const question = session?.questions?.[index];

  // Listening questions (and the audio button) use the browser's Mandarin TTS.
  useEffect(() => {
    if (question?.type === "listen_to_word" && question.prompt.speak && !result) {
      speakChinese(question.prompt.speak);
    }
    shownAt.current = Date.now();
  }, [question, result]);

  async function choose(optionId) {
    if (busy || result) return;
    setBusy(true);
    try {
      const r = await api.post(`/practice/sessions/${session.id}/answer`, {
        index,
        choice_id: optionId,
        response_ms: Date.now() - shownAt.current,
      });
      setResult({ ...r, choice_id: optionId, index });
      setOutcomes((o) => ({ ...o, [index]: r.correct }));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function next() {
    if (index + 1 < session.questions.length) {
      setIndex(index + 1);
      setResult(null);
      return;
    }
    setBusy(true);
    try {
      const s = await api.post(`/practice/sessions/${session.id}/complete`);
      setSummary(s);
      // Only a real celebration: >= 90% or the lesson completed by THIS
      // round (the server's reaction decides; re-practicing an already
      // completed lesson no longer throws a party at any score).
      setCelebrating(s.reaction?.mood === "celebrating");
      refresh?.(); // XP, streak, DNA and companion state changed
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const title = t(`practice.title.${source}`, { level: level ?? "" });
  const backTo = lessonId ? `/lessons/${lessonId}` : source === "review" ? "/mistakes" : `/${source === "vocab" ? "vocabulary" : source}`;
  const eyebrow = level ? `HSK ${level}` : t(source === "review" ? "nav.review" : "nav.lessons");
  const head = (kpis = null) => (
    <header className="page-head">
      <div>
        <div className="page-eyebrow">
          <Icon name="target" size={13} /> {eyebrow}
        </div>
        <h1 className="h1">{title}</h1>
      </div>
      {kpis}
    </header>
  );

  if (error) {
    return (
      <Layout>
        {head()}
        <Empty>{error}</Empty>
        <div className="row" style={{ marginTop: 12 }}>
          <button className="btn" onClick={start}>{t("practice.retry")}</button>
          <Link to={backTo}><button className="btn ghost">{t("practice.back")}</button></Link>
        </div>
      </Layout>
    );
  }
  if (!session) return <Layout><Loading>{t("practice.loading")}</Loading></Layout>;

  if (session.empty === "nothing_due") {
    return (
      <Layout>
        {head()}
        <div className="card" style={{ marginTop: 16, textAlign: "center" }}>
          <CompanionReaction
            animal={dashboard?.animal}
            reaction={session.reaction || { mood: "happy", event: "review_clear", streak: 0 }}
            size={88}
          />
          <p className="sub" style={{ marginTop: 10 }}>{t("practice.nothingDue")}</p>
          <div className="row" style={{ justifyContent: "center", marginTop: 12, flexWrap: "wrap" }}>
            <Link to="/vocabulary"><button className="btn">{t("nav.vocabulary")}</button></Link>
            <Link to="/hanzi"><button className="btn">{t("nav.hanzi")}</button></Link>
            <Link to="/grammar"><button className="btn">{t("nav.grammar")}</button></Link>
          </div>
        </div>
      </Layout>
    );
  }

  if (summary) {
    return (
      <Layout>
        {head(
          <div className="kpi-row">
            <div className="kpi">
              <span className="kpi-value">{Math.round(summary.score)}%</span>
              <span className="kpi-label">{t("practice.score")}</span>
            </div>
            <div className="kpi">
              <span className="kpi-value">{summary.correct}/{summary.total}</span>
              <span className="kpi-label">{t("practice.accuracy")}</span>
            </div>
            <div className="kpi">
              <span className="kpi-value">+{summary.xp_bonus}</span>
              <span className="kpi-label">XP</span>
            </div>
          </div>
        )}
        <Celebration
          show={celebrating}
          icon={summary.reaction?.event === "lesson_complete" ? "🎓" : "🎉"}
          title={t(summary.reaction?.event === "lesson_complete" ? "practice.lessonDone" : "practice.greatRound")}
          countTo={Math.round(summary.score)}
          countLabel="%"
          onClose={() => setCelebrating(false)}
          actionLabel={t("practice.nice")}
        />
        <div className="grid grid-2" style={{ marginTop: 16 }}>
          <div className="card" style={{ textAlign: "center" }}>
            <RingHero value={summary.score} label={t("practice.score")} />
            <p className="sub" style={{ marginTop: 8 }}>
              {t("practice.resultLine", { correct: summary.correct, total: summary.total })}
            </p>
            {summary.xp_bonus > 0 && <span className="badge good">+{summary.xp_bonus} XP</span>}
            {summary.lesson_status && (
              <p style={{ marginTop: 8 }}>
                <span className={`badge ${summary.lesson_status === "completed" ? "good" : "accent"}`}>
                  {t(`lessonStatus.${summary.lesson_status}`)}
                </span>
                {summary.lesson_status !== "completed" && (
                  <span className="sub" style={{ display: "block", marginTop: 6 }}>{t("practice.lessonPassHint")}</span>
                )}
              </p>
            )}
          </div>
          <div className="card">
            <CompanionReaction animal={dashboard?.animal} reaction={summary.reaction} size={96} />
            {summary.missed.length > 0 && (
              <>
                <h2 className="h2" style={{ marginTop: 14 }}>{t("practice.toReview")}</h2>
                <ul className="practice-missed">
                  {summary.missed.map((m, i) => (
                    <li key={i}>
                      <b>{m.hanzi}</b> {m.pinyin && <span className="sub">{m.pinyin}</span>} — {m.meaning}
                    </li>
                  ))}
                </ul>
                <p className="sub" style={{ fontSize: 12 }}>{t("practice.missedGoToReview")}</p>
              </>
            )}
          </div>
        </div>
        <div className="row" style={{ marginTop: 16, flexWrap: "wrap" }}>
          {/* Set by the server only when this round just completed the lesson. */}
          {summary.next_lesson_id && (
            <Link to={`/lessons/${summary.next_lesson_id}`} className="btn primary">
              {t("practice.nextLesson")} <Icon name="arrowRight" size={15} />
            </Link>
          )}
          <button className={`btn${summary.next_lesson_id ? "" : " primary"}`} onClick={start}>{t("practice.again")}</button>
          <Link to="/review"><button className="btn">{t("nav.review")}</button></Link>
          <Link to={backTo}><button className="btn ghost">{t("practice.back")}</button></Link>
        </div>
      </Layout>
    );
  }

  const total = session.questions.length;
  const answered = Object.keys(outcomes).length;
  const correctCount = Object.values(outcomes).filter(Boolean).length;
  const bigPrompt = ["word_to_meaning", "char_to_meaning", "char_to_pinyin"].includes(question.type);
  const animal = dashboard?.animal;
  // The greeting belongs to the start of the round only; after that the
  // companion reacts to each graded answer and calms back to neutral when
  // the next question appears -- temporary emotions never linger.
  const greeting = index === 0 && answered === 0 && !result ? session.reaction : null;
  // On narrow screens the greeting card stays until "Next" so answering the
  // first question doesn't make the feedback jump up the page.
  const narrowGreeting = index === 0 ? session.reaction : null;

  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow">
            <Icon name="target" size={13} /> {eyebrow}
          </div>
          <h1 className="h1">{title}</h1>
          <div style={{ marginTop: 10, maxWidth: 520 }}>
            <Bar value={(answered / total) * 100} />
          </div>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">{t("practice.counter", { n: index + 1, total })}</span>
            <span className="kpi-label">{t("practice.questionLabel")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{answered ? `${Math.round((correctCount / answered) * 100)}%` : "—"}</span>
            <span className="kpi-label">{t("practice.accuracy")}</span>
          </div>
        </div>
      </header>

      <div className="ws">
        <div className="ws-main">
          {narrowGreeting && (
            <div className="card only-narrow" style={{ marginBottom: 12 }}>
              <CompanionReaction animal={animal} reaction={narrowGreeting} compact size={56} />
            </div>
          )}
          <div className="card practice-card" key={`${session.id}-${index}-${i18n.language}`}>
            <p className="sub" style={{ marginBottom: 8 }}>{t(`practice.q.${question.type}`)}</p>
            <div className="practice-prompt">
              {question.type === "listen_to_word" ? (
                <button type="button" className="btn" onClick={() => speakChinese(question.prompt.speak)}>
                  <Icon name="ear" size={16} style={{ verticalAlign: -3, marginRight: 6 }} />
                  {t("practice.playAgain")}
                </button>
              ) : (
                <>
                  <div className={bigPrompt ? "practice-hanzi" : "practice-text"}>{question.prompt.text}</div>
                  {question.prompt.pinyin && <div className="sub" style={{ color: "var(--accent2)" }}>{question.prompt.pinyin}</div>}
                  {question.prompt.speak && (
                    <button type="button" className="btn small ghost" onClick={() => speakChinese(question.prompt.speak)} aria-label={t("pages.hanzi.hear")}>
                      <Icon name="ear" size={14} style={{ verticalAlign: -2 }} />
                    </button>
                  )}
                </>
              )}
            </div>

            <div className="practice-options">
              {question.options.map((o) => {
                let cls = "btn practice-option";
                if (result) {
                  if (o.id === result.correct_id) cls += " is-correct";
                  else if (o.id === result.choice_id) cls += " is-wrong";
                }
                const cjk = ["meaning_to_word", "listen_to_word"].includes(question.type);
                return (
                  <button key={o.id} type="button" className={cls} disabled={busy || !!result} onClick={() => choose(o.id)}>
                    <span className={cjk ? "practice-option-hanzi" : ""}>{o.label}</span>
                  </button>
                );
              })}
            </div>

            {result && (
              <div className="practice-feedback" style={{ marginTop: 14 }}>
                <div className={`badge ${result.correct ? "good" : "bad"}`}>
                  {result.correct ? t("practice.correct") : t("practice.notQuite")}
                </div>
                <div className="practice-answer-card">
                  <b style={{ fontSize: 22 }}>{result.card.hanzi}</b>{" "}
                  {result.card.pinyin && <span className="sub" style={{ color: "var(--accent2)" }}>{result.card.pinyin}</span>}
                  <div className="sub">{result.card.meaning}</div>
                  <div className="sub" style={{ fontSize: 12, marginTop: 4 }}>
                    {t("practice.masteryNow", { value: Math.round(result.mastery) })}
                    {result.xp_gained > 0 && ` · +${result.xp_gained} XP`}
                  </div>
                </div>
                {/* On narrow screens the side panel sits below the fold, so
                    the reaction is repeated here where the learner is looking. */}
                <div className="only-narrow">
                  <CompanionReaction animal={animal} reaction={result.reaction} context={question.item_type} compact focusMode="example" size={60} />
                </div>
                <button className="btn primary" style={{ marginTop: 12 }} onClick={next} disabled={busy} autoFocus>
                  {index + 1 < total ? t("practice.next") : t("practice.finish")}
                </button>
              </div>
            )}
          </div>
        </div>

        <aside className="ws-side">
          <div className="card side-card practice-companion only-wide">
            <p className="side-title">{animal?.name || t("nav.companion")}</p>
            {result ? (
              <CompanionReaction animal={animal} reaction={result.reaction} context={question.item_type} size={104} focusMode="example" />
            ) : greeting ? (
              <CompanionReaction animal={animal} reaction={greeting} size={104} />
            ) : (
              animal?.slug && <CompanionFigure slug={animal.slug} mood="neutral" size={104} />
            )}
          </div>

          <div className="card side-card">
            <p className="side-title">{t("practice.roundProgress")}</p>
            <div className="round-dots">
              {session.questions.map((q, i) => {
                const state = i in outcomes ? (outcomes[i] ? "is-right" : "is-wrong") : i === index ? "is-now" : "";
                return (
                  <span key={i} className={`round-dot ${state}`} aria-hidden="true">
                    {i + 1}
                  </span>
                );
              })}
            </div>
            <p className="sub" style={{ marginTop: 12 }}>
              {t("practice.resultLine", { correct: correctCount, total: answered })}
            </p>
          </div>

          <div className="card side-card">
            <div className="side-links">
              <Link to="/review"><button className="btn"><Icon name="clock" size={15} /> {t("nav.review")}</button></Link>
              <Link to={backTo}><button className="btn ghost">{t("practice.back")}</button></Link>
            </div>
          </div>
        </aside>
      </div>
    </Layout>
  );
}
