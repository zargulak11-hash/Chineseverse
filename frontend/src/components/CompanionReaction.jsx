import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import CompanionFigure from "./CompanionFigure.jsx";
import Icon from "./Icon.jsx";
import { speakChinese } from "../zhSpeech.js";

// The learner's permanent companion reacting to a REAL, server-graded result.
// `reaction` comes straight from the API (app/services/companion_reaction.py:
// {mood, event, cause, zh, streak, focus, skill, words, ...}); nothing here
// decides how well the learner did. The companion says a short Chinese line
// (never translated), the explanation around it is localized, and the item
// it talks about is the real curriculum row -- with the curriculum's own
// example sentence when one exists. Moods are never shaming: a rough patch
// is the companion feeling it with the learner, not disappointment.
//
// `animal` must be the PERMANENT companion (dashboard.animal), never the
// Daily Voice Companion picked for one conversation.

// Causes where the companion points at the item to look at again.
const HELP_CAUSES = new Set([
  "miss", "streak_break", "two_misses", "mistake_run", "long_slump", "repeat_item", "tricky_item",
  "still_learning", "keep_practicing", "needs_review", "shaky_trace",
]);
// Causes where the item itself is the good news.
const WIN_CAUSES = new Set(["new_item", "mastered", "comeback", "writing_mastered", "clean_trace"]);

const pulses = new WeakMap();
let pulseSeq = 0;
function pulseOf(obj) {
  if (!pulses.has(obj)) pulses.set(obj, ++pulseSeq);
  return pulses.get(obj);
}

function Speak({ text, label }) {
  if (!text) return null;
  return (
    <button type="button" className="btn small ghost" onClick={() => speakChinese(text)} aria-label={label} title={label}>
      <Icon name="ear" size={13} style={{ verticalAlign: -2 }} />
    </button>
  );
}

export default function CompanionReaction({
  animal,
  reaction,
  context,
  size = 64,
  compact = false,
  focusMode = "full", // full | example | none -- Practice already shows the answer card
  settleAfter = 0, // ms after which the figure calms back to neutral
}) {
  const { t } = useTranslation();
  const [settled, setSettled] = useState(false);

  useEffect(() => {
    setSettled(false);
    if (!settleAfter || !reaction) return undefined;
    const id = setTimeout(() => setSettled(true), settleAfter);
    return () => clearTimeout(id);
  }, [reaction, settleAfter]);

  if (!reaction) return null;
  const mood = reaction.mood || "neutral";
  const cause = reaction.cause;
  const focus = reaction.focus;
  const name = animal?.name || t("companionReact.fallbackName");
  // Each species has its own way of voicing the same emotion.
  const voice = animal?.slug ? t(`companionReact.voice.${animal.slug}`, { defaultValue: "" }) : "";
  const legacyKey =
    reaction.event === "lesson_complete" ? "lessonComplete" : reaction.event === "review_clear" ? "reviewClear" : mood;
  const skill = reaction.skill;
  const skillName = skill ? t(`companionReact.skill.${skill.code}`, { defaultValue: skill.code }) : "";
  const vars = {
    name,
    skill: skillName,
    count: reaction.streak,
    misses: reaction.miss_streak,
    score: Math.round(reaction.score ?? reaction.accuracy ?? 0),
    due: reaction.due ?? 0,
    mistakes: reaction.mistakes ?? 0,
    noun: t(`companionReact.noun.${focus?.item_type || context || "vocab"}`),
  };
  const line = cause
    ? t(`companionReact.cause.${cause}`, { ...vars, defaultValue: t(`companionReact.${legacyKey}`, vars) })
    : t(`companionReact.${legacyKey}`, vars);
  const extra =
    context && (mood === "happy" || mood === "excited") && !WIN_CAUSES.has(cause)
      ? t(`companionReact.context.${context}`, { defaultValue: "" })
      : "";
  const showFocus = focus && focusMode !== "none" && (HELP_CAUSES.has(cause) || WIN_CAUSES.has(cause));
  const example = focus?.example;

  return (
    <div className={`companion-reaction mood-${mood}${compact ? " is-compact" : ""}`} role="status" aria-live="polite">
      {animal?.slug && (
        <CompanionFigure slug={animal.slug} mood={settled ? "neutral" : mood} size={size} pulse={pulseOf(reaction)} />
      )}
      <div className="companion-reaction-text">
        {reaction.zh && (
          <div className="cr-bubble" lang="zh-CN">
            <span>{reaction.zh}</span>
            <Speak text={reaction.zh} label={t("companionReact.hear")} />
          </div>
        )}
        <p className="cr-line">
          {voice && <span className="companion-voice">{voice} </span>}
          <span>{line}</span>
          {extra && <span className="sub" style={{ display: "block", marginTop: 2 }}>{extra}</span>}
        </p>

        {skill && (
          <span className="badge accent cr-skill">
            {skill.trained != null
              ? t("companionReact.skillTrained", { skill: skillName, value: Math.round(skill.value) })
              : t("companionReact.skillUp", { skill: skillName, value: Math.round(skill.value) })}
          </span>
        )}

        {showFocus && (focusMode === "full" || example) && (
          <div className="cr-focus">
            {focusMode === "full" && (
              <div>
                <span className="cr-focus-word" lang="zh-CN">{focus.hanzi}</span>
                {focus.pinyin && <span className="sub" style={{ color: "var(--accent2)" }}>{focus.pinyin} </span>}
                {focus.item_type !== "grammar" && <Speak text={focus.hanzi} label={t("companionReact.hear")} />}
                {focus.meaning && <div className="sub">{focus.meaning}</div>}
              </div>
            )}
            {example && (
              <div className="cr-example">
                <div style={{ minWidth: 0 }}>
                  <span className="sub" style={{ fontSize: 12 }}>{t("companionReact.example")} </span>
                  <span className="cr-example-zh" lang="zh-CN">{example}</span>
                  {focus.example_pinyin && <div className="sub" style={{ fontSize: 12 }}>{focus.example_pinyin}</div>}
                </div>
                <Speak text={example} label={t("companionReact.hear")} />
              </div>
            )}
          </div>
        )}

        {reaction.words?.length > 0 && (
          // Collapsed by default: the round's first question may ask about
          // one of these words, so peeking is the learner's own choice (like
          // re-reading the lesson), not something shown next to the answer.
          <details className="cr-words-toggle">
            <summary className="sub">{t("companionReact.lessonWords")}</summary>
            <div className="cr-words">
              {reaction.words.map((w) => (
                <button key={w.hanzi} type="button" className="cr-word" onClick={() => speakChinese(w.hanzi)}>
                  <b lang="zh-CN">{w.hanzi}</b>
                  <span className="sub" style={{ fontSize: 11 }}>{w.pinyin}</span>
                </button>
              ))}
            </div>
          </details>
        )}
      </div>
    </div>
  );
}
