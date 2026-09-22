import { useState } from "react";
import { api } from "../api.js";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
import Layout from "../components/Layout.jsx";
import MicRecorder from "../components/MicRecorder.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { useApi } from "../hooks/useApi.js";

export default function PetTeacher() {
  const { dashboard } = useDashboard();
  const { data: lesson, error, reload } = useApi("/pet-teacher/lesson");
  const [correction, setCorrection] = useState("");
  const [explanation, setExplanation] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!lesson) return <Layout><Loading>Your companion is thinking of a mistake…</Loading></Layout>;

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
      <h1 className="h1">Pet Teacher Mode</h1>
      <p className="sub">
        {animal ? animal.name : "Your companion"} sometimes gets Chinese wrong on
        purpose. Catch the mistake, fix it, and explain the rule — that's how it
        actually learns.
      </p>

      <div className="chat" style={{ marginTop: 18 }}>
        <div className="bubble npc">
          <span className="speaker" style={{ display: "flex", alignItems: "center", gap: 5 }}>
            {animal ? (
              <AnimalAvatar slug={animal.slug} accentColor={animal.accent_color} size={16} />
            ) : (
              "🐾"
            )}{" "}
            {animal?.name || "Companion"}
          </span>
          {lesson.wrong_sentence}
          {lesson.hint && !result && <span className="english">hint: {lesson.hint}</span>}
        </div>

        {!result && (
          <div
            className="microw"
            style={{ flexDirection: "column", alignItems: "stretch", maxWidth: 520, margin: "0 auto" }}
          >
            <div className="field">
              <label>Your correction</label>
              <input
                className="input"
                value={correction}
                onChange={(e) => setCorrection(e.target.value)}
                placeholder="Rewrite the sentence correctly…"
              />
            </div>
            <div className="field">
              <label>Explain the rule</label>
              <div className="row" style={{ alignItems: "stretch" }}>
                <textarea
                  className="input"
                  rows={2}
                  style={{ flex: 1 }}
                  value={explanation}
                  onChange={(e) => setExplanation(e.target.value)}
                  placeholder="Why was it wrong? Tap the mic to speak your answer…"
                />
                <MicRecorder
                  onTranscript={(t) => setExplanation((prev) => (prev ? `${prev} ${t}` : t))}
                  disabled={busy}
                />
              </div>
            </div>
            <button
              className="btn primary"
              onClick={submit}
              disabled={busy || !correction.trim() || !explanation.trim()}
            >
              {busy ? "Checking…" : "Teach your companion"}
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
                    ? { borderColor: "var(--bad)", color: "var(--bad)", background: "rgba(248,113,113,.1)" }
                    : undefined
                }
              >
                {result.success ? "✅ " : "❌ "}
                {result.feedback}
              </div>
              {!result.success && (
                <p className="sub center">
                  Correct sentence: <b>{result.correct_sentence}</b>
                </p>
              )}
              <div className="row center" style={{ justifyContent: "center" }}>
                <button className="btn primary" onClick={result.success ? next : retry}>
                  {result.success ? "Teach another rule" : "Try again"}
                </button>
              </div>
            </>
          ))}
      </div>

      <p className="sub center" style={{ marginTop: 20 }}>
        Rules taught so far: <b>{result?.taught_count ?? "—"}</b>
      </p>
    </Layout>
  );
}
