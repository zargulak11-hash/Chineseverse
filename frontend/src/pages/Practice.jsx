import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api.js";
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
  const shownAt = useRef(Date.now());

  const start = useCallback(() => {
    setSession(null);
    setSummary(null);
    setResult(null);
    setIndex(0);
    setError("");
    const body = { source, size: source === "review" ? 12 : 10 };
    if (level) body.hsk_level = level;
    if (lessonId) body.lesson_id = lessonId;
    api
      .post("/practice/sessions", body)
      .then((s) => {
        setSession(s);
        shownAt.current = Date.now();
      })
      .catch((e) => setError(e.message));
  }, [source, level, lessonId]);

  useEffect(start, [start]);

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
      setResult({ ...r, choice_id: optionId });
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
      setCelebrating(s.score >= 90 || s.lesson_status === "completed");
      refresh?.(); // XP, streak, DNA and companion state changed
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const title = t(`practice.title.${source}`, { level: level ?? "" });
  const backTo = lessonId ? `/lessons/${lessonId}` : source === "review" ? "/mistakes" : `/${source === "vocab" ? "vocabulary" : source}`;

  if (error) {
    return (
      <Layout>
        <h1 className="h1">{title}</h1>
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
        <h1 className="h1">{title}</h1>
        <div className="card" style={{ marginTop: 16, textAlign: "center" }}>
          <CompanionReaction animal={dashboard?.animal} reaction={{ mood: "happy", event: "review_clear", streak: 0 }} />
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
        <h1 className="h1">{title}</h1>
        <Celebration
          show={celebrating}
          icon={summary.lesson_status === "completed" ? "🎓" : "🎉"}
          title={t(summary.lesson_status === "completed" ? "practice.lessonDone" : "practice.greatRound")}
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
            <CompanionReaction animal={dashboard?.animal} reaction={summary.reaction} size={80} />
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
          <button className="btn primary" onClick={start}>{t("practice.again")}</button>
          <Link to="/review"><button className="btn">{t("nav.review")}</button></Link>
          <Link to={backTo}><button className="btn ghost">{t("practice.back")}</button></Link>
        </div>
      </Layout>
    );
  }

  const answered = session.questions.filter((q, i) => q.answer || (i === index && result)).length;
  const bigPrompt = ["word_to_meaning", "char_to_meaning", "char_to_pinyin"].includes(question.type);

  return (
    <Layout>
      <div className="row spread" style={{ flexWrap: "wrap", gap: 8 }}>
        <h1 className="h1">{title}</h1>
        <span className="badge">{t("practice.counter", { n: index + 1, total: session.questions.length })}</span>
      </div>
      <div style={{ marginTop: 8 }}>
        <Bar value={(answered / session.questions.length) * 100} />
      </div>

      <div className="card practice-card" style={{ marginTop: 16 }} key={`${session.id}-${index}-${i18n.language}`}>
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
            <CompanionReaction animal={dashboard?.animal} reaction={result.reaction} context={question.item_type} />
            <button className="btn primary" style={{ marginTop: 12 }} onClick={next} disabled={busy} autoFocus>
              {index + 1 < session.questions.length ? t("practice.next") : t("practice.finish")}
            </button>
          </div>
        )}
      </div>
    </Layout>
  );
}
