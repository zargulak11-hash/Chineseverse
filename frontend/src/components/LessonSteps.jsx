import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { canSpeakChinese, speakChinese } from "../zhSpeech.js";
import Icon from "./Icon.jsx";

// The questions of a lesson's guided steps (backend services/lesson_flow.py,
// practice source "lesson_step"): what each one asks, the "build the phrase"
// question, and why an answer was wrong. Grading is the server's: the page
// sends the option id, or for a build the ids of the pieces in order.

export const PHRASE_TYPES = ["phrase_listen", "phrase_gap", "phrase_build", "phrase_meaning", "phrase_situation", "phrase_reply"];

export function phraseAsk(t, question) {
  const p = question.prompt || {};
  if (question.type === "phrase_build") return t(p.final ? "lessonFlow.ask.buildFinal" : "lessonFlow.ask.build");
  if (question.type === "phrase_listen") return t(p.by === "meaning" ? "lessonFlow.ask.listenMeaning" : "lessonFlow.ask.listenPhrase");
  return t(`lessonFlow.ask.${question.type.replace("phrase_", "")}`);
}

// Options written in Chinese (everything but "what did you hear -> its meaning").
export function phraseOptionsInChinese(question) {
  return question.type !== "phrase_listen" || question.prompt?.by !== "meaning";
}

function Hear({ text, label }) {
  const { t } = useTranslation();
  if (!text) return null;
  return (
    <button type="button" className="btn small" onClick={() => speakChinese(text)}>
      <Icon name="volume" size={14} /> {label || t("lessonFlow.hear")}
    </button>
  );
}

