import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { canSpeakChinese, speakChinese } from "../zhSpeech.js";
import Icon from "./Icon.jsx";

// Detective Mode and Chinese Sound World pieces for Practice.jsx. What is
// shown -- the clue texts, the voices, the answers -- is what the server
// rendered for the stored round (services/detective.py, sound_world.py);
// nothing here grades or decides progress.

// The question being asked, in the learner's language, with the real words
// (already localized by the server) filled in.
export function askText(t, question) {
  const ask = question.prompt?.ask || {};
  if (question.type === "case_clue") {
    // No "who": the clue is the owner's own account ("I went to ...").
    const kind = ask.who ? ask.kind : `${ask.kind}_me`;
    return t(`detective.ask.${kind}`, { who: ask.who, time: ask.time, place: ask.place });
  }
  if (question.type === "case_deduce") return t("detective.ask.deduce");
  const sub = question.type === "sound_info" ? `${question.type}.${ask.info}` :
    question.type === "sound_conversation" ? `${question.type}.${ask.ask}` : question.type;
  return t(`soundWorld.ask.${sub}`, {
    item: ask.item,
    order: ask.order,
    speaker: ask.speaker ? t(`soundWorld.speaker.${ask.speaker}`, { defaultValue: ask.speaker }) : "",
  });
}

// Word-by-word reading of a clue / line (curriculum words with pinyin and
// localized meaning) -- the "explain the Chinese" part after an answer.
export function GlossList({ gloss }) {
  const { t } = useTranslation();
  if (!gloss?.length) return null;
  return (
    <div className="gloss" aria-label={t("detective.gloss")}>
      <p className="side-title">{t("detective.gloss")}</p>
      <div className="gloss-row">
        {gloss.map((g, i) => (
          <span key={i} className="gloss-chip">
            <b lang="zh-CN">{g.text}</b>
            {g.pinyin && <span className="sub">{g.pinyin}</span>}
            {g.meaning && <span className="gloss-meaning">{g.meaning}</span>}
          </span>
        ))}
      </div>
    </div>
  );
}

