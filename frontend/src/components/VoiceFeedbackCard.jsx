import { motion } from "framer-motion";
import { popIn } from "../motion.js";
import { Bar } from "./ui.jsx";
import AnimalAvatar from "./AnimalAvatar.jsx";
import Icon from "./Icon.jsx";

const SCORE_FIELDS = [
  ["pronunciation", "Pronunciation", "mic"],
  ["tones", "Tones", "droplet"],
  ["fluency", "Fluency", "trending"],
  ["grammar", "Grammar", "book"],
];

function overallTone(score) {
  if (score >= 80) return "var(--good)";
  if (score >= 55) return "var(--accent)";
  return "var(--bad)";
}

// Reuses the existing voice-evaluation pipeline's own output (pronunciation/
// tones/fluency/grammar/overall + a coaching `feedback` sentence, already
// computed by services/voice_eval.py + ai_client.py) and gives it a mentor-
// style presentation: the coaching sentence leads, a companion avatar frames
// it as your companion talking to you, and the weakest sub-score gets an
// explicit, encouraging call-out — instead of a bare "72/100".
export default function VoiceFeedbackCard({ attempt, reaction, companionSlug, companionName }) {
  if (!attempt) return null;
  const scores = SCORE_FIELDS.map(([key, label, icon]) => ({ key, label, icon, value: attempt[key] ?? 0 }));
  const weakest = scores.reduce((a, b) => (b.value < a.value ? b : a), scores[0]);
  const overall = Math.round(attempt.overall ?? 0);

  return (
    <motion.div className="voice-feedback" variants={popIn} initial="initial" animate="animate">
      <div className="voice-feedback-head">
        {companionSlug ? (
          <AnimalAvatar slug={companionSlug} size={40} />
        ) : (
          <span className="sidebar-profile-fallback" style={{ width: 40, height: 40 }}>
            <Icon name="chat" size={18} />
          </span>
        )}
        <div className="voice-feedback-text">
          <b>{companionName ? `${companionName} says` : "Your companion says"}</b>
          <p className="sub" style={{ margin: 0 }}>{attempt.feedback || reaction || "Good attempt!"}</p>
        </div>
        <span className="voice-feedback-overall" style={{ color: overallTone(overall) }}>
          {overall}
          <small>/100</small>
        </span>
      </div>

      {reaction && attempt.feedback && <p className="voice-feedback-reaction">{reaction}</p>}

      <div className="voice-feedback-scores">
        {scores.map((s) => (
          <div key={s.key} className={`voice-score-row${s.key === weakest.key ? " weakest" : ""}`}>
            <Icon name={s.icon} size={13} />
            <span className="lbl">{s.label}</span>
            <Bar value={s.value} />
            <span className="val">{Math.round(s.value)}</span>
          </div>
        ))}
      </div>

      {weakest.value < 70 && (
        <p className="voice-feedback-tip">
          <Icon name="target" size={13} style={{ verticalAlign: -2, marginRight: 4 }} />
          Focus tip: <b>{weakest.label.toLowerCase()}</b> was your softest spot this time — that's exactly
          what {companionName || "your companion"} would drill next.
        </p>
      )}
    </motion.div>
  );
}
