import { TextToSpeech } from "@capacitor-community/text-to-speech";
import { isNativeApp } from "./platform.js";

// The phone's own text-to-speech engine, for the Android / iOS app. Android's
// WebView has no speechSynthesis at all (every listening exercise and
// pronunciation button would be silent there), and iOS's WKWebView one goes
// quiet with the ringer switch. zhSpeech.js routes through here inside the
// app and keeps using speechSynthesis on the website.
export const nativeSpeechEnabled = isNativeApp;

// speechSynthesis rates/pitches (0.1-10 / 0-2) map onto the plugin's
// directly; volume is the same 0-1.
function options(text, lang, profile) {
  const opts = { text, lang, rate: 1.0, pitch: 1.0, volume: 1.0, category: "playback" };
  if (profile) {
    if (profile.rate) opts.rate = profile.rate;
    if (profile.pitch) opts.pitch = profile.pitch;
    if (profile.volume != null) opts.volume = profile.volume;
  }
  return opts;
}

let generation = 0;

/**
 * Speaks each {text, lang} part in order. A newer call (or stopNative())
 * cancels the rest of an older queue, the way speechSynthesis.cancel() does.
 * onEnd is called once: after the last part, after a failure (no Chinese
 * voice installed), or when a newer call replaced this one.
 */
export async function speakNative(parts, { profile, onStart, onEnd } = {}) {
  const mine = ++generation;
  let started = false;
  try {
    await TextToSpeech.stop().catch(() => {});
    for (const part of parts) {
      if (mine !== generation) break;
      if (!started) {
        started = true;
        onStart?.();
      }
      await TextToSpeech.speak(options(part.text, part.lang, profile));
    }
  } catch {
    // Audio is a nice-to-have, never a blocker -- same as the web path.
  } finally {
    onEnd?.();
  }
}

export function stopNative() {
  generation += 1;
  TextToSpeech.stop().catch(() => {});
}