// The case so far: what happened, and every clue already examined.
export function CaseFile({ context, questions, upTo }) {
  const { t } = useTranslation();
  if (!context) return null;
  const found = questions.filter((q) => q.index < upTo && q.type === "case_clue" && q.answer);
  return (
    <div className="card case-file">
      <p className="side-title">{t("detective.caseFile")}</p>
      <div className="case-title" lang="zh-CN">{context.title?.zh}</div>
      <div className="sub">{context.title?.py}</div>
      <p className="case-intro">
        <span lang="zh-CN">{context.intro?.zh}</span>
        <button type="button" className="btn small ghost" onClick={() => speakChinese(context.intro?.zh)}
                aria-label={t("companionReact.hear")} title={t("companionReact.hear")}>
          <Icon name="ear" size={13} style={{ verticalAlign: -2 }} />
        </button>
      </p>
      {context.tier !== "advanced" && <div className="sub">{context.intro?.py}</div>}
      {found.length > 0 && (
        <ol className="case-clues">
          {found.map((q) => (
            <li key={q.index} className={q.answer.correct ? "" : "is-missed"}>
              <span lang="zh-CN">{q.prompt.text}</span>
              {q.prompt.mode === "listen" && <span className="badge" style={{ marginLeft: 6 }}>{t("detective.heard")}</span>}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

// One clue: read it, or hear it first (text arrives after answering).
export function CaseClue({ question }) {
  const { t } = useTranslation();
  const p = question.prompt;
  const hidden = !p.text;
  const noVoice = hidden && !canSpeakChinese();
  return (
    <div className="case-clue">
      <span className={`badge ${p.mode === "listen" ? "accent" : ""}`}>
        <Icon name={p.mode === "listen" ? "ear" : "eye"} size={12} /> {t(`detective.mode.${p.mode}`)}
      </span>
      {hidden && !noVoice ? (
        <div className="row" style={{ gap: 8, marginTop: 8 }}>
          <button type="button" className="btn small" onClick={() => speakChinese(p.speak)}>
            <Icon name="ear" size={14} style={{ verticalAlign: -2, marginRight: 6 }} /> {t("detective.playClue")}
          </button>
          <span className="sub">{t("detective.listenFirst")}</span>
        </div>
      ) : (
        <div className="case-clue-text">
          <span lang="zh-CN">{p.text || p.fallback}</span>
          <button type="button" className="btn small ghost" onClick={() => speakChinese(p.speak)}
                  aria-label={t("companionReact.hear")} title={t("companionReact.hear")}>
            <Icon name="ear" size={13} style={{ verticalAlign: -2 }} />
          </button>
          {(p.pinyin || noVoice) && <div className="sub">{p.pinyin || p.fallback}</div>}
          {noVoice && <p className="sub">{t("practice.noChineseVoice")}</p>}
        </div>
      )}
    </div>
  );
}

// Speak a list of lines one after another, each with its own voice.
function playLines(lines, from = 0, onLine) {
  if (from >= lines.length) {
    onLine?.(-1);
    return;
  }
  const l = lines[from];
  onLine?.(from);
  speakChinese(l.speak, {
    profile: { rate: l.rate, pitch: l.pitch, volume: 1 },
    onEnd: () => setTimeout(() => playLines(lines, from + 1, onLine), 350),
  });
}

export function SoundStage({ question, autoPlay }) {
  const { t } = useTranslation();
  const lines = question.prompt.lines || [];
  const [speaking, setSpeaking] = useState(-1);
  const noVoice = !canSpeakChinese();
  const answered = !!lines[0]?.text;

  useEffect(() => {
    if (autoPlay && !answered && !noVoice) playLines(lines, 0, setSpeaking);
    return () => window.speechSynthesis?.cancel();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [question.index]);

  return (
    <div className="sound-stage">
      <div className="row spread" style={{ margin: 0, flexWrap: "wrap", gap: 8 }}>
        <button type="button" className="btn small" onClick={() => playLines(lines, 0, setSpeaking)}>
          <Icon name="play" size={13} /> {lines.length > 1 ? t("soundWorld.playAll") : t("practice.playAgain")}
        </button>
        {noVoice && <span className="sub">{t("practice.noChineseVoice")}</span>}
      </div>
      <ul className="sound-lines">
        {lines.map((l, i) => (
          <li key={i} className={`sound-line${speaking === i ? " is-speaking" : ""}`}>
            <span className="sound-speaker">
              <span lang="zh-CN">{l.speaker_zh}</span>
              {l.speaker !== "npc" && <span className="sub"> · {t(`soundWorld.speaker.${l.speaker}`, { defaultValue: "" })}</span>}
            </span>
            <div className="sound-line-body">
              {l.text ? (
                <>
                  <span lang="zh-CN">{l.text}</span>
                  <div className="sub">{l.pinyin}</div>
                </>
              ) : noVoice ? (
                <span className="sub">{l.fallback}</span>
              ) : (
                <span className="sound-wave" aria-hidden="true">
                  <span /><span /><span /><span /><span />
                </span>
              )}
            </div>
            <button type="button" className="icon-btn" onClick={() => playLines([l], 0, (x) => setSpeaking(x === 0 ? i : -1))}
                    aria-label={t("soundWorld.replayLine", { n: i + 1 })} title={t("soundWorld.replayLine", { n: i + 1 })}>
              <Icon name="ear" size={15} />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

// A soft background bed for the place (filtered noise, generated in the
// browser -- no audio files). Off until the learner turns it on.
const AMBIENT = {
  night_market: 1100, restaurant: 850, train_station: 600, school: 950, street: 450, airport: 700, shopping: 1000,
};

export function AmbientToggle({ env }) {
  const { t } = useTranslation();
  const [on, setOn] = useState(false);
  const ref = useRef(null);

  useEffect(() => () => ref.current?.ctx.close(), []);

  function toggle() {
    if (on) {
      ref.current?.ctx.close();
      ref.current = null;
      setOn(false);
      return;
    }
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();
    const buffer = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    let last = 0;
    for (let i = 0; i < data.length; i++) {
      // Brown noise: a murmur rather than hiss.
      last = (last + 0.02 * (Math.random() * 2 - 1)) / 1.02;
      data[i] = last * 3.5;
    }
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.loop = true;
    const filter = ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = AMBIENT[env] || 800;
    const gain = ctx.createGain();
    gain.gain.value = 0.18;
    src.connect(filter).connect(gain).connect(ctx.destination);
    src.start();
    ref.current = { ctx };
    setOn(true);
  }

  return (
    <button type="button" className={`btn small ${on ? "primary" : "ghost"}`} onClick={toggle} aria-pressed={on}>
      <Icon name={on ? "stop" : "play"} size={13} /> {t(on ? "soundWorld.ambientOff" : "soundWorld.ambientOn")}
    </button>
  );
}
