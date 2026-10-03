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

// Real microphone capture: uses the browser's own speech recognizer (Web
// Speech API) to turn spoken Chinese into text, then hands that text to the
// caller exactly like typed input. No audio ever leaves the browser — only
// the recognized transcript is sent to our backend for scoring.
export default function MicRecorder({ onTranscript, lang = "zh-CN", disabled }) {
  const { t } = useTranslation();
  const recognitionRef = useRef(null);
  const [state, setState] = useState(SpeechRecognitionImpl ? "idle" : "unsupported");

  useEffect(() => () => recognitionRef.current?.stop(), []);

  function start() {
    if (!SpeechRecognitionImpl || disabled || state === "listening") return;
    const recognition = new SpeechRecognitionImpl();
    recognition.lang = lang;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript || "";
      if (transcript) onTranscript?.(transcript);
    };
    recognition.onerror = () => setState("idle");
    recognition.onend = () => setState("idle");
    recognitionRef.current = recognition;
    setState("listening");
    recognition.start();
  }

  function stop() {
    recognitionRef.current?.stop();
    setState("idle");
  }

  if (state === "unsupported") {
    return (
      <span className="muted" style={{ fontSize: 11 }}>
        {t("voice.micUnsupported")}
      </span>
    );
  }

  return (
    <button
      type="button"
      className={`micbtn${state === "listening" ? " listening" : ""}`}
      onClick={state === "listening" ? stop : start}
      disabled={disabled}
      title={state === "listening" ? t("voice.micListening") : t("voice.micStart")}
      aria-label={state === "listening" ? t("voice.micListening") : t("voice.micStart")}
    >
      <Icon name={state === "listening" ? "stop" : "mic"} size={22} />
    </button>
  );
}
