import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import Icon from "./Icon.jsx";

const SpeechRecognitionImpl =
  typeof window !== "undefined"
    ? window.SpeechRecognition || window.webkitSpeechRecognition
    : null;

// Whether this browser can turn speech into text at all (Chrome, Edge,
// Safari: yes; Firefox: no Web Speech recognition). Callers without a typed
// alternative use it to say so instead of showing a dead mic.
export const micSupported = Boolean(SpeechRecognitionImpl);

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
  const [state, setState] = useState(SpeechRecognitionImpl ? "idle" : "unsupported");
  const [error, setError] = useState("");

  useEffect(() => () => recognitionRef.current?.abort?.(), []);

  function start() {
    if (!SpeechRecognitionImpl || disabled || state === "listening") return;
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
