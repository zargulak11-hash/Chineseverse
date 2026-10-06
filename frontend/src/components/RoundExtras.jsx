import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api.js";
import { canSpeakChinese, speakChinese } from "../zhSpeech.js";
import Icon from "./Icon.jsx";
import MicRecorder, { micSupported } from "./MicRecorder.jsx";

// Pieces Practice.jsx adds for Real Chinese scenes and One Sentence lessons.
// Everything shown is what the server rendered for the stored round
// (services/practice.py _render_virtual); grading and speaking scores come
// back from the API -- nothing here decides how the learner did.

// Speech at the tier's pace (beginners hear lines a little slower).
export function speakAt(text, rate) {
  speakChinese(text, rate ? { profile: { rate, pitch: 1, volume: 1 } } : undefined);
}

function HearButton({ text, rate, label, small = true }) {
  if (!text) return null;
  return (
    <button
      type="button"
      className={`btn${small ? " small" : ""} ghost`}
      onClick={() => speakAt(text, rate)}
      aria-label={label}
      title={label}
    >
      <Icon name="ear" size={14} style={{ verticalAlign: -2 }} />
    </button>
  );
}

// The other person's line of a scene question. Advanced learners hear it
// before they can read it (text is null until answered); on a device with
// no Chinese voice the line is shown so the question stays answerable.
export function NpcLine({ question, context }) {
  const { t } = useTranslation();
  const p = question.prompt || {};
  const hidden = !p.text;
  const fallback = hidden && !canSpeakChinese();
  return (
    <div className="bubble npc scene-line">
      <span className="speaker">
        <span lang="zh-CN">{context?.npc?.zh}</span> · {context?.npc?.role}
      </span>
      {hidden && !fallback ? (
        <div className="row" style={{ gap: 8, margin: 0 }}>
          <button type="button" className="btn small" onClick={() => speakAt(p.speak, p.rate)}>
            <Icon name="ear" size={14} style={{ verticalAlign: -2, marginRight: 6 }} />
            {t("realLife.listenLine")}
          </button>
          <span className="sub">{t("realLife.listenFirst")}</span>
        </div>
      ) : (
        <>
          <div className="row" style={{ gap: 8, margin: 0, alignItems: "center" }}>
            <span className="scene-line-zh" lang="zh-CN">{p.text || p.speak}</span>
            <HearButton text={p.speak} rate={p.rate} label={t("companionReact.hear")} />
          </div>
          {(p.pinyin || fallback) && <span className="pinyin">{p.pinyin}</span>}
          {p.translation && (
            <details className="scene-translation">
              <summary className="sub">{t("realLife.showTranslation")}</summary>
              <span className="english">{p.translation}</span>
            </details>
          )}
        </>
      )}
    </div>
  );
}

