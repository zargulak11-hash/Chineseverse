import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { SpeechRecognition as NativeRecognition } from "@capgo/capacitor-speech-recognition";
import { isNativeApp } from "../platform.js";
import Icon from "./Icon.jsx";

// Neither app WebView (Android, iOS) has the Web Speech recognizer, so the
// Android / iOS app uses the phone's own one through a plugin instead; the
// website never does.
const SpeechRecognitionImpl =
  typeof window !== "undefined" && !isNativeApp
    ? window.SpeechRecognition || window.webkitSpeechRecognition
    : null;

// Whether this browser can turn speech into text at all (Chrome, Edge,
// Safari: yes; Firefox: no Web Speech recognition). Callers without a typed
// alternative use it to say so instead of showing a dead mic. In the app
// the phone's recognizer is asked when the learner taps the mic.
export const micSupported = isNativeApp || Boolean(SpeechRecognitionImpl);

// The recognizer's error codes, each with what the learner can do about it.
// "aborted" is our own stop() and says nothing.
const ERRORS = {
  "not-allowed": "voice.micDenied",
  "service-not-allowed": "voice.micDenied",
  "no-speech": "voice.micNoSpeech",
  "audio-capture": "voice.micNoDevice",
  network: "voice.micNetwork",
  "language-not-supported": "voice.micLanguage",
};

// Real microphone capture: uses the browser's own speech recognizer (Web
// Speech API) to turn speech into text, then hands that text to the caller
// exactly like typed input. No audio is sent to our backend -- only the
// recognized transcript. `showStatus` renders the listening / error line
// next to the button (callers with no room for it leave it off and still
// get the error in the button's title).
export default function MicRecorder({ onTranscript, lang = "zh-CN", disabled, showStatus = false }) {
  const { t } = useTranslation();
  const recognitionRef = useRef(null);
  const [state, setState] = useState(micSupported ? "idle" : "unsupported");
  const [error, setError] = useState("");
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      recognitionRef.current?.abort?.();
      if (isNativeApp) NativeRecognition.stop().catch(() => {});
    };
  }, []);

  // The phone's recognizer: asks for the microphone / speech permission the
  // first time, listens for one phrase and resolves with what it heard. Only
  // the transcript reaches the caller, as on the web.
  async function startNative() {
    setError("");
    setState("listening");
    try {
      const { available } = await NativeRecognition.available();
      if (!available) {
        setError(t("voice.micNoDevice"));
        return;
      }
      const permission = await NativeRecognition.requestPermissions();
      if (permission.speechRecognition !== "granted") {
        setError(t("voice.micDenied"));
        return;
      }
      const { matches } = await NativeRecognition.start({ language: lang, maxResults: 1, partialResults: false, popup: false });
      const transcript = matches?.[0] || "";
      if (!mountedRef.current) return;
      if (transcript) onTranscript?.(transcript);
      else setError(t("voice.micNoSpeech"));
    } catch {
      if (mountedRef.current) setError(t("voice.micNoSpeech"));
    } finally {
      if (mountedRef.current) setState("idle");
    }
  }

  function start() {
    if (disabled || state === "listening") return;
    if (isNativeApp) {
      startNative();
      return;
    }
    if (!SpeechRecognitionImpl) return;
    const recognition = new SpeechRecognitionImpl();
    recognition.lang = lang;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    let heard = false;
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript || "";
      if (transcript) {
        heard = true;
        onTranscript?.(transcript);
      }
    };
    recognition.onerror = (event) => {
      const key = ERRORS[event.error];
      if (key) setError(t(key));
      setState("idle");
    };
    recognition.onend = () => {
      setState("idle");
      if (!heard) setError((e) => e || t("voice.micNoSpeech"));
    };
    recognitionRef.current = recognition;
    setError("");
    try {
      recognition.start();
      setState("listening");
    } catch {
      setError(t("voice.micNoDevice"));
      setState("idle");
    }
  }

  function stop() {
    if (isNativeApp) NativeRecognition.stop().catch(() => {});
    recognitionRef.current?.stop();
  }

  if (state === "unsupported") {
    return (
      <span className="muted" style={{ fontSize: 11 }}>
        {t("voice.micUnsupported")}
      </span>
    );
  }

  const label = state === "listening" ? t("voice.micListening") : error || t("voice.micStart");
  return (
    <span className="mic-wrap">
      <button
        type="button"
        className={`micbtn${state === "listening" ? " listening" : ""}`}
        onClick={state === "listening" ? stop : start}
        disabled={disabled}
        title={label}
        aria-label={state === "listening" ? t("voice.micListening") : t("voice.micStart")}
        aria-pressed={state === "listening"}
      >
        <Icon name={state === "listening" ? "stop" : "mic"} size={22} />
      </button>
      {showStatus && (state === "listening" || error) && (
        <span className={`mic-status${error && state !== "listening" ? " bad" : ""}`} role="status">
          {state === "listening" ? t("voice.micListening") : error}
        </span>
      )}
    </span>
  );
}
