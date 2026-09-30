import { useTranslation } from "react-i18next";
import AnimalAvatar from "./AnimalAvatar.jsx";

// The learner's permanent companion reacting to a REAL, server-graded result.
// `reaction` comes straight from the practice API ({mood, event, streak});
// nothing here decides how well the learner did. Moods are never shaming:
// a rough patch is "worried" in a supportive way, not disappointed.
const MOOD_STATE = {
  happy: "happy",
  excited: "excited",
  proud: "correct",
  celebrating: "celebrating",
  encouraging: "encouraging",
  worried: "thinking",
};

export default function CompanionReaction({ animal, reaction, context, size = 64 }) {
  const { t } = useTranslation();
  if (!reaction) return null;
  const mood = reaction.mood;
  const name = animal?.name || t("companionReact.fallbackName");
  // Each species has its own way of voicing the same emotion.
  const voice = animal?.slug ? t(`companionReact.voice.${animal.slug}`, { defaultValue: "" }) : "";
  const key =
    reaction.event === "lesson_complete" ? "lessonComplete" : reaction.event === "review_clear" ? "reviewClear" : mood;
  const line = t(`companionReact.${key}`, { name, count: reaction.streak });
  const extra =
    context && (mood === "happy" || mood === "excited")
      ? t(`companionReact.context.${context}`, { defaultValue: "" })
      : "";

  return (
    <div className={`companion-reaction mood-${mood}`} role="status" aria-live="polite">
      {animal?.slug && <AnimalAvatar slug={animal.slug} size={size} state={MOOD_STATE[mood] || "idle"} />}
      <div className="companion-reaction-text">
        {voice && <span className="companion-voice">{voice} </span>}
        <span>{line}</span>
        {extra && <span className="sub" style={{ display: "block", marginTop: 2 }}>{extra}</span>}
      </div>
    </div>
  );
}
