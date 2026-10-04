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
 * Whether this device can say Chinese aloud: false without speechSynthesis,
 * or once the voice list has loaded and holds no Chinese voice. An empty
 * list (still loading) counts as able -- the browser may yet provide one.
 */
export function canSpeakChinese() {
  if (typeof window === "undefined" || !window.speechSynthesis) return false;
  const voices = window.speechSynthesis.getVoices();
  return !voices.length || !!pickChineseVoice();
}

const VOICE_LANG = { en: "en", ru: "ru", tg: "tg", zh: "zh" };

function voiceFor(locale) {
  if (typeof window === "undefined" || !window.speechSynthesis) return null;
  const prefix = VOICE_LANG[locale] || "en";
  return window.speechSynthesis.getVoices().find((v) => v.lang && v.lang.toLowerCase().startsWith(prefix)) || null;
}

/** Whether this device has a voice for the interface language `locale`. */
export function canSpeakLocale(locale) {
  return locale === "zh" ? canSpeakChinese() : !!voiceFor(locale);
}

/**
 * Reads a mixed answer aloud (the assistant's replies): runs of Chinese with
 * the Chinese voice, everything else with a voice for the interface
 * language `locale`. Without such a voice (Tajik often has none) only the
 * Chinese is read -- never Tajik through a Russian voice. Markdown marks are
 * not read out. Calls onEnd once when everything has been spoken, or at once
 * when there was nothing to say.
 */
export function speakText(text, locale, { onEnd } = {}) {
  if (!text || typeof window === "undefined" || !window.speechSynthesis) {
    onEnd?.();
    return;
  }
  const clean = text.replace(/\*\*|^\s*[*#-]+\s*/gm, "").replace(/[*_`#]/g, "");
  const runs = clean.match(/[㐀-鿿，。！？、；：“”‘’（）《》·…—]+|[^㐀-鿿]+/g) || [];
  const localVoice = locale === "zh" ? null : voiceFor(locale);
  const zhVoice = pickChineseVoice();
  const queue = [];
  for (const run of runs) {
    const isZh = /[㐀-鿿]/.test(run);
    if (!isZh && (!localVoice || !/[\p{L}\p{N}]/u.test(run))) continue;
    const utter = new SpeechSynthesisUtterance(run.trim());
    utter.lang = isZh ? "zh-CN" : localVoice.lang;
    utter.voice = isZh ? zhVoice || null : localVoice;
    queue.push(utter);
  }
  window.speechSynthesis.cancel();
  if (!queue.length) {
    onEnd?.();
    return;
  }
  const last = queue[queue.length - 1];
  last.onend = () => onEnd?.();
  last.onerror = () => onEnd?.();
  queue.forEach((u) => window.speechSynthesis.speak(u));
}

export function stopSpeaking() {
  if (typeof window !== "undefined" && window.speechSynthesis) window.speechSynthesis.cancel();
}

/**
 * Speaks `text` aloud in Mandarin Chinese. `options.profile` (optional)
 * carries {rate, pitch, volume} for a per-character voice (e.g. the Daily
 * Voice Companion's per-animal profile); omitted, it just uses natural
 * defaults -- both paths always set lang + an explicit Chinese voice.
 * Fails silently (calls onEnd) if the browser has no speechSynthesis at
 * all, rather than throwing -- audio is a nice-to-have, never a blocker.
 */
// `whole`: read the text as written. By default a leading "Speaker：" label
// is dropped (dialogue lines); narration like 服务员问：“…” needs all of it.
export function speakChinese(text, { profile, onStart, onEnd, whole = false } = {}) {
  if (!text || typeof window === "undefined" || !window.speechSynthesis) {
    onEnd?.();
    return;
  }
  const utter = new SpeechSynthesisUtterance(whole ? text : text.replace(/^[^：:]+[：:]\s*/, ""));
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