// The prompt of a phrase question (not the options).
export function PhrasePrompt({ question, answered }) {
  const { t } = useTranslation();
  const p = question.prompt || {};
  const qtype = question.type;
  useEffect(() => {
    // Heard first: the phrase plays when the question appears.
    if (qtype === "phrase_listen" && p.speak && !answered && canSpeakChinese()) speakChinese(p.speak);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [question.index]);

  if (qtype === "phrase_listen") {
    return (
      <div className="lf-prompt">
        <Hear text={p.speak} label={t("practice.playAgain")} />
        {!canSpeakChinese() && p.pinyin && (
          <div className="practice-no-voice">
            <div className="practice-text">{p.pinyin}</div>
            <p className="sub">{t("practice.noChineseVoice")}</p>
          </div>
        )}
      </div>
    );
  }
  if (qtype === "phrase_gap") {
    return (
      <div className="lf-prompt">
        <div className="practice-text" lang="zh-CN">{p.text}</div>
        {p.gloss && <p className="sub">{t("lessonFlow.means", { text: p.gloss, interpolation: { escapeValue: false } })}</p>}
        {p.hint && <p className="sub">{t("lessonFlow.gapHint", { text: p.hint, interpolation: { escapeValue: false } })}</p>}
      </div>
    );
  }
  if (qtype === "phrase_reply") {
    return (
      <div className="lf-prompt">
        <p className="side-title">{t("lessonFlow.someoneSays")}</p>
        <div className="practice-text" lang="zh-CN">{p.text}</div>
        {p.pinyin && <div className="sub">{p.pinyin}</div>}
        <Hear text={p.speak} />
      </div>
    );
  }
  if (qtype === "phrase_meaning" || qtype === "phrase_situation") {
    return (
      <div className="lf-prompt">
        <div className="practice-text lf-gloss">«{p.gloss}»</div>
      </div>
    );
  }
  return null;
}

// A teaching screen of a played lesson (services/lesson_flow.build_play):
// one new phrase or word -- heard as it appears, with its pinyin, meaning
// and words -- then Continue. Nothing is graded here.
export function TeachCard({ question, busy, onContinue }) {
  const { t } = useTranslation();
  const p = question.prompt || {};
  useEffect(() => {
    if (p.speak && canSpeakChinese()) speakChinese(p.speak);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [question.index]);
  return (
    <div className="lf-teach">
      <span className="badge accent">{t(p.teach === "word" ? "lessonPlay.newWord" : "lessonPlay.newPhrase")}</span>
      <button type="button" className="lf-phrase-main" onClick={() => speakChinese(p.speak)}
              aria-label={`${t("lessonFlow.hear")}: ${p.zh}`}>
        <span className="lf-phrase-zh" lang="zh-CN">{p.zh}</span>
        {p.pinyin && <span className="lf-phrase-py">{p.pinyin}</span>}
        <span className="lf-phrase-say" aria-hidden="true"><Icon name="volume" size={18} /></span>
      </button>
      {p.meaning ? <p className="lf-phrase-mean">«{p.meaning}»</p> : p.teach === "phrase" && (
        <p className="sub">{t("lessonFlow.noTranslation")}</p>
      )}
      {p.template && <p className="sub">{t("lessonFlow.template")}</p>}
      {p.pattern && <p className="sub">{t("lessonFlow.pattern")}: <span lang="zh-CN" className="ld-pattern">{p.pattern}</span></p>}
      {!canSpeakChinese() && <p className="sub">{t("foundation.noVoice")}</p>}
      {p.words?.length > 1 && (
        <ul className="lf-words" aria-label={t("lessonFlow.wordByWord")}>
          {p.words.map((w, k) => (
            <li key={k}>
              <button type="button" className="lf-word" onClick={() => speakChinese(w.text)}
                      aria-label={`${t("lessonFlow.hear")}: ${w.text}`}>
                <b lang="zh-CN">{w.text}</b>
                {w.pinyin && <span className="lf-word-py">{w.pinyin}</span>}
                {w.meaning && <span className="sub">{w.meaning}</span>}
              </button>
            </li>
          ))}
        </ul>
      )}
      {p.example?.zh && (
        <p className="sub">
          {t("lessonPlay.example")}:{" "}
          <button type="button" className="ld-zh-run" lang="zh-CN" onClick={() => speakChinese(p.example.zh)}>{p.example.zh}</button>
          {p.example.py && <> · {p.example.py}</>}
        </p>
      )}
      {p.reply && (
        <div className="lf-reply">
          <p className="side-title">{t("lessonFlow.replyTitle")}</p>
          <button type="button" className="ld-zh-run" lang="zh-CN" onClick={() => speakChinese(p.reply)}>{p.reply}</button>
        </div>
      )}
      <button type="button" className="btn primary lf-continue" disabled={busy} onClick={onContinue} autoFocus>
        {t("lessonPlay.gotIt")} <Icon name="arrowRight" size={15} />
      </button>
    </div>
  );
}

// "Build the phrase": tap the pieces in order (tap a placed piece to take it
// back). The pieces come shuffled from the server, with as much help as the
// learner's level gets (pinyin, the words' meanings) -- the final task none.
export function PhraseBuild({ question, busy, result, onSubmit }) {
  const { t } = useTranslation();
  const p = question.prompt || {};
  const pieces = p.pieces || [];
  const [placed, setPlaced] = useState([]);
  useEffect(() => setPlaced([]), [question.index]);
  const answered = !!result;
  const order = answered && result.order ? result.order : placed;
  const left = pieces.filter((x) => !order.includes(x.id));

  function put(id) {
    if (!answered) setPlaced((o) => [...o, id]);
  }
  function takeBack(id) {
    if (!answered) setPlaced((o) => o.filter((x) => x !== id));
  }

  return (
    <div className="lf-build">
      {p.gloss && <div className="practice-text lf-gloss">«{p.gloss}»</div>}
      {!p.gloss && p.words?.length > 0 && (
        <p className="sub">{t("lessonFlow.wordsMean", { list: p.words.join(" · "), interpolation: { escapeValue: false } })}</p>
      )}
      {p.pattern && <p className="sub">{t("lessonFlow.pattern")}: <span lang="zh-CN" className="ld-pattern">{p.pattern}</span></p>}
      <div className={`lf-line${answered ? (result.correct ? " is-right" : " is-wrong") : ""}`} aria-live="polite"
           aria-label={t("lessonFlow.yourSentence")}>
        {order.length === 0 && <span className="sub">{t("lessonFlow.tapPieces")}</span>}
        {order.map((id) => {
          const x = pieces.find((y) => y.id === id);
          return (
            <button key={id} type="button" className="lf-piece is-placed" disabled={answered || busy} onClick={() => takeBack(id)}
                    aria-label={t("lessonFlow.takeBack", { text: x?.zh })}>
              <span lang="zh-CN">{x?.zh}</span>
            </button>
          );
        })}
      </div>
      {!answered && (
        <div className="lf-pieces" role="group" aria-label={t("lessonFlow.pieces")}>
          {left.map((x) => (
            <button key={x.id} type="button" className="lf-piece" disabled={busy} onClick={() => put(x.id)}>
              <span lang="zh-CN">{x.zh}</span>
              {x.py && <small className="lf-piece-py">{x.py}</small>}
              {x.meaning && <small className="lf-piece-mean">{x.meaning}</small>}
            </button>
          ))}
        </div>
      )}
      {!answered && (
        <div className="row" style={{ gap: 8, flexWrap: "wrap", margin: 0 }}>
          <button type="button" className="btn primary" disabled={busy || placed.length !== pieces.length}
                  onClick={() => onSubmit(placed)}>
            {t("lessonFlow.check")}
          </button>
          <button type="button" className="btn ghost" disabled={busy || placed.length === 0} onClick={() => setPlaced([])}>
            {t("lessonFlow.clear")}
          </button>
        </div>
      )}
    </div>
  );
}

// Why a phrase answer was wrong -- worded from the server's check, which
// only says what the stored question and answer show.
export function PhraseWhy({ check }) {
  const { t } = useTranslation();
  if (!check) return null;
  const plain = { interpolation: { escapeValue: false } };
  const lines = [];
  if (check.kind === "order") {
    if (check.correct) return null;
    lines.push(t("lessonFlow.why.order", { given: check.given, expected: check.expected, ...plain }));
    if (check.rule) lines.push(t(`lessonFlow.rule.${check.rule}`, { word: check.word, ...plain }));
    else if (check.pattern) lines.push(t("lessonFlow.why.pattern", { pattern: check.pattern, ...plain }));
    else lines.push(t("lessonFlow.why.orderGeneral"));
  } else if (check.kind === "gap") {
    lines.push(t("lessonFlow.why.gap", {
      picked: check.picked, pickedMeaning: check.picked_meaning, answer: check.answer, answerMeaning: check.answer_meaning, ...plain,
    }));
  } else if (check.kind === "heard") {
    lines.push(check.answer_pinyin
      ? t("lessonFlow.why.heard", { picked: check.picked, answer: check.answer, pinyin: check.answer_pinyin, ...plain })
      : t("lessonFlow.why.heardNoPy", { picked: check.picked, answer: check.answer, ...plain }));
  } else if (check.kind === "reply") {
    lines.push(t("lessonFlow.why.reply", { asked: check.asked, answer: check.answer, ...plain }));
    if (check.picked_meaning) lines.push(t("lessonFlow.why.pickedMeans", { picked: check.picked, meaning: check.picked_meaning, ...plain }));
  } else if (check.kind === "means") {
    lines.push(check.picked_meaning
      ? t("lessonFlow.why.pickedMeans", { picked: check.picked, meaning: check.picked_meaning, ...plain })
      : t("lessonFlow.why.notThis", { picked: check.picked, ...plain }));
    lines.push(t("lessonFlow.why.say", { answer: check.answer, ...plain }));
  } else {
    return null;
  }
  return (
    <div className="practice-why" aria-live="polite">
      {lines.map((l, i) => <p key={i}>{l}</p>)}
    </div>
  );
}
