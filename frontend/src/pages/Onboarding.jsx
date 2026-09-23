import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import MicRecorder from "../components/MicRecorder.jsx";
import { Loading } from "../components/ui.jsx";
import { usePrefs } from "../prefs.jsx";

const MOTIVATIONS = ["travel", "work", "culture", "exam", "family", "other"];
const SOURCES = ["friend", "social", "school", "search", "other"];

export default function Onboarding() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { soundEnabled } = usePrefs() || {};

  const [step, setStep] = useState("loading"); // loading|motivation|discovery|intro|test|result
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const [motivation, setMotivation] = useState(null);
  const [motivationOther, setMotivationOther] = useState("");
  const [source, setSource] = useState(null);
  const [sourceOther, setSourceOther] = useState("");

  const [attemptId, setAttemptId] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [qIdx, setQIdx] = useState(0);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);

  useEffect(() => {
    api
      .get("/me")
      .then((me) => {
        if (me.profile.onboarding_completed) {
          navigate("/dashboard", { replace: true });
        } else {
          setStep("motivation");
        }
      })
      .catch(() => setStep("motivation"));
  }, [navigate]);

  async function saveMotivationAndSource() {
    setBusy(true);
    setError("");
    try {
      await api.patch("/me/profile", {
        learning_motivation: motivation,
        learning_motivation_other: motivation === "other" ? motivationOther : null,
        discovery_source: source,
        discovery_source_other: source === "other" ? sourceOther : null,
      });
      setStep("intro");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function startTest() {
    setBusy(true);
    setError("");
    try {
      const r = await api.post("/onboarding/placement-test/start");
      setAttemptId(r.attempt_id);
      setQuestions(r.questions);
      setAnswers({});
      setQIdx(0);
      setStep("test");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function skipTest() {
    setBusy(true);
    setError("");
    try {
      const r = await api.post("/onboarding/placement-test/skip");
      setResult(r);
      setStep("result");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function finishSubmit(finalAnswers) {
    setBusy(true);
    setError("");
    try {
      const payload = {
        answers: Object.entries(finalAnswers).map(([index, answer]) => ({
          index: Number(index),
          answer,
        })),
      };
      const r = await api.post(`/onboarding/placement-test/${attemptId}/submit`, payload);
      setResult(r);
      setStep("result");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function answerQuestion(value) {
    const q = questions[qIdx];
    const nextAnswers = { ...answers, [q.index]: value };
    setAnswers(nextAnswers);
    if (qIdx + 1 < questions.length) {
      setQIdx(qIdx + 1);
    } else {
      finishSubmit(nextAnswers);
    }
  }

  const q = questions[qIdx];
  useEffect(() => {
    if (step === "test" && soundEnabled && q?.type === "listening" && q.tts_text && window.speechSynthesis) {
      const utter = new SpeechSynthesisUtterance(q.tts_text);
      utter.lang = "zh-CN";
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utter);
    }
  }, [step, qIdx, q?.type, q?.tts_text, soundEnabled]);

  if (step === "loading") {
    return (
      <Layout>
        <Loading>{t("pages.onboarding.loading")}</Loading>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="card formcard" style={{ maxWidth: 560, margin: "24px auto" }}>
        {error && <p className="formerr">{error}</p>}

        {step === "motivation" && (
          <>
            <h1 className="h1">{t("pages.onboarding.motivationTitle")}</h1>
            <p className="sub">{t("pages.onboarding.motivationSubtitle")}</p>
            <div className="col" style={{ marginTop: 16, gap: 10 }}>
              {MOTIVATIONS.map((key) => (
                <button
                  key={key}
                  className={`option${motivation === key ? " picked" : ""}`}
                  onClick={() => setMotivation(key)}
                >
                  {t(`pages.onboarding.motivation.${key}`)}
                </button>
              ))}
            </div>
            {motivation === "other" && (
              <div className="field" style={{ marginTop: 12 }}>
                <input
                  className="input"
                  value={motivationOther}
                  onChange={(e) => setMotivationOther(e.target.value)}
                  placeholder={t("pages.onboarding.otherPlaceholder")}
                />
              </div>
            )}
            <button
              className="btn primary"
              style={{ marginTop: 18 }}
              disabled={!motivation || (motivation === "other" && !motivationOther.trim())}
              onClick={() => setStep("discovery")}
            >
              {t("pages.onboarding.next")}
            </button>
          </>
        )}

        {step === "discovery" && (
          <>
            <h1 className="h1">{t("pages.onboarding.discoveryTitle")}</h1>
            <div className="col" style={{ marginTop: 16, gap: 10 }}>
              {SOURCES.map((key) => (
                <button
                  key={key}
                  className={`option${source === key ? " picked" : ""}`}
                  onClick={() => setSource(key)}
                >
                  {t(`pages.onboarding.source.${key}`)}
                </button>
              ))}
            </div>
            {source === "other" && (
              <div className="field" style={{ marginTop: 12 }}>
                <input
                  className="input"
                  value={sourceOther}
                  onChange={(e) => setSourceOther(e.target.value)}
                  placeholder={t("pages.onboarding.otherPlaceholder")}
                />
              </div>
            )}
            <button
              className="btn primary"
              style={{ marginTop: 18 }}
              disabled={busy || !source || (source === "other" && !sourceOther.trim())}
              onClick={saveMotivationAndSource}
            >
              {t("pages.onboarding.next")}
            </button>
          </>
        )}

        {step === "intro" && (
          <>
            <h1 className="h1">{t("pages.onboarding.testIntroTitle")}</h1>
            <p className="sub">{t("pages.onboarding.testIntroBody")}</p>
            <button className="btn primary" style={{ marginTop: 18 }} disabled={busy} onClick={startTest}>
              {t("pages.onboarding.startTest")}
            </button>
            <button className="btn ghost" style={{ marginTop: 10 }} disabled={busy} onClick={skipTest}>
              {t("pages.onboarding.skipTest")}
            </button>
          </>
        )}

        {step === "test" && q && (
          <>
            <div className="row spread">
              <span className="ilb">{t("pages.onboarding.questionProgress", { current: qIdx + 1, total: questions.length })}</span>
              <span className="ilb">HSK{q.level}</span>
            </div>
            <h2 className="h2" style={{ marginTop: 14, fontSize: 22 }}>{q.prompt}</h2>

            <div className="col" style={{ marginTop: 14, gap: 10 }}>
              {q.options &&
                q.options.map((opt) => (
                  <button key={opt} className="option" onClick={() => answerQuestion(opt)} disabled={busy}>
                    {opt}
                  </button>
                ))}
              {!q.options && q.type === "recognition" && (
                <div className="row center" style={{ justifyContent: "center" }}>
                  <MicRecorder onTranscript={(text) => answerQuestion(text)} disabled={busy} />
                  <span className="muted" style={{ fontSize: 12 }}>{t("pages.onboarding.sayItAloud")}</span>
                </div>
              )}
            </div>
          </>
        )}

        {step === "result" && result && (
          <div className="center">
            <div className="reveal-icon" style={{ fontSize: 52 }}>
              <Icon name="sparkles" size={44} />
            </div>
            <h1 className="h1">{t("pages.onboarding.resultTitle")}</h1>
            <p className="sub">{t("pages.onboarding.resultLevel", { level: result.placed_level })}</p>
            {result.total_count > 0 && (
              <p className="sub">{t("pages.onboarding.resultScore", { correct: result.correct_count, total: result.total_count })}</p>
            )}
            <button className="btn primary" style={{ marginTop: 18 }} onClick={() => navigate("/dashboard", { replace: true })}>
              {t("pages.onboarding.continueToDashboard")}
            </button>
          </div>
        )}

      </div>
    </Layout>
  );
}
