// Derives a per-animal speechSynthesis voice profile (pitch/rate) from the
// SAME AnimalPersonality fields (energy/humor/patience/strictness) already
// shown elsewhere in the app -- not a new personality system, just a pure
// mapping so Wolf doesn't sound like Rabbit through the browser's TTS.
//
// Deliberately gender-neutral: pitch/rate are continuous dials driven by
// character traits, never a male/female voice pick.
const clamp = (v, min, max) => Math.min(max, Math.max(min, v));

export function deriveVoiceProfile(personalityRow) {
  const energy = personalityRow?.energy ?? 50;
  const humor = personalityRow?.humor ?? 50;
  const patience = personalityRow?.patience ?? 50;
  const strictness = personalityRow?.strictness ?? 50;

  const rate = clamp(0.82 + (energy / 100) * 0.55 - (patience / 100) * 0.25, 0.75, 1.35);
  const pitch = clamp(1.15 - (strictness / 100) * 0.35 + (humor / 100) * 0.15, 0.75, 1.35);

  return { rate: Number(rate.toFixed(2)), pitch: Number(pitch.toFixed(2)), volume: 1 };
}

// Short "Trait • Trait • voice descriptor" label for the selection cards,
// e.g. "Clever • playful • lively voice" -- built from the animal's own
// traits plus a voice adjective derived from the same profile above.
export function voiceLabel(personalityRow) {
  const traits = (personalityRow?.traits || "")
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean)
    .slice(0, 2);
  const { rate, pitch } = deriveVoiceProfile(personalityRow);

  let descriptor;
  if (rate >= 1.2) descriptor = "fast, energetic voice";
  else if (rate <= 0.85 && pitch >= 1.1) descriptor = "soft, gentle voice";
  else if (rate <= 0.85) descriptor = "calm, steady voice";
  else if (pitch <= 0.9) descriptor = "deep, confident voice";
  else if (pitch >= 1.15) descriptor = "light, bright voice";
  else descriptor = "warm, easygoing voice";

  return [...traits, descriptor].join(" • ");
}
