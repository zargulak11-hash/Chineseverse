import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { speakChinese } from "../zhSpeech.js";
import Icon from "./Icon.jsx";

// A question answered from memory (type_word / type_pinyin): the learner
// types the word or the reading, and the server grades it
// (services/recall.py). "I don't know" sends an empty answer -- an honest
// one, which brings the item back sooner than a guess would.
export function RecallForm({ question, busy, answered, typed, retry, onSubmit }) {
  const { t } = useTranslation();
  const [text, setText] = useState("");
  const input = useRef(null);
  useEffect(() => {
    setText("");
  }, [question.index]);
  useEffect(() => {
    if (!answered) input.current?.focus();
  }, [answered, retry, question.index]);

  function submit(e) {
    e.preventDefault();
    if (!busy && !answered && text.trim()) onSubmit(text);
  }

  return (
    <form className="recall-form" onSubmit={submit}>
      <p className="sub recall-why">
        <span className="badge accent">{t("practice.recall.badge")}</span> {t("practice.recall.why")}
      </p>
      <div className="recall-row">
        <input
          ref={input}
          className="input recall-input"
          value={answered ? typed ?? "" : text}
          onChange={(e) => setText(e.target.value)}
          aria-label={t("practice.recall.label")}
          placeholder={t("practice.recall.label")}
          maxLength={40}
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="none"
          spellCheck={false}
          readOnly={answered}
          disabled={busy && !answered}
        />
        {!answered && (
          <>
            <button type="submit" className="btn primary" disabled={busy || !text.trim()}>
              {t("practice.recall.check")}
            </button>
            <button type="button" className="btn ghost" disabled={busy} onClick={() => onSubmit("")}>
              {t("practice.recall.dontKnow")}
            </button>
          </>
        )}
      </div>
      {retry && !answered ? (
        <p className="recall-retry" role="status" aria-live="polite">{t("practice.recall.addTones")}</p>
      ) : (
        !answered && <p className="sub recall-hint">{t("practice.recall.toneHint")}</p>
      )}
    </form>
  );
}

// "Explain my answer" (like Duolingo Max): on a wrong answer the learner can
// ask for an AI explanation, written by the server from the stored question
// and their stored answer (POST /practice/sessions/{id}/questions/{i}/explain),
// with one example sentence. Unavailable AI is said plainly.
export function ExplainAnswer({ sessionId, index }) {
  const { t } = useTranslation();
  const [state, setState] = useState(null); // null | "loading" | {data} | {error}
  async function ask() {
    setState("loading");
    try {
      setState({ data: await api.post(`/practice/sessions/${sessionId}/questions/${index}/explain`) });
    } catch (e) {
      setState({ error: e.message });
    }
  }
  if (state === null) {
    return (
      <button type="button" className="btn small" style={{ marginTop: 8 }} onClick={ask}>
        <Icon name="sparkles" size={13} /> {t("practice.explainBtn")}
      </button>
    );
  }
  if (state === "loading") return <p className="sub" role="status" style={{ marginTop: 8 }}>{t("practice.explainLoading")}</p>;
  if (state.error) return <p className="sub" role="alert" style={{ marginTop: 8 }}>{state.error}</p>;
  const { explanation, example } = state.data;
  return (
    <div className="practice-why" aria-live="polite">
      <p>{explanation}</p>
      {example?.zh && (
        <p>
          <button type="button" className="btn small ghost" onClick={() => speakChinese(example.zh)} aria-label={t("pages.hanzi.hear")}>
            <Icon name="ear" size={13} />
          </button>{" "}
          <b lang="zh-CN">{example.zh}</b> <span className="sub">{example.pinyin}</span>
          {example.translation && <span className="sub"> — {example.translation}</span>}
        </p>
      )}
      <p className="sub" style={{ fontSize: "var(--text-xs)" }}>{t("practice.explainNote")}</p>
    </div>
  );
}

// Why an answer was right or wrong -- only what the server's grading shows
// (the `check` of /practice/sessions/{id}/answer): the kind of mistake, the
// word that was typed or picked instead, and the tones written vs needed.
export function CheckExplain({ check, card }) {
  const { t } = useTranslation();
  if (!check || !check.kind || check.kind === "exact") return null;
  if (check.kind === "picked_grammar") {
    // Two grammar points: the one chosen and the one the sentence uses,
    // each a link to its own explanation.
    if (!check.other) return null;
    const plain = { interpolation: { escapeValue: false } };
    return (
      <div className="practice-why" aria-live="polite">
        <p>{t("practice.why.picked_grammar", { meaning: check.other.meaning, ...plain })}</p>
        <div className="row" style={{ flexWrap: "wrap", gap: 8, marginTop: 8 }}>
          <Link to={`/grammar/${check.target_id}`} className="btn small">
            {t("practice.why.openPoint", { title: card?.meaning || "", ...plain })}
          </Link>
          <Link to={`/grammar/${check.other_id}`} className="btn small ghost">
            {t("practice.why.openPoint", { title: check.other.meaning, ...plain })}
          </Link>
        </div>
      </div>
    );
  }
  const other = check.other;
  const vars = {
    word: other?.hanzi || "",
    pinyin: other?.pinyin || "",
    meaning: other?.meaning || "",
    typed: check.tones_typed || "",
    expected: check.tones_expected || "",
    interpolation: { escapeValue: false },
  };
  const needsOther = ["alternative", "other_word", "picked"].includes(check.kind);
  if (needsOther && !other) return null;
  return (
    <div className="practice-why" aria-live="polite">
      {check.typed && <p className="sub" lang="zh-CN">{t("practice.recall.youTyped", { text: check.typed, interpolation: { escapeValue: false } })}</p>}
      <p>{t(`practice.why.${check.kind}`, vars)}</p>
    </div>
  );
}
