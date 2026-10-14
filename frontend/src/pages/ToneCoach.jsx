import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { useApi } from "../hooks/useApi.js";
import { recordAndAnalyse, recordingSupported } from "../pitch.js";
import { speakChinese } from "../zhSpeech.js";

// Tone Coach (backend services/tone_coach.py). The learner hears the word,
// says it, and sees their own pitch curve over the shape each tone should
// have. The browser only measures pitch (pitch.js) -- the tone verdict, the
// statistics and what to practise next all come from the server.

// The shape each tone traces, in semitones around the speaker's own middle
// (the same shapes the server's classifier looks for). A 3rd tone that is
// not last is a low "half third".
const SHAPES = { 1: [2, 2, 2], 2: [-1, 0.5, 3], 3: [-1, -4, 0], 4: [3, 0, -4], half3: [-3, -4, -4.5] };
const Y_RANGE = 8;

// How long the microphone listens (pitch.js stops by itself after this):
// the record button draws the same time as a ring, so "how long do I talk"
// is visible rather than guessed.
const recordMs = (zh) => (zh.length > 1 ? 2600 : 1800);

function shapeOf(tone, last) {
  return tone === 3 && !last ? SHAPES.half3 : SHAPES[tone];
}

// A small drawing of the contour one syllable should follow -- the same
// numbers as the chart's dashed target, so the glyph above the word and the
// line in the result are the same shape. The neutral tone is a short dot.
function ToneGlyph({ tone, last, state = "" }) {
  const W = 44;
  const H = 32;
  const shape = shapeOf(tone, last);
  const y = (st) => H / 2 - (st / 4.5) * (H / 2 - 3);
  return (
    <svg className={`tc-glyph ${state}`} width={W} height={H} viewBox={`0 0 ${W} ${H}`} aria-hidden="true">
      {shape
        ? <polyline points={shape.map((v, k) => `${4 + (k * (W - 8)) / (shape.length - 1)},${y(v).toFixed(1)}`).join(" ")} />
        : <circle cx={W / 2} cy={H / 2 + 4} r="3" />}
    </svg>
  );
}

