import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { canSpeakChinese, speakChinese } from "../zhSpeech.js";

// An HSK level's final exam (backend: services/hsk_exam.py, /api/exams).
// The server owns the attempt: its questions, the clock, the grading and the
// result -- this page only shows questions and sends option ids. It is a
// protected one-sitting session: hiding the page (another tab or window),
// leaving it, reloading or closing it ends the attempt with 0. The page
// reports what it can see; the server also ends any attempt that is opened
// again, so a report that never arrived does not leave a way back in.

// Report an integrity violation; api.beacon's request outlives the page
// (reload, close, navigation).
function reportViolation(attemptId, reason) {
  return api.beacon(`/exams/attempts/${attemptId}/violation`, { reason });
}

// While the exam is visible and focused the page tells the server it is
// still there; the server ends the attempt with 0 after ~30 s of silence
// (backend services/hsk_exam.py PRESENCE_TIMEOUT), so a page that was really
// left can't go on answering even if its violation report never arrived.
const HEARTBEAT_MS = 5000;
// Focus moving to another window. A brief flicker (a permission bubble, the
// browser's own UI) is tolerated; staying away is leaving the exam.
const BLUR_GRACE_MS = 800;

const formatTime = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

export default function Exam() {
  const { level: levelParam } = useParams();
  const level = Number(levelParam);
  const { t } = useTranslation();
  const [overview, setOverview] = useState(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(null); // running attempt (questions)
  const [index, setIndex] = useState(0);
  const [chosen, setChosen] = useState({}); // question index -> option id
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [blockedBy, setBlockedBy] = useState(null); // another open attempt's id
  const running = useRef(null); // attempt id while the exam is live
  const finishing = useRef(false); // submit in flight: not a violation

  useEffect(() => {
    api.get("/exams").then(setOverview).catch((e) => setError(e.message));
  }, [result]);

  // The exam ends (with 0) the moment the page is hidden, closed, reloaded
  // or left. Only while an attempt is live.
  useEffect(() => {
    if (!attempt) return undefined;
    running.current = attempt.id;
    const end = (reason) => {
      if (running.current !== attempt.id || finishing.current) return;
      running.current = null;
      reportViolation(attempt.id, reason).then((r) => r && setResult(r));
    };
    const onVisibility = () => document.visibilityState === "hidden" && end("hidden");
    const onPageHide = () => end("closed");
    let blurTimer = null;
    const onBlur = () => {
      clearTimeout(blurTimer);
      blurTimer = setTimeout(() => {
        if (!document.hasFocus() && document.visibilityState === "visible") end("window_blur");
      }, BLUR_GRACE_MS);
    };
    const onFocus = () => clearTimeout(blurTimer);
    const beat = setInterval(() => {
      if (running.current !== attempt.id || finishing.current) return;
      if (document.visibilityState !== "visible" || !document.hasFocus()) return;
      api.post(`/exams/attempts/${attempt.id}/heartbeat`).catch((e) => {
        if (e.data?.result && running.current === attempt.id) {
          running.current = null;
          setResult(e.data.result);
        }
      });
    }, HEARTBEAT_MS);
    const onBeforeUnload = (e) => {
      e.preventDefault();
      e.returnValue = ""; // the browser's own "leave this page?" warning
    };
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("pagehide", onPageHide);
    window.addEventListener("beforeunload", onBeforeUnload);
    window.addEventListener("blur", onBlur);
    window.addEventListener("focus", onFocus);
    return () => {
      clearInterval(beat);
      clearTimeout(blurTimer);
      window.removeEventListener("blur", onBlur);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("pagehide", onPageHide);
      window.removeEventListener("beforeunload", onBeforeUnload);
      // Leaving the page inside the app (sidebar, back button). Deferred a
      // tick: React's dev double-mount must not count as leaving.
      const id = attempt.id;
      setTimeout(() => {
        if (running.current === id && !document.getElementById(`exam-${id}`)) end("navigation");
      }, 0);
    };
  }, [attempt]);

  // The server's clock, counted down here; at 0 the exam is submitted.
  useEffect(() => {
    if (!attempt || result) return undefined;
    const timer = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          clearInterval(timer);
          submit();
          return 0;
        }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt, result]);

  // A listening question plays its word when it comes up.
  const question = attempt?.questions[index];
  useEffect(() => {
    if (question?.type === "listen_to_word" && question.prompt.speak && !result) speakChinese(question.prompt.speak);
  }, [question, result]);

  async function start() {
    setBusy(true);
    setError("");
    setBlockedBy(null);
    try {
      const a = await api.post(`/exams/${level}/start`);
      setResult(null);
      setChosen({});
      setIndex(0);
      setSecondsLeft(a.seconds_left);
      setAttempt(a);
    } catch (e) {
      if (e.code === "exam_in_progress") setBlockedBy(e.data?.attempt_id ?? null);
      else setError(e.code === "exam_locked" ? t("exam.locked", { level }) : e.message);
    } finally {
      setBusy(false);
    }
  }

  async function endOtherAndStart() {
    if (blockedBy) await reportViolation(blockedBy, "closed");
    await start();
  }

  async function choose(optionId) {
    if (!attempt || result) return;
    setChosen((c) => ({ ...c, [index]: optionId }));
    try {
      await api.post(`/exams/attempts/${attempt.id}/answer`, { index, choice_id: optionId });
    } catch (e) {
      if (e.data?.result) finish(e.data.result);
      else setError(e.message);
    }
  }

  function finish(r) {
    running.current = null;
    setResult(r);
  }

  async function submit() {
    if (!attempt || finishing.current) return;
    finishing.current = true;
    setBusy(true);
    try {
      finish(await api.post(`/exams/attempts/${attempt.id}/submit`));
    } catch (e) {
      if (e.data?.result) finish(e.data.result);
      else setError(e.message);
    } finally {
      finishing.current = false;
      setBusy(false);
      setConfirming(false);
    }
  }

  if (!Number.isInteger(level) || level < 1 || level > 9) return <Layout><Empty>{t("exam.locked", { level: 1 })}</Empty></Layout>;
  if (!overview && !error) return <Layout><Loading /></Layout>;

  const levelInfo = overview?.levels.find((l) => l.level === level);
  const next = level < 9 ? level + 1 : null;
  const answeredCount = Object.keys(chosen).length;

  // ------------------------------------------------------------ result
  if (result) {
    const passed = result.status === "passed";
    const message =
      result.status === "passed" ? (next ? t("exam.result.passed", { next }) : t("exam.result.passedLast"))
      : result.status === "invalidated" ? t("exam.result.invalidated")
      : result.status === "expired" ? t("exam.result.expired")
      : t("exam.result.failed", { score: result.pass_score });
    return (
      <Layout>
        <div className="card exam-result" data-self-animate="true">
          <div className="page-eyebrow"><Icon name="award" size={13} /> {t("exam.eyebrow")}</div>
          <h1 className="h1">{t("exam.title", { level })}</h1>
          <div className={`badge ${passed ? "good" : "bad"}`} style={{ marginTop: 8 }}>
            {t(`exam.status.${result.status}`)}
          </div>
          <p className="kpi-value exam-score">{result.score ?? 0}%</p>
          <p className="sub">{t("exam.result.score", { correct: result.correct ?? 0, total: result.total, score: result.score ?? 0 })}</p>
          <p style={{ marginTop: 12 }}>{message}</p>
          <div className="row" style={{ marginTop: 16, gap: 8, flexWrap: "wrap" }}>
            {passed && next ? (
              <Link to="/lessons" className="btn primary">{t("exam.toNextLevel", { level: next })}</Link>
            ) : (
              <Link to="/lessons" className="btn">{t("exam.toLessons")}</Link>
            )}
            {!passed && overview?.exam_level === level && (
              <button type="button" className="btn primary" onClick={start} disabled={busy}>{t("exam.retry")}</button>
            )}
          </div>
        </div>
      </Layout>
    );
  }

  // ------------------------------------------------------------ running
  if (attempt) {
    const q = question;
    const cjk = q.type === "meaning_to_word";
    return (
      <Layout>
        <div id={`exam-${attempt.id}`}>
          <header className="page-head">
            <div>
              <div className="page-eyebrow"><Icon name="award" size={13} /> {t("exam.eyebrow")}</div>
              <h1 className="h1">{t("exam.title", { level })}</h1>
              <p className="sub exam-warning"><Icon name="lock" size={13} /> {t("exam.integrityBanner")}</p>
            </div>
            <div className="kpi-row">
              <div className="kpi">
                <span className="kpi-value">{index + 1}/{attempt.total}</span>
                <span className="kpi-label">{t("exam.questionKpi")}</span>
              </div>
              <div className="kpi">
                <span className={`kpi-value${secondsLeft <= 60 ? " exam-time-low" : ""}`}>{formatTime(secondsLeft)}</span>
                <span className="kpi-label">{t("exam.timeLeft")}</span>
              </div>
            </div>
          </header>

          <div className="card practice-card" style={{ marginTop: 16 }}>
            <Bar value={answeredCount} max={attempt.total} />
            <p className="sub" style={{ margin: "12px 0 8px" }}>{t(`practice.q.${q.type}`)}</p>
            <div className="practice-prompt">
              {q.type === "listen_to_word" ? (
                <>
                  <button type="button" className="btn" onClick={() => speakChinese(q.prompt.speak)}>
                    <Icon name="ear" size={16} /> {t("practice.playAgain")}
                  </button>
                  {!canSpeakChinese() && q.prompt.pinyin && (
                    <div className="practice-no-voice">
                      <div className="practice-text">{q.prompt.pinyin}</div>
                      <p className="sub">{t("practice.noChineseVoice")}</p>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div className={q.type === "word_to_meaning" || q.type.startsWith("char_") ? "practice-hanzi" : "practice-text"}>
                    {q.prompt.text}
                  </div>
                  {q.prompt.pinyin && <div className="sub">{q.prompt.pinyin}</div>}
                </>
              )}
            </div>
            <div className="practice-options">
              {q.options.map((o) => (
                <button
                  key={o.id}
                  type="button"
                  className={`btn practice-option${chosen[index] === o.id ? " is-chosen" : ""}`}
                  aria-pressed={chosen[index] === o.id}
                  disabled={busy}
                  onClick={() => choose(o.id)}
                >
                  <span className={cjk ? "practice-option-hanzi" : ""}>{o.label}</span>
                </button>
              ))}
            </div>
            <div className="row spread" style={{ marginTop: 16, flexWrap: "wrap", gap: 8 }}>
              <button type="button" className="btn ghost" disabled={index === 0} onClick={() => setIndex(index - 1)}>
                {t("exam.prev")}
              </button>
              <span className="sub">{t("exam.answered", { count: answeredCount, total: attempt.total })}</span>
              {index + 1 < attempt.total ? (
                <button type="button" className="btn" onClick={() => setIndex(index + 1)}>{t("exam.next")}</button>
              ) : (
                <button type="button" className="btn primary" disabled={busy} onClick={() => setConfirming(true)}>
                  {t("exam.submit")}
                </button>
              )}
            </div>
            {confirming && (
              <div className="exam-confirm">
                <p className="sub">{t("exam.confirmSubmit", { count: attempt.total - answeredCount })}</p>
                <div className="row" style={{ gap: 8 }}>
                  <button type="button" className="btn primary" disabled={busy} onClick={submit}>{t("exam.submit")}</button>
                  <button type="button" className="btn ghost" onClick={() => setConfirming(false)}>{t("exam.keepGoing")}</button>
                </div>
              </div>
            )}
          </div>
          {error && <p className="formerr">{error}</p>}
        </div>
      </Layout>
    );
  }

  // ------------------------------------------------------------ intro
  const open = overview?.exam_level === level;
  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="award" size={13} /> {t("exam.eyebrow")}</div>
          <h1 className="h1">{t("exam.title", { level })}</h1>
          <p className="sub">{next ? t("exam.intro", { level, next }) : t("exam.introLast")}</p>
        </div>
        {levelInfo && (
          <div className="kpi-row">
            <div className="kpi">
              <span className="kpi-value">{levelInfo.lessons_completed}/{levelInfo.lessons_total}</span>
              <span className="kpi-label">{t("exam.lessonsKpi")}</span>
            </div>
            <div className="kpi">
              <span className="kpi-value">{levelInfo.best_score != null ? `${levelInfo.best_score}%` : "—"}</span>
              <span className="kpi-label">{t("exam.bestKpi")}</span>
            </div>
          </div>
        )}
      </header>
      <div className="card" style={{ marginTop: 24 }}>
        <h2 className="h2">{t("exam.rulesTitle")}</h2>
        <ul className="exam-rules">
          <li>{t("exam.rules.questions", { count: overview?.question_count ?? 20, level })}</li>
          <li>{t("exam.rules.time", { minutes: Math.round((overview?.time_limit_seconds ?? 1200) / 60) })}</li>
          <li>{t("exam.rules.pass", { score: overview?.pass_score ?? 80 })}</li>
          <li className="exam-warning"><Icon name="lock" size={13} /> {t("exam.rules.integrity")}</li>
        </ul>
        {levelInfo?.exam === "passed" ? (
          <p className="badge good" style={{ marginTop: 16 }}><Icon name="check" size={13} /> {t("exam.status.passed")}</p>
        ) : open ? (
          <button type="button" className="btn primary" style={{ marginTop: 16 }} disabled={busy} onClick={start}>
            <Icon name="play" size={15} /> {busy ? t("exam.starting") : t("exam.start")}
          </button>
        ) : (
          <p className="sub" style={{ marginTop: 16 }}><Icon name="lock" size={13} /> {t("exam.locked", { level })}</p>
        )}
        {blockedBy !== null && (
          <div className="exam-confirm">
            <p className="sub">{t("exam.inProgress")}</p>
            <button type="button" className="btn" disabled={busy} onClick={endOtherAndStart}>{t("exam.endAndRestart")}</button>
          </div>
        )}
        {error && <p className="formerr">{error}</p>}
        <div className="row" style={{ marginTop: 16 }}>
          <Link to="/lessons" className="btn ghost">{t("exam.toLessons")}</Link>
        </div>
      </div>
    </Layout>
  );
}
