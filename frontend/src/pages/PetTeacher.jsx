import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
import CompanionReaction from "../components/CompanionReaction.jsx";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import MicRecorder from "../components/MicRecorder.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { useApi } from "../hooks/useApi.js";

export default function PetTeacher() {
  const { t } = useTranslation();
  const { dashboard } = useDashboard();
  const { data: lesson, error, reload } = useApi("/pet-teacher/lesson");
  const [correction, setCorrection] = useState("");
  const [explanation, setExplanation] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!lesson) return <Layout><Loading>{t("pages.petTeacher.thinking")}</Loading></Layout>;

  const animal = dashboard?.animal;
  const tone = !result || result.error ? "" : result.success ? "good" : result.correct_fix || result.outcome === "close" ? "accent" : "bad";

  async function submit() {
    if (!correction.trim() || !explanation.trim() || busy) return;
    setBusy(true);
    try {
      const res = await api.post(`/pet-teacher/lesson/${lesson.id}/answer`, {
        correction: correction.trim(),
        explanation: explanation.trim(),
      });
      setResult(res);
    } catch (e) {
      setResult({ error: e.message });
    } finally {
      setBusy(false);
    }
  }

  function retry() {
    setCorrection("");
    setExplanation("");
    setResult(null);
  }

  // The correction was right; only the explanation needs another go, so
  // the learner keeps their sentence instead of retyping it.
  function explainAgain() {
    setExplanation("");
    setResult(null);
  }

  function next() {
    retry();
    reload();
  }

  return (
    <Layout>
      <header className="page-head">
        <div>
          <h1 className="h1">{t("pages.petTeacher.title")}</h1>
          <p className="sub">
            {t("pages.petTeacher.subtitle", { name: animal ? animal.name : t("pages.petTeacher.yourCompanion") })}
          </p>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">{result?.taught_count ?? lesson.taught_count ?? 0}</span>
            <span className="kpi-label">{t("pages.petTeacher.rulesTaught")}</span>
          </div>
        </div>
      </header>

      <div className="ws">
      <div className="ws-main">
      <div className="card"><div className="chat">
        <div className="bubble npc">
          <span className="speaker" style={{ display: "flex", alignItems: "center", gap: 5 }}>
            {animal ? (
              <AnimalAvatar
                slug={animal.slug}
                accentColor={animal.accent_color}
                size={16}
                state={!result || result.error ? "idle" : result.success ? "celebrating" : result.correct_fix ? "happy" : "encouraging"}
              />
            ) : (
              <Icon name="paw" size={14} style={{ verticalAlign: -2 }} />
            )}{" "}
            {animal?.name || t("pages.petTeacher.yourCompanion")}
          </span>
          <span lang="zh">{lesson.wrong_sentence}</span>
          {lesson.hint && !result && <span className="english">{t("pages.conversation.hint")}: {lesson.hint}</span>}
        </div>

        {!result && (
          <div
            className="microw"
            style={{ flexDirection: "column", alignItems: "stretch" }}
          >
            <div className="field">
              <label>{t("pages.petTeacher.yourCorrection")}</label>
              <input
                className="input"
                value={correction}
                onChange={(e) => setCorrection(e.target.value)}
                placeholder={t("pages.petTeacher.correctionPlaceholder")}
              />
            </div>
            <div className="field">
              <label>{t("pages.petTeacher.explainRule")}</label>
              <div className="row" style={{ alignItems: "stretch" }}>
                <textarea
                  className="input"
                  rows={2}
                  style={{ flex: 1 }}
                  value={explanation}
                  onChange={(e) => setExplanation(e.target.value)}
                  placeholder={t("pages.petTeacher.explanationPlaceholder")}
                />
                <MicRecorder
                  onTranscript={(txt) => setExplanation((prev) => (prev ? `${prev} ${txt}` : txt))}
                  disabled={busy}
                />
              </div>
            </div>
            <button
              className="btn primary"
              onClick={submit}
              disabled={busy || !correction.trim() || !explanation.trim()}
            >
              {busy ? t("pages.petTeacher.checking") : t("pages.petTeacher.teachCompanion")}
            </button>
          </div>
        )}

        {result && result.error && <div className="bubble reaction" role="alert"><Icon name="alert" size={14} style={{ verticalAlign: -2 }} /> {result.error}</div>}
        {result && !result.error && (
          <div aria-live="polite" className="pt-result">
            <div className="bubble me">
              {correction}
              <span className="english">{explanation}</span>
            </div>
            <div className={`pt-verdict ${tone}`}>
              <Icon name={result.correct_fix ? "check" : "x"} size={15} />
              <div style={{ minWidth: 0 }}>
                <b>{t(`pages.petTeacher.outcome.${result.outcome}`)}</b>
                {/* One hint, not two: a repeated sentence gets the "say why"
                    hint; otherwise the grader's own feedback. */}
                {result.outcome === "fixed_needs_explanation"
                  ? <p>{result.restated ? t("pages.petTeacher.restated") : result.feedback || t("pages.petTeacher.explainMore")}</p>
                  : result.feedback && <p>{result.feedback}</p>}
              </div>
            </div>
            {result.reaction && animal && (
              <CompanionReaction animal={animal} reaction={result.reaction} context="grammar" compact size={56} focusMode="none" />
            )}
            {(result.issues || []).map((code) => (
              <p key={code} className="pt-issue">{t(`grammarCheck.issue.${code}`)}</p>
            ))}
            {result.show_correct_sentence && (
              <p className="sub center">
                {t("pages.petTeacher.correctSentence")}: <b lang="zh">{result.correct_sentence}</b>
              </p>
            )}
            {!result.correct_fix && result.mistake_summary && (
              <p className="sub center">{t("pages.petTeacher.theRule")}: {result.mistake_summary}</p>
            )}
            {result.unlocked?.length > 0 && (
              <p className="sub center">{t("pages.petTeacher.unlocked")}: {result.unlocked.join(", ")}</p>
            )}
            <div className="row" style={{ justifyContent: "center", flexWrap: "wrap" }}>
              {result.success ? (
                <button type="button" className="btn primary" onClick={next}>{t("pages.petTeacher.teachAnother")}</button>
              ) : result.correct_fix ? (
                <>
                  <button type="button" className="btn primary" onClick={explainAgain}>{t("pages.petTeacher.explainAgain")}</button>
                  <button type="button" className="btn ghost" onClick={next}>{t("pages.petTeacher.skipCase")}</button>
                </>
              ) : (
                <>
                  <button type="button" className="btn primary" onClick={retry}>{t("pages.petTeacher.tryAgain")}</button>
                  <button type="button" className="btn ghost" onClick={next}>{t("pages.petTeacher.skipCase")}</button>
                </>
              )}
              {result.grammar_topic_id && (
                <Link className="btn ghost" to={`/grammar/${result.grammar_topic_id}`}>
                  <Icon name="book" size={15} /> {t("grammarCheck.openGrammar", { title: result.grammar_topic_title })}
                </Link>
              )}
            </div>
          </div>
        )}
      </div></div>
      </div>
      <aside className="ws-side">
        <div className="card side-card">
          <p className="side-title">{t("pages.petTeacher.howTitle")}</p>
          <ol className="scene-rules">
            <li>{t("pages.petTeacher.how1")}</li>
            <li>{t("pages.petTeacher.how2")}</li>
            <li>{t("pages.petTeacher.how3")}</li>
          </ol>
        </div>
      </aside>
      </div>
    </Layout>
  );
}