function ToneChart({ result }) {
  const { t } = useTranslation();
  const W = 600;
  const H = 180;
  const curve = result.curve || [];
  const n = Math.max(curve.length, 2);
  const x = (i) => (i / (n - 1)) * W;
  const y = (st) => H / 2 - (Math.max(-Y_RANGE, Math.min(Y_RANGE, st)) / Y_RANGE) * (H / 2 - 8);
  // The learner's curve, broken where no pitch was heard.
  const paths = [];
  let d = "";
  curve.forEach((v, i) => {
    if (v === null || v === undefined) {
      if (d) paths.push(d);
      d = "";
    } else d += `${d ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
  });
  if (d) paths.push(d);
  const judged = result.syllables.map((s, i) => ({ s, i })).filter(({ s }) => s.judged && s.span);
  const targets = judged.map(({ s, i }) => {
    const shape = shapeOf(s.expected, i === result.syllables.length - 1);
    const [a, b] = s.span;
    const pts = shape.map((v, k) => `${x(a + ((b - a) * k) / (shape.length - 1)).toFixed(1)},${y(v).toFixed(1)}`);
    return <polyline key={i} points={pts.join(" ")} className="tc-target" />;
  });
  // Each judged syllable's stretch of the recording, shaded: where in the
  // curve the server looked for that syllable's tone.
  const bands = judged.map(({ s, i }) => (
    <rect key={`b${i}`} x={x(s.span[0])} y="0" width={Math.max(2, x(s.span[1]) - x(s.span[0]))} height={H}
          className={`tc-band ${sylState(s)}`} />
  ));
  return (
    <figure className="tc-chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t("toneCoach.chartLabel")} preserveAspectRatio="none">
        {bands}
        <line x1="0" x2={W} y1={H / 2} y2={H / 2} className="tc-axis" />
        {targets}
        {paths.map((p, i) => <path key={i} d={p} className="tc-voice" />)}
      </svg>
      <figcaption className="tc-legend">
        <span><i className="tc-key is-target" aria-hidden="true" /> {t("toneCoach.legendTarget")}</span>
        <span><i className="tc-key is-voice" aria-hidden="true" /> {t("toneCoach.legendVoice")}</span>
      </figcaption>
    </figure>
  );
}

// A judged syllable is right, wrong, or -- when no clear pitch was heard --
// unclear, which is not a wrong tone and is not painted as one.
function sylState(s) {
  if (!s?.judged) return "";
  if (!s.heard) return "is-unclear";
  return s.heard === s.expected ? "is-ok" : "is-off";
}

function toneLabel(t, tone) {
  return tone ? t(`toneCoach.tone${tone}`) : t("toneCoach.heardUnclear");
}

export default function ToneCoach() {
  const { t, i18n } = useTranslation();
  const { refresh } = useDashboard();
  const [mode, setMode] = useState("pair");
  const [item, setItem] = useState(null);
  const [itemError, setItemError] = useState("");
  const [phase, setPhase] = useState("idle"); // idle | recording | analysing
  const [result, setResult] = useState(null);
  const [mine, setMine] = useState(null);
  const [recError, setRecError] = useState("");
  const [heardModel, setHeardModel] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const { data: stats, reload: reloadStats } = useApi("/tones/stats");

  const load = useCallback(() => {
    setItem(null);
    setItemError("");
    setResult(null);
    setRecError("");
    setHeardModel(false);
    setMine((url) => {
      if (url) URL.revokeObjectURL(url);
      return null;
    });
    api.get(`/tones/next?mode=${mode}`).then(setItem).catch((e) => setItemError(e.message));
    // i18n.language: the word's meaning is in the learner's language, so a
    // language switch fetches it again.
  }, [mode, i18n.language]);
  useEffect(load, [load]);

  async function record() {
    setRecError("");
    setResult(null);
    setPhase("recording");
    try {
      const rec = await recordAndAnalyse(recordMs(item.zh));
      setPhase("analysing");
      setMine((old) => {
        if (old) URL.revokeObjectURL(old);
        return rec.url;
      });
      const r = await api.post("/tones/attempt", {
        item_type: item.item_type, item_id: item.item_id, f0: rec.f0, rms: rec.rms,
      });
      setResult(r);
      reloadStats();
      if (r.verdict === "correct" || r.verdict === "wrong") refresh?.();
    } catch (e) {
      setRecError(e?.name === "NotAllowedError" ? t("voice.micDenied") : e?.name === "NotFoundError" ? t("voice.micNoDevice") : e.message);
    } finally {
      setPhase("idle");
    }
  }

  function listen() {
    setHeardModel(true);
    speakChinese(item.zh, { onStart: () => setSpeaking(true), onEnd: () => setSpeaking(false) });
  }

  const tones = item ? item.expected.filter((x) => x !== 5) : [];
  const chars = item ? Array.from(item.zh) : [];
  // Per-syllable pinyin only when the API's pinyin splits into exactly one
  // piece per character ("zhè lǐ"); "míngzi" stays whole under the word.
  const pyParts = item ? item.pinyin.trim().split(/\s+/) : [];
  const perSyllable = pyParts.length === chars.length;
  // Where the learner is in listen -> say -> compare: lit by what really happened.
  const step = result ? 3 : phase !== "idle" || heardModel ? 2 : 1;
  const steps = ["toneCoach.stepListen", "toneCoach.stepSay", "toneCoach.stepCompare"];

  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="mic" size={13} /> {t("practice.toneRound")}</div>
          <h1 className="h1">{t("toneCoach.title")}</h1>
          <p className="sub">{t("toneCoach.subtitle")}</p>
        </div>
        <div className="tc-modes" role="group" aria-label={t("toneCoach.modeLabel")}>
          {["single", "pair"].map((m) => (
            <button key={m} type="button" className={`btn small${mode === m ? " primary" : " ghost"}`}
                    aria-pressed={mode === m} onClick={() => setMode(m)}>
              {t(m === "single" ? "toneCoach.modeSingle" : "toneCoach.modePair")}
            </button>
          ))}
        </div>
      </header>

      <div className="ws">
        <div className="ws-main">
          {!recordingSupported && <div className="card"><Empty>{t("toneCoach.unsupported")}</Empty></div>}
          {itemError && <div className="card"><Empty>{itemError}</Empty></div>}
          {!item && !itemError && <div className="card tc-studio"><Loading /></div>}

          {item && (
            <section className="card tc-studio" aria-labelledby="tc-word">
              <ol className="tc-steps" aria-label={t("toneCoach.stepsLabel")}>
                {steps.map((key, i) => (
                  <li key={key} className={step === i + 1 ? "is-now" : step > i + 1 ? "is-done" : ""}
                      aria-current={step === i + 1 ? "step" : undefined}>
                    <span className="tc-step-n">{step > i + 1 ? <Icon name="check" size={12} /> : i + 1}</span>
                    {t(key)}
                  </li>
                ))}
              </ol>

              <div className="tc-stage">
                {item.focus && <span className="badge accent tc-focus">{t("toneCoach.focus", { tone: item.focus })}</span>}
                <div className="tc-word" id="tc-word" lang="zh-CN" aria-label={`${item.zh} ${item.pinyin}`}>
                  {chars.map((ch, i) => {
                    const exp = item.expected[i];
                    const sy = result?.syllables?.[i];
                    const state = sylState(sy);
                    return (
                      <span key={i} className={`tc-syl ${state}`}>
                        <ToneGlyph tone={exp} last={i === chars.length - 1} state={state} />
                        <span className="tc-char" aria-hidden="true">{ch}</span>
                        {perSyllable && <span className="tc-syl-py" aria-hidden="true">{pyParts[i]}</span>}
                      </span>
                    );
                  })}
                </div>
                {!perSyllable && <div className="tc-pinyin">{item.pinyin}</div>}
                {item.meaning && <p className="tc-meaning">{item.meaning}</p>}
                <p className="sub tc-expected">
                  {t("toneCoach.expected")}: <b>{tones.join(" · ")}</b>
                  {item.sandhi && <span className="tc-sandhi"> — {t("toneCoach.sandhi", { tones: item.expected.filter((x) => x !== 5).join("-") })}</span>}
                </p>
              </div>

              <div className="tc-deck">
                <button type="button" className={`tc-side-btn${speaking ? " is-playing" : ""}`} onClick={listen}>
                  <span className="tc-side-icon"><Icon name="volume" size={20} /></span>
                  <span>{t("toneCoach.listen")}</span>
                </button>
                <div className="tc-rec-wrap">
                  <button type="button" className={`tc-rec is-${phase}`} onClick={record}
                          disabled={!recordingSupported || phase !== "idle"} aria-live="polite"
                          style={{ "--rec-ms": `${recordMs(item.zh)}ms` }}>
                    <svg className="tc-rec-ring" viewBox="0 0 100 100" aria-hidden="true">
                      <circle cx="50" cy="50" r="46" />
                    </svg>
                    <Icon name={phase === "recording" ? "stop" : "mic"} size={30} />
                  </button>
                  <span className="tc-rec-label" aria-hidden="true">
                    {phase === "recording" ? t("toneCoach.recording") : phase === "analysing" ? t("toneCoach.analysing") : t("toneCoach.record")}
                  </span>
                </div>
                <button type="button" className="tc-side-btn" onClick={() => mine && new Audio(mine).play()} disabled={!mine}>
                  <span className="tc-side-icon"><Icon name="play" size={18} /></span>
                  <span>{t("toneCoach.playMine")}</span>
                </button>
              </div>
              <p className="sub tc-how">{t("toneCoach.how")}</p>
              {recError && <p className="formerr" role="alert">{recError}</p>}

              {result && (
                <div className={`tc-result is-${result.verdict}`} aria-live="polite">
                  <div className="tc-verdict">
                    <span className={`badge ${result.verdict === "correct" ? "good" : result.verdict === "wrong" ? "bad" : ""}`}>
                      {t(`toneCoach.verdict_${result.verdict}`)}
                    </span>
                    {result.xp_gained > 0 && <span className="badge good">+{result.xp_gained} XP</span>}
                  </div>
                  <ul className="tc-syllables">
                    {result.syllables.map((s, i) => (
                      <li key={i} className={sylState(s)}>
                        <b lang="zh-CN">{chars[i]}</b>
                        <span>
                          {s.judged
                            ? t("toneCoach.syllableLine", { expected: toneLabel(t, s.expected), heard: toneLabel(t, s.heard) })
                            : t("toneCoach.notJudged")}
                        </span>
                      </li>
                    ))}
                  </ul>
                  {result.verdict !== "silent" && <ToneChart result={result} />}
                </div>
              )}
              <div className="tc-next">
                <button type="button" className={`btn${result ? " primary" : " ghost"}`} onClick={load} disabled={phase !== "idle"}>
                  {t("toneCoach.next")} <Icon name="arrowRight" size={14} />
                </button>
              </div>
            </section>
          )}
          <div className="tc-notes">
            <p className="sub tc-note"><Icon name="lock" size={12} /> {t("toneCoach.privacy")}</p>
            <p className="sub tc-note">{t("toneCoach.honest")}</p>
          </div>
        </div>

        <aside className="ws-side">
          <div className="card side-card">
            <p className="side-title">{t("toneCoach.statsTitle", { days: stats?.days ?? 30 })}</p>
            {!stats ? <Loading /> : (
              <>
                <ul className="tc-tiles">
                  {stats.tones.map((x) => (
                    <li key={x.tone} className="tc-tile">
                      <ToneGlyph tone={x.tone} last />
                      <span className="tc-tile-name">{t(`toneCoach.tone${x.tone}`)}</span>
                      <span className="tc-tile-score">{x.judged ? t("toneCoach.statsTone", { correct: x.correct, judged: x.judged }) : "—"}</span>
                      {x.judged > 0 && <Bar value={x.correct} max={x.judged} />}
                    </li>
                  ))}
                </ul>
                {stats.tones.every((x) => x.judged === 0) && <p className="sub" style={{ marginTop: 12 }}>{t("toneCoach.statsNone")}</p>}
              </>
            )}
            {stats?.confusions?.length > 0 && (
              <ul className="tc-confusions">
                {stats.confusions.map((c) => (
                  <li key={`${c.expected}-${c.heard}`} className="sub">
                    {t("toneCoach.confusion", { expected: c.expected, heard: c.heard, count: c.count })}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="card side-card">
            <p className="sub">{t("toneCoach.listenCourseWhy")}</p>
            <Link to="/sound-world" className="btn small" style={{ marginTop: 8 }}>{t("toneCoach.listenCourse")}</Link>
          </div>
        </aside>
      </div>
    </Layout>
  );
}
