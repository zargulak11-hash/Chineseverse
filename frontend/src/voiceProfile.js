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

// Which kind of voice the profile above produces, as an i18n key under
// voice.tone.* (fast / soft / calm / deep / light / warm). This used to be an
// English "trait • trait • voice" string; the raw traits exist only in
// English, so the picker shows the animal's localized personality instead.
export function voiceTone(personalityRow) {
  const { rate, pitch } = deriveVoiceProfile(personalityRow);
  if (rate >= 1.2) return "fast";
  if (rate <= 0.85 && pitch >= 1.1) return "soft";
  if (rate <= 0.85) return "calm";
  if (pitch <= 0.9) return "deep";
  if (pitch >= 1.15) return "light";
  return "warm";
}
