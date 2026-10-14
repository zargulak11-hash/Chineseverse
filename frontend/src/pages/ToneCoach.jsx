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
  const targets = result.syllables
    .map((s, i) => ({ s, i }))
    .filter(({ s }) => s.judged && s.span)
    .map(({ s, i }) => {
      const last = i === result.syllables.length - 1;
      const shape = s.expected === 3 && !last ? SHAPES.half3 : SHAPES[s.expected];
      const [a, b] = s.span;
      const pts = shape.map((v, k) => `${x(a + ((b - a) * k) / (shape.length - 1)).toFixed(1)},${y(v).toFixed(1)}`);
      return <polyline key={i} points={pts.join(" ")} className="tc-target" />;
    });
  return (
    <figure className="tc-chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t("toneCoach.chartLabel")} preserveAspectRatio="none">
        <line x1="0" x2={W} y1={H / 2} y2={H / 2} className="tc-axis" />
        {targets}
        {paths.map((p, i) => <path key={i} d={p} className="tc-voice" />)}
      </svg>
      <figcaption className="sub">{t("toneCoach.chartLabel")}</figcaption>
    </figure>
  );
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
  const { data: stats, reload: reloadStats } = useApi("/tones/stats");

  const load = useCallback(() => {
    setItem(null);
    setItemError("");
    setResult(null);
    setRecError("");
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
      const rec = await recordAndAnalyse(item.zh.length > 1 ? 2600 : 1800);
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

  const tones = item ? item.expected.filter((x) => x !== 5) : [];
  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="mic" size={13} /> {t("practice.toneRound")}</div>
          <h1 className="h1">{t("toneCoach.title")}</h1>
          <p className="sub">{t("toneCoach.subtitle")}</p>
        </div>
      </header>

      <div className="ws">
        <div className="ws-main">
          <div className="row" style={{ flexWrap: "wrap", gap: 8 }} role="group" aria-label={t("toneCoach.modeLabel")}>
            {["single", "pair"].map((m) => (
              <button key={m} type="button" className={`btn small${mode === m ? " primary" : " ghost"}`}
                      aria-pressed={mode === m} onClick={() => setMode(m)}>
                {t(m === "single" ? "toneCoach.modeSingle" : "toneCoach.modePair")}
              </button>
            ))}
          </div>

          {!recordingSupported && <div className="card" style={{ marginTop: 16 }}><Empty>{t("toneCoach.unsupported")}</Empty></div>}
          {itemError && <div className="card" style={{ marginTop: 16 }}><Empty>{itemError}</Empty></div>}
          {!item && !itemError && <div className="card" style={{ marginTop: 16 }}><Loading /></div>}

          {item && (
            <section className="card tc-card" style={{ marginTop: 16 }} aria-labelledby="tc-word">
              {item.focus && <span className="badge accent">{t("toneCoach.focus", { tone: item.focus })}</span>}
              <div className="tc-word" id="tc-word" lang="zh-CN">{item.zh}</div>
              <div className="tc-pinyin">{item.pinyin}</div>
              {item.meaning && <p className="sub">{item.meaning}</p>}
              <p className="sub tc-expected">
                {t("toneCoach.expected")}: <b>{tones.join(" · ")}</b>
                {item.sandhi && <span className="tc-sandhi"> — {t("toneCoach.sandhi", { tones: item.expected.filter((x) => x !== 5).join("-") })}</span>}
              </p>
              <p className="sub">{t("toneCoach.how")}</p>
              <div className="row" style={{ flexWrap: "wrap", gap: 8, marginTop: 12 }}>
                <button type="button" className="btn" onClick={() => speakChinese(item.zh)}>
                  <Icon name="ear" size={15} /> {t("toneCoach.listen")}
                </button>
                <button type="button" className="btn primary tc-record" onClick={record}
                        disabled={!recordingSupported || phase !== "idle"} aria-live="polite">
                  <Icon name={phase === "recording" ? "stop" : "mic"} size={15} />{" "}
                  {phase === "recording" ? t("toneCoach.recording") : phase === "analysing" ? t("toneCoach.analysing") : t("toneCoach.record")}
                </button>
                {mine && (
                  <button type="button" className="btn ghost" onClick={() => new Audio(mine).play()}>
                    <Icon name="ear" size={15} /> {t("toneCoach.playMine")}
                  </button>
                )}
              </div>
              {recError && <p className="formerr" role="alert">{recError}</p>}

              {result && (
                <div className="tc-result" aria-live="polite">
                  <span className={`badge ${result.verdict === "correct" ? "good" : result.verdict === "wrong" ? "bad" : ""}`}>
                    {t(`toneCoach.verdict_${result.verdict}`)}
                  </span>
                  <ul className="tc-syllables">
                    {result.syllables.map((s, i) => (
                      <li key={i} className={s.judged ? (s.heard === s.expected ? "is-ok" : "is-off") : ""}>
                        <b lang="zh-CN">{item.zh[i]}</b>{" "}
                        {s.judged
                          ? t("toneCoach.syllableLine", { expected: toneLabel(t, s.expected), heard: toneLabel(t, s.heard) })
                          : t("toneCoach.notJudged")}
                      </li>
                    ))}
                  </ul>
                  {result.verdict !== "silent" && <ToneChart result={result} />}
                  {result.xp_gained > 0 && <span className="badge good">+{result.xp_gained} XP</span>}
                </div>
              )}
              <div className="row" style={{ marginTop: 16 }}>
                <button type="button" className={`btn${result ? " primary" : ""}`} onClick={load} disabled={phase !== "idle"}>
                  {t("toneCoach.next")} <Icon name="arrowRight" size={14} />
                </button>
              </div>
            </section>
          )}
          <p className="sub tc-note"><Icon name="lock" size={12} /> {t("toneCoach.privacy")}</p>
          <p className="sub tc-note">{t("toneCoach.honest")}</p>
        </div>

        <aside className="ws-side">
          <div className="card side-card">
            <p className="side-title">{t("toneCoach.statsTitle", { days: stats?.days ?? 30 })}</p>
            {!stats ? <Loading /> : stats.tones.every((x) => x.judged === 0) ? (
              <p className="sub">{t("toneCoach.statsNone")}</p>
            ) : (
              <ul className="tc-stats">
                {stats.tones.map((x) => (
                  <li key={x.tone}>
                    <div className="row spread" style={{ margin: 0 }}>
                      <span>{t(`toneCoach.tone${x.tone}`)}</span>
                      <span className="sub">{x.judged ? t("toneCoach.statsTone", { correct: x.correct, judged: x.judged }) : "—"}</span>
                    </div>
                    {x.judged > 0 && <Bar value={x.correct} max={x.judged} />}
                  </li>
                ))}
              </ul>
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
