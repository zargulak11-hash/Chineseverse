import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api.js";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
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

  function next() {
    retry();
    reload();
  }

  return (
    <Layout>
      <h1 className="h1">{t("pages.petTeacher.title")}</h1>
      <p className="sub">
        {t("pages.petTeacher.subtitle", { name: animal ? animal.name : t("pages.petTeacher.yourCompanion") })}
      </p>

      <div className="chat" style={{ marginTop: 18 }}>
        <div className="bubble npc">
          <span className="speaker" style={{ display: "flex", alignItems: "center", gap: 5 }}>
            {animal ? (
              <AnimalAvatar slug={animal.slug} accentColor={animal.accent_color} size={16} />
            ) : (
              "🐾"
            )}{" "}
            {animal?.name || t("pages.petTeacher.yourCompanion")}
          </span>
          {lesson.wrong_sentence}
          {lesson.hint && !result && <span className="english">{t("pages.conversation.hint")}: {lesson.hint}</span>}
        </div>

        {!result && (
          <div
            className="microw"
            style={{ flexDirection: "column", alignItems: "stretch", maxWidth: 520, margin: "0 auto" }}
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

        {result &&
          (result.error ? (
            <div className="bubble reaction">⚠️ {result.error}</div>
          ) : (
            <>
              <div className="bubble me">
                {correction}
                <span className="english">{explanation}</span>
              </div>
              <div
                className="bubble reaction"
                style={
                  !result.success
                    ? { borderColor: "var(--bad)", color: "var(--bad)", background: "var(--bad-dim)" }
                    : undefined
                }
              >
                <Icon name={result.success ? "check" : "x"} size={13} style={{ verticalAlign: -2, marginRight: 4 }} />
                {result.feedback}
              </div>
              {!result.success && (
                <p className="sub center">
                  {t("pages.petTeacher.correctSentence")}: <b>{result.correct_sentence}</b>
                </p>
              )}
              <div className="row center" style={{ justifyContent: "center" }}>
                <button className="btn primary" onClick={result.success ? next : retry}>
                  {result.success ? t("pages.petTeacher.teachAnother") : t("pages.petTeacher.tryAgain")}
                </button>
              </div>
            </>
          ))}
      </div>

      <p className="sub center" style={{ marginTop: 20 }}>
        {t("pages.petTeacher.rulesTaught")}: <b>{result?.taught_count ?? "—"}</b>
      </p>
    </Layout>
  );
}
