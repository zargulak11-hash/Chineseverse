import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.js";
import BrandLogo from "../components/BrandLogo.jsx";
import CompanionPicker from "../components/CompanionPicker.jsx";
import Icon from "../components/Icon.jsx";
import MicRecorder from "../components/MicRecorder.jsx";
import { nextTitle } from "../components/NextStep.jsx";
import { Loading } from "../components/ui.jsx";
import { SUPPORTED_LANGS } from "../i18n.js";
import { usePrefs } from "../prefs.jsx";

const MOTIVATIONS = ["travel", "work", "culture", "exam", "family", "other"];
const SOURCES = ["friend", "social", "school", "search", "other"];

// The three stages shown in the progress bar, and the screens in each.
const STAGES = [
  { key: "companion", steps: ["companion"] },
  { key: "questions", steps: ["motivation", "discovery"] },
  { key: "level", steps: ["intro", "test"] },
  { key: "ready", steps: ["result"] },
];

// The closing screen's "how ChineseVerse works": the four things a new
// learner meets every day, in the order they meet them.
const HOW = [
  ["route", "next"],
  ["book", "lessons"],
  ["clock", "review"],
  ["crosshair", "notebook"],
];

// Where a learner (re)enters onboarding: the first step whose answer the
// server doesn't have yet. Every step is saved the moment it's answered, so
// a refresh, a closed tab or a new sign-in resumes here instead of starting
// over -- it used to restart at the first question every time, which is how
// the questions kept coming back.
function resumeStep(me) {
  if (!me.user.animal_id) return "companion";
  if (!me.profile.learning_motivation) return "motivation";
  if (!me.profile.discovery_source) return "discovery";
  return "intro";
}

// Back only ever moves between onboarding's own screens.
const BACK = { motivation: "companion", discovery: "motivation", intro: "discovery", test: "intro" };

