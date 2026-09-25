// Shared Mandarin speechSynthesis helper — the one place in the app that
// turns Chinese text into audio. Extracted from VoiceCompanion.jsx so the
// Hanzi pronunciation button reuses the exact same voice-selection logic
// instead of a second copy: explicit zh-CN, and (when the browser actually
// exposes one) an explicit Chinese SpeechSynthesisVoice rather than
// whatever the browser/system default happens to be.

let cachedZhVoice;

export function pickChineseVoice() {
  if (typeof window === "undefined" || !window.speechSynthesis) return null;
  const voices = window.speechSynthesis.getVoices();
  if (!voices.length) return cachedZhVoice ?? null;
  const zhVoices = voices.filter((v) => v.lang && v.lang.toLowerCase().startsWith("zh"));
  cachedZhVoice =
    zhVoices.find((v) => v.lang.toLowerCase() === "zh-cn") ||
    zhVoices.find((v) => v.lang.toLowerCase().startsWith("zh-cn")) ||
    zhVoices[0] ||
    null;
  return cachedZhVoice;
}

if (typeof window !== "undefined" && window.speechSynthesis) {
  // addEventListener (not `.onvoiceschanged =`) so this never overwrites a
  // handler some other page sets on the same shared speechSynthesis object.
  window.speechSynthesis.addEventListener("voiceschanged", pickChineseVoice);
}

/**
 * Speaks `text` aloud in Mandarin Chinese. `options.profile` (optional)
 * carries {rate, pitch, volume} for a per-character voice (e.g. the Daily
 * Voice Companion's per-animal profile); omitted, it just uses natural
 * defaults -- both paths always set lang + an explicit Chinese voice.
 * Fails silently (calls onEnd) if the browser has no speechSynthesis at
 * all, rather than throwing -- audio is a nice-to-have, never a blocker.
 */
export function speakChinese(text, { profile, onStart, onEnd } = {}) {
  if (!text || typeof window === "undefined" || !window.speechSynthesis) {
    onEnd?.();
    return;
  }
  const utter = new SpeechSynthesisUtterance(text.replace(/^[^：:]+[：:]\s*/, ""));
  utter.lang = "zh-CN";
  const zhVoice = pickChineseVoice();
  if (zhVoice) utter.voice = zhVoice;
  if (profile) {
    utter.rate = profile.rate;
    utter.pitch = profile.pitch;
    utter.volume = profile.volume;
  }
  utter.onstart = onStart;
  utter.onend = onEnd;
  utter.onerror = onEnd;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utter);
}