// The conversation so far: every exchange already answered in this round,
// with the fitting reply (the server's answer card), not the learner's pick.
export function SceneThread({ questions, upTo, context }) {
  const { t } = useTranslation();
  const done = questions.filter((q) => q.index < upTo && q.type === "scene_reply" && q.answer);
  if (done.length === 0) return null;
  return (
    <div className="card scene-thread">
      <p className="side-title">{t("realLife.conversationSoFar")}</p>
      <div className="chat">
        {done.map((q) => (
          <div key={q.index} className="scene-exchange">
            <div className="bubble npc">
              <span className="speaker" lang="zh-CN">{context?.npc?.zh}</span>
              <span lang="zh-CN">{q.prompt.text}</span>
              {q.prompt.pinyin && <span className="pinyin">{q.prompt.pinyin}</span>}
            </div>
            <div className="bubble me">
              <span lang="zh-CN">{q.answer.card.hanzi}</span>
              <span className="pinyin">{q.answer.card.pinyin}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// "Now say it": the reply / sentence just answered, spoken into the mic and
// graded by the server against the stored line (POST .../speak).
export function SpeakLine({ sessionId, index, text, onSpoken }) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function send(transcript) {
    setBusy(true);
    setError("");
    try {
      const r = await api.post(`/practice/sessions/${sessionId}/speak`, { index, spoken_text: transcript });
      setResult(r);
      onSpoken?.(r);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const done = result && result.attempts_left <= 0;
  return (
    <div className="speak-line" aria-live="polite">
      <p className="side-title">{t("realLife.sayIt")}</p>
      <div className="row" style={{ gap: 12, margin: 0, alignItems: "center" }}>
        {/* Speaking is graded from what the browser heard, so there is no
            typed stand-in: without speech recognition the round simply
            goes on without this optional step. */}
        {micSupported && <MicRecorder onTranscript={send} disabled={busy || done} />}
        <div style={{ minWidth: 0 }}>
          <span className="scene-line-zh" lang="zh-CN">{text}</span>
          <div className="sub">
            {!micSupported ? t("voice.micUnsupportedSkip") : busy ? t("realLife.grading") : t("realLife.sayItHint")}
          </div>
        </div>
      </div>
      {result && (
        <div className="speak-result">
          <span className={`badge ${result.is_correct ? "good" : "accent"}`}>
            {result.is_correct ? t("realLife.spokenWell") : t("realLife.spokenAgain")}
          </span>
          <span className="sub">
            {t("realLife.heard")}: <span lang="zh-CN">{result.transcript || "—"}</span>
          </span>
          <span className="sub">
            {t("realLife.speakScore", { overall: Math.round(result.scores.overall), tones: Math.round(result.scores.tones) })}
          </span>
          {result.attempts_left > 0 && (
            <span className="sub">{t("realLife.attemptsLeft", { count: result.attempts_left })}</span>
          )}
        </div>
      )}
      {error && <p className="formerr">{error}</p>}
    </div>
  );
}

// Side-panel summary of what this round is about.
export function RoundContextCard({ context }) {
  const { t, i18n } = useTranslation();
  if (!context) return null;
  if (context.kind === "scene") {
    return (
      <div className="card side-card">
        <p className="side-title">{t("nav.realChinese")}</p>
        <div className="row" style={{ margin: 0, gap: 12 }}>
          <span className="scene-icon" aria-hidden="true">{context.icon}</span>
          <div style={{ minWidth: 0 }}>
            <b>{context.title}</b>
            <div className="sub"><span lang="zh-CN">{context.npc?.zh}</span> · {context.npc?.role}</div>
          </div>
        </div>
        <span className="badge accent" style={{ marginTop: 12 }}>{t(`realLife.tier.${context.tier}`)}</span>
        <p className="sub" style={{ marginTop: 8 }}>{t(`realLife.tierHow.${context.tier}`)}</p>
      </div>
    );
  }
  if (context.kind === "case") {
    const p = context.profile || {};
    return (
      <div className="card side-card">
        <p className="side-title">{t("nav.detective")}</p>
        <div className="row" style={{ margin: 0, gap: 12 }}>
          <span className="scene-icon" aria-hidden="true">{context.icon}</span>
          {/* A case file carries its own title; a generated case is named by its structure. */}
          <b>{context.file ? (context.titles?.[i18n.language] || context.titles?.en) : t(`detective.case.${context.case}.title`)}</b>
        </div>
        <span className="badge accent" style={{ marginTop: 12 }}>{t(`realLife.tier.${context.tier}`)}</span>
        <ul className="scene-rules">
          <li>{t("detective.profile.suspects", { count: p.suspects })}</li>
          {!context.file && <li>{t("detective.profile.listen", { pct: Math.round((p.listen_share || 0) * 100) })}</li>}
          {p.evidence_notes > 0 && <li>{t("detective.profile.evidence", { count: p.evidence_notes })}</li>}
        </ul>
      </div>
    );
  }
  if (context.kind === "internet") {
    return (
      <div className="card side-card">
        <p className="side-title">{t("nav.internet")}</p>
        <div className="row" style={{ margin: 0, gap: 12 }}>
          <span className="scene-icon" aria-hidden="true">{context.icon}</span>
          <div>
            <b lang="zh-CN">{context.title}</b>
            <div className="sub" lang="zh-CN">{context.source}</div>
          </div>
        </div>
        <span className="badge accent" style={{ marginTop: 12 }}>{t(`internet.version.${context.version}`)}</span>
      </div>
    );
  }
  if (context.kind === "pronunciation") {
    const lang = i18n.language;
    return (
      <div className="card side-card">
        <p className="side-title">{t("soundWorld.pron.title")}</p>
        <div className="row" style={{ margin: 0, gap: 12 }}>
          <span className="scene-icon" aria-hidden="true">{context.icon}</span>
          <div style={{ minWidth: 0 }}>
            <b>{context.titles?.[lang] || context.titles?.en}</b>
            <div className="sub" lang="zh-CN">{context.titles?.zh}</div>
          </div>
        </div>
        <p className="sub" style={{ marginTop: 12 }}>{context.how?.[lang] || context.how?.en}</p>
      </div>
    );
  }
  if (context.kind === "sound") {
    return (
      <div className="card side-card">
        <p className="side-title">{t("nav.soundWorld")}</p>
        <div className="row" style={{ margin: 0, gap: 12 }}>
          <span className="scene-icon" aria-hidden="true">{context.icon}</span>
          <div>
            <b>{t(`soundWorld.env.${context.env}`)}</b>
            <div className="sub" lang="zh-CN">{context.zh}</div>
          </div>
        </div>
        <span className="badge accent" style={{ marginTop: 12 }}>{t(`soundWorld.stage.${context.stage}`)}</span>
      </div>
    );
  }
  return (
    <div className="card side-card">
      <p className="side-title">{t("nav.sentence")}</p>
      <div className="row" style={{ margin: 0, gap: 8 }}>
        <span className="scene-line-zh" lang="zh-CN">{context.text}</span>
        <HearButton text={context.text} label={t("companionReact.hear")} />
      </div>
      {context.pinyin && <div className="sub">{context.pinyin}</div>}
    </div>
  );
}