// The one-time setup a new account goes through before the app opens:
// companion -> two questions -> level (placement test, or "complete
// beginner"). It is full-screen on purpose (App.jsx renders it outside the
// app shell): no sidebar or menu to wander off by. Finishing the level step
// is what marks onboarding complete on the server, and the server refuses it
// until the companion and both answers are saved (routers/onboarding.py).
export default function Onboarding() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { user, setCurrentUser, logout } = useAuth();
  const { soundEnabled } = usePrefs() || {};

  const [step, setStep] = useState("loading"); // loading|companion|motivation|discovery|intro|test|result
  const [loadError, setLoadError] = useState("");
  const [loadVersion, setLoadVersion] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const [animalId, setAnimalId] = useState(null);
  const [motivation, setMotivation] = useState(null);
  const [motivationOther, setMotivationOther] = useState("");
  const [source, setSource] = useState(null);
  const [sourceOther, setSourceOther] = useState("");

  const [attemptId, setAttemptId] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [qIdx, setQIdx] = useState(0);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [firstTask, setFirstTask] = useState(null); // the journey's next step once onboarding is done

  // Runs once (and on "try again") -- not on a language change, which only
  // re-renders the same step in the new language.
  useEffect(() => {
    let cancelled = false;
    setLoadError("");
    api
      .get("/me")
      .then((me) => {
        if (cancelled) return;
        if (me.user.onboarding_completed) {
          // Already done (e.g. finished in another tab): the route guard
          // takes it from here and opens the app.
          setCurrentUser(me.user);
          return;
        }
        const p = me.profile;
        setAnimalId(me.user.animal_id);
        setMotivation(p.learning_motivation || null);
        setMotivationOther(p.learning_motivation_other || "");
        setSource(p.discovery_source || null);
        setSourceOther(p.discovery_source_other || "");
        setStep(resumeStep(me));
      })
      .catch((err) => {
        if (!cancelled) setLoadError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [loadVersion]);

  function go(next) {
    setError("");
    setStep(next);
  }

  async function run(action) {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const chooseCompanion = (id) =>
    run(async () => {
      await api.post("/me/animal", { animal_id: id });
      setAnimalId(id);
      const me = await api.get("/me");
      setCurrentUser(me.user);
      go("motivation");
    });

  const saveMotivation = () =>
    run(async () => {
      await api.patch("/me/profile", {
        learning_motivation: motivation,
        learning_motivation_other: motivation === "other" ? motivationOther.trim() : null,
      });
      go("discovery");
    });

  const saveSource = () =>
    run(async () => {
      await api.patch("/me/profile", {
        discovery_source: source,
        discovery_source_other: source === "other" ? sourceOther.trim() : null,
      });
      go("intro");
    });

  const startTest = () =>
    run(async () => {
      const r = await api.post("/onboarding/placement-test/start");
      setAttemptId(r.attempt_id);
      setQuestions(r.questions);
      setAnswers({});
      setQIdx(0);
      go("test");
    });

  // Onboarding is complete on the server now; enter the app with the
  // server's own copy of the user (so the route guard lets them through).
  // Should that re-read fail, the completion call itself already succeeded.
  async function enterApp(to) {
    let next;
    try {
      next = (await api.get("/me")).user;
    } catch {
      next = { ...user, onboarding_completed: true };
    }
    setCurrentUser(next);
    navigate(to, { replace: true });
  }

  // Onboarding is complete on the server: ask the journey for the real
  // first task (for a beginner, step 1 of the foundation) so the closing
  // screen can start it. Without it the button still opens the journey.
  async function loadFirstTask() {
    try {
      setFirstTask((await api.get("/journey")).next || null);
    } catch {
      setFirstTask(null);
    }
  }

  // A complete beginner starts at HSK 1, without a test.
  const startAsBeginner = () =>
    run(async () => {
      const r = await api.post("/onboarding/placement-test/skip");
      await loadFirstTask();
      setResult(r);
      go("result");
    });

  const submitTest = (finalAnswers) =>
    run(async () => {
      const payload = {
        answers: Object.entries(finalAnswers).map(([index, answer]) => ({
          index: Number(index),
          answer,
        })),
      };
      const r = await api.post(`/onboarding/placement-test/${attemptId}/submit`, payload);
      await loadFirstTask();
      setResult(r);
      go("result");
    });

  function answerQuestion(value) {
    const q = questions[qIdx];
    const nextAnswers = { ...answers, [q.index]: value };
    setAnswers(nextAnswers);
    if (qIdx + 1 < questions.length) {
      setQIdx(qIdx + 1);
    } else {
      submitTest(nextAnswers);
    }
  }

  function signOut() {
    logout();
    navigate("/", { replace: true });
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

  const stageIdx = STAGES.findIndex((s) => s.steps.includes(step));
  const wide = step === "companion";

  let body;
  if (loadError) {
    body = (
      <section className="card onboard-card" role="alert">
        <h1 className="h1">{t("pages.onboarding.loadErrorTitle")}</h1>
        <p className="sub">{loadError}</p>
        <button type="button" className="btn primary" style={{ marginTop: 16 }} onClick={() => setLoadVersion((v) => v + 1)}>
          {t("pages.onboarding.retry")}
        </button>
      </section>
    );
  } else if (step === "loading") {
    body = <Loading>{t("pages.onboarding.loading")}</Loading>;
  } else {
    body = (
      <>
        <p className="page-eyebrow">
          <Icon name="sparkles" size={13} /> {t("pages.onboarding.eyebrow")}
        </p>
        <ol className="onboard-steps" aria-label={t("pages.onboarding.stepsLabel")}>
          {STAGES.map((s, i) => (
            <li
              key={s.key}
              className={i < stageIdx ? "is-done" : i === stageIdx ? "is-current" : ""}
              aria-current={i === stageIdx ? "step" : undefined}
            >
              {t(`pages.onboarding.stage.${s.key}`)}
            </li>
          ))}
        </ol>

        <section key={step} className={wide ? "onboard-panel" : "card onboard-card"}>
          {BACK[step] && (
            <button type="button" className="btn small ghost onboard-back" disabled={busy} onClick={() => go(BACK[step])}>
              ← {t("common.back")}
            </button>
          )}
          {error && (
            <p className="formerr" role="alert">
              {error}
            </p>
          )}

          {step === "companion" && (
            <>
              <h1 className="h1">{t("pages.animalSelect.title")}</h1>
              <p className="sub">{t("pages.onboarding.companionSub")}</p>
              <CompanionPicker picked={animalId} busy={busy} onChoose={chooseCompanion} />
            </>
          )}

          {step === "motivation" && (
            <>
              <h1 className="h1">{t("pages.onboarding.motivationTitle")}</h1>
              <p className="sub">{t("pages.onboarding.motivationSubtitle")}</p>
              <div className="col" style={{ marginTop: 16, gap: 8 }}>
                {MOTIVATIONS.map((key) => (
                  <button
                    key={key}
                    type="button"
                    className={`option${motivation === key ? " picked" : ""}`}
                    aria-pressed={motivation === key}
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
                    maxLength={200}
                    aria-label={t("pages.onboarding.otherPlaceholder")}
                    onChange={(e) => setMotivationOther(e.target.value)}
                    placeholder={t("pages.onboarding.otherPlaceholder")}
                  />
                </div>
              )}
              <button
                type="button"
                className="btn primary"
                style={{ marginTop: 16 }}
                disabled={busy || !motivation || (motivation === "other" && !motivationOther.trim())}
                onClick={saveMotivation}
              >
                {busy ? t("pages.onboarding.saving") : t("pages.onboarding.next")}
              </button>
            </>
          )}

          {step === "discovery" && (
            <>
              <h1 className="h1">{t("pages.onboarding.discoveryTitle")}</h1>
              <div className="col" style={{ marginTop: 16, gap: 8 }}>
                {SOURCES.map((key) => (
                  <button
                    key={key}
                    type="button"
                    className={`option${source === key ? " picked" : ""}`}
                    aria-pressed={source === key}
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
                    maxLength={200}
                    aria-label={t("pages.onboarding.otherPlaceholder")}
                    onChange={(e) => setSourceOther(e.target.value)}
                    placeholder={t("pages.onboarding.otherPlaceholder")}
                  />
                </div>
              )}
              <button
                type="button"
                className="btn primary"
                style={{ marginTop: 16 }}
                disabled={busy || !source || (source === "other" && !sourceOther.trim())}
                onClick={saveSource}
              >
                {busy ? t("pages.onboarding.saving") : t("pages.onboarding.next")}
              </button>
            </>
          )}

          {step === "intro" && (
            // Three honest starting points: a complete beginner starts the
            // foundation (no test, level 1); anyone who knows some Chinese takes
            // the real placement test -- the level is never guessed.
            <>
              <h1 className="h1">{t("pages.onboarding.levelTitle")}</h1>
              <p className="sub">{t("pages.onboarding.levelSub")}</p>
              <div className="level-choices">
                <button type="button" className="level-choice is-primary" disabled={busy} onClick={startAsBeginner}>
                  <b>{t("pages.onboarding.levelBeginner")}</b>
                  <span className="sub">{t("pages.onboarding.levelBeginnerHint")}</span>
                </button>
                <button type="button" className="level-choice" disabled={busy} onClick={startTest}>
                  <b>{t("pages.onboarding.levelSome")}</b>
                  <span className="sub">{t("pages.onboarding.levelSomeHint")}</span>
                </button>
                <button type="button" className="level-choice" disabled={busy} onClick={startTest}>
                  <b>{t("pages.onboarding.levelStudy")}</b>
                  <span className="sub">{t("pages.onboarding.levelStudyHint")}</span>
                </button>
              </div>
            </>
          )}

          {step === "test" && q && (
            <>
              <div className="row spread">
                <span className="ilb">{t("pages.onboarding.questionProgress", { current: qIdx + 1, total: questions.length })}</span>
                <span className="ilb">HSK{q.level}</span>
              </div>
              <h2 className="h2 onboard-question">{q.prompt}</h2>

              <div className="col" style={{ marginTop: 16, gap: 8 }}>
                {q.options &&
                  q.options.map((opt) => (
                    <button key={opt} type="button" className="option" onClick={() => answerQuestion(opt)} disabled={busy}>
                      {opt}
                    </button>
                  ))}
                {!q.options && q.type === "recognition" && (
                  <div className="row center" style={{ justifyContent: "center" }}>
                    <MicRecorder onTranscript={(text) => answerQuestion(text)} disabled={busy} />
                    <span className="muted" style={{ fontSize: "var(--text-xs)" }}>{t("pages.onboarding.sayItAloud")}</span>
                  </div>
                )}
              </div>
              {/* A failed submit keeps the answers: send them again. */}
              {error && qIdx + 1 === questions.length && answers[q.index] !== undefined && (
                <button type="button" className="btn primary" style={{ marginTop: 16 }} disabled={busy} onClick={() => submitTest(answers)}>
                  {t("pages.onboarding.retry")}
                </button>
              )}
            </>
          )}

          {step === "result" && result && (
            // The last screen explains how ChineseVerse works before the
            // learner is in it, then starts their real first task.
            <>
              <h1 className="h1">{t("pages.onboarding.resultTitle")}</h1>
              <p className="sub">
                {t("pages.onboarding.resultLevel", { level: result.placed_level })}
                {result.total_count > 0 && <> · {t("pages.onboarding.resultScore", { correct: result.correct_count, total: result.total_count })}</>}
              </p>
              <h2 className="h2 onboard-how-title">{t("pages.onboarding.how.title")}</h2>
              <ul className="onboard-how">
                {HOW.map(([icon, key]) => (
                  <li key={key}>
                    <span className="onboard-how-icon"><Icon name={icon} size={17} /></span>
                    <span>
                      <b>{t(`pages.onboarding.how.${key}Title`)}</b>
                      <span className="sub">{t(`pages.onboarding.how.${key}`)}</span>
                    </span>
                  </li>
                ))}
              </ul>
              {firstTask && (
                <p className="onboard-first">
                  <span className="side-title">{t("pages.onboarding.how.firstTask")}</span>
                  <b>{nextTitle(t, firstTask)}</b>
                </p>
              )}
              <div className="row" style={{ gap: 12, marginTop: 16, flexWrap: "wrap" }}>
                <button type="button" className="btn primary" disabled={busy}
                        onClick={() => run(() => enterApp(firstTask?.to || "/journey"))}>
                  {t("pages.onboarding.how.start")}
                </button>
                <button type="button" className="btn ghost" disabled={busy} onClick={() => run(() => enterApp("/dashboard"))}>
                  {t("pages.onboarding.how.home")}
                </button>
              </div>
            </>
          )}
        </section>
      </>
    );
  }

  return (
    <div className="onboard">
      <header className="onboard-top">
        <BrandLogo className="brand-logo--boot" />
        <div className="onboard-tools">
          <div className="row onboard-langs" role="group" aria-label={t("settings.language")}>
            {SUPPORTED_LANGS.map((l) => (
              <button
                key={l.code}
                type="button"
                lang={l.code}
                className={`btn small${i18n.language === l.code ? " primary" : " ghost"}`}
                aria-pressed={i18n.language === l.code}
                onClick={() => i18n.changeLanguage(l.code)}
              >
                {l.label}
              </button>
            ))}
          </div>
          <button type="button" className="btn small ghost" onClick={signOut}>
            {t("common.logOut")}
          </button>
        </div>
      </header>
      <main className={`onboard-main${wide ? " is-wide" : ""}`}>{body}</main>
    </div>
  );
}
