import { useEffect, useRef, useState } from "react";

const SpeechRecognitionImpl =
  typeof window !== "undefined"
    ? window.SpeechRecognition || window.webkitSpeechRecognition
    : null;

// Real microphone capture: uses the browser's own speech recognizer (Web
// Speech API) to turn spoken Chinese into text, then hands that text to the
// caller exactly like typed input. No audio ever leaves the browser — only
// the recognized transcript is sent to our backend for scoring.
export default function MicRecorder({ onTranscript, lang = "zh-CN", disabled }) {
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
        Voice input needs Chrome or Edge — type instead.
      </span>
    );
  }

  return (
    <button
      type="button"
      className={`micbtn${state === "listening" ? " listening" : ""}`}
      onClick={state === "listening" ? stop : start}
      disabled={disabled}
      title={state === "listening" ? "Listening… click to stop" : "Click to speak"}
    >
      {state === "listening" ? "⏹" : "🎤"}
    </button>
  );
}
