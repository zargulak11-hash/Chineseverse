import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { speakChinese } from "../zhSpeech.js";
import { StatusDot } from "./CharacterDNA.jsx";

// Vocabulary Ecosystem (GET /api/vocab/ecosystem): one character, the real
// compounds built from it (within an HSK filter) and the characters those
// compounds lead to -- with the learner's own status on every node. The
// server caps the network at a screenful; the layout below is a fixed
// radial one (no physics), so it never jitters and costs nothing to draw.

const R_WORD = 285;
const R_CHAR = 455;

function layout(nodes, edges) {
  const words = nodes.filter((n) => n.kind === "word");
  const chars = nodes.filter((n) => n.kind === "char" && !n.center);
  const pos = {};
  const center = nodes.find((n) => n.center);
  if (center) pos[center.id] = { x: 0, y: 0, a: 0 };
  words.forEach((w, i) => {
    const a = (i / Math.max(1, words.length)) * Math.PI * 2 - Math.PI / 2;
    pos[w.id] = { x: Math.cos(a) * R_WORD, y: Math.sin(a) * R_WORD, a };
  });
  // Each outer character sits near the words it belongs to: order by the
  // mean angle of its words, then spread evenly around the outer ring.
  const meanAngle = (c) => {
    const as = edges.filter((e) => e.to === c.id).map((e) => pos[e.from]?.a).filter((a) => a !== undefined);
    if (!as.length) return 0;
    const x = as.reduce((s, a) => s + Math.cos(a), 0);
    const y = as.reduce((s, a) => s + Math.sin(a), 0);
    return Math.atan2(y, x);
  };
  const ordered = chars.map((c) => ({ c, a: meanAngle(c) })).sort((p, q) => p.a - q.a);
  ordered.forEach(({ c, a }, i) => {
    const spread = ordered.length > 1 ? (i / ordered.length) * Math.PI * 2 + ordered[0].a : a;
    pos[c.id] = { x: Math.cos(spread) * R_CHAR, y: Math.sin(spread) * R_CHAR, a: spread };
  });
  return pos;
}

export default function Ecosystem() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const center = params.get("center") || "";
  const hskMax = params.get("hsk") || "";
  const query = new URLSearchParams();
  if (center) query.set("center", center);
  if (hskMax) query.set("hsk_max", hskMax);
  const { data, error } = useApi(`/vocab/ecosystem${query.toString() ? `?${query}` : ""}`);
  const [selected, setSelected] = useState(null);
  const [hover, setHover] = useState(null);
  const [input, setInput] = useState("");

  const pos = useMemo(() => (data ? layout(data.nodes, data.edges) : {}), [data]);

  function recenter(c) {
    setSelected(null);
    const next = new URLSearchParams(params);
    next.set("center", c);
    setParams(next);
  }
  function setLevel(l) {
    const next = new URLSearchParams(params);
    next.set("hsk", String(l));
    if (data?.center) next.set("center", data.center);
    setParams(next);
  }

  if (error) {
    return (
      <Layout>
        <Empty>{error}</Empty>
        <Link to="/ecosystem" className="btn ghost" style={{ marginTop: 12 }}>{t("practice.back")}</Link>
      </Layout>
    );
  }
  if (!data) return <Layout><Loading /></Layout>;

  const words = data.nodes.filter((n) => n.kind === "word");
  const sel = selected && data.nodes.find((n) => n.id === selected);
  const near = new Set(
    hover ? data.edges.filter((e) => e.from === hover || e.to === hover).flatMap((e) => [e.from, e.to]) : []
  );

  function activate(n) {
    if (n.kind === "char" && !n.center) recenter(n.text);
    else setSelected(n.id);
  }

  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="world" size={13} /> {t("nav.ecosystem")}</div>
          <h1 className="h1">{t("ecosystem.title")}</h1>
          <p className="sub">{t("ecosystem.subtitle")}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">{data.stats.mastered}/{data.stats.shown}</span>
            <span className="kpi-label">{t("ecosystem.mastered")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{data.stats.due}</span>
            <span className="kpi-label">{t("ecosystem.due")}</span>
          </div>
        </div>
      </header>

      <div className="ws">
        <div className="ws-main">
          <div className="card">
            <form
              className="row"
              style={{ margin: 0, gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}
              onSubmit={(e) => {
                e.preventDefault();
                const c = input.trim().slice(0, 1);
                if (c) recenter(c);
              }}
            >
              <div className="field" style={{ marginBottom: 0, flex: "1 1 160px" }}>
                <label htmlFor="eco-center">{t("ecosystem.centerLabel")}</label>
                <input id="eco-center" className="input" lang="zh-CN" maxLength={1} value={input}
                       placeholder={data.center} onChange={(e) => setInput(e.target.value)} />
              </div>
              <button type="submit" className="btn" disabled={!input.trim()}>{t("ecosystem.explore")}</button>
            </form>
            <p className="side-title" style={{ marginTop: 16 }}>{t("ecosystem.levels")}</p>
            <div className="row" style={{ gap: 8, flexWrap: "wrap", margin: 0 }} role="group" aria-label={t("ecosystem.levels")}>
              {[1, 2, 3, 4, 5, 6, 7].map((l) => (
                <button key={l} type="button" className={`btn small ${data.hsk_max === l ? "primary" : "ghost"}`}
                        aria-pressed={data.hsk_max === l} onClick={() => setLevel(l)}>
                  {l === 7 ? "HSK 7–9" : `≤ HSK ${l}`}
                </button>
              ))}
            </div>
          </div>

          <div className="card eco-card">
            {words.length === 0 ? (
              <Empty>{t("ecosystem.empty", { char: data.center, level: data.hsk_max })}</Empty>
            ) : (
              <svg className="eco-graph" viewBox="-520 -520 1040 1040" role="img"
                   aria-label={t("ecosystem.graphLabel", { char: data.center, count: words.length })}>
                {data.edges.map((e, i) => {
                  const a = pos[e.from];
                  const b = pos[e.to];
                  if (!a || !b) return null;
                  const lit = hover && near.has(e.from) && near.has(e.to);
                  return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} className={`eco-edge${lit ? " is-lit" : ""}`} />;
                })}
                {data.nodes.map((n) => {
                  const p = pos[n.id];
                  if (!p) return null;
                  const r = n.center ? 62 : n.kind === "word" ? 40 : 28;
                  const state = n.due ? "due" : n.status;
                  return (
                    <g
                      key={n.id}
                      className={`eco-node is-${n.kind} is-${state}${n.center ? " is-center" : ""}${selected === n.id ? " is-selected" : ""}${hover && !near.has(n.id) && hover !== n.id ? " is-dim" : ""}`}
                      role="button"
                      tabIndex={0}
                      aria-label={`${n.text} ${n.pinyin || ""} ${n.meaning || ""}`}
                      onClick={() => activate(n)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          activate(n);
                        }
                      }}
                      onMouseEnter={() => setHover(n.id)}
                      onMouseLeave={() => setHover(null)}
                      onFocus={() => setHover(n.id)}
                      onBlur={() => setHover(null)}
                    >
                      <circle cx={p.x} cy={p.y} r={r} />
                      <text x={p.x} y={p.y + (n.kind === "word" ? 8 : 10)} textAnchor="middle" className="eco-label" fontSize={n.center ? 48 : n.text.length >= 4 ? 16 : n.text.length === 3 ? 20 : 26} lang="zh-CN">
                        {n.text}
                      </text>
                      {n.kind === "word" && words.length <= 10 && (
                        <text x={p.x} y={p.y + r + 22} textAnchor="middle" className="eco-sub" fontSize={18}>{n.pinyin}</text>
                      )}
                    </g>
                  );
                })}
              </svg>
            )}
            <p className="sub legend">
              <StatusDot status="mastered" /> {t("charDna.status.mastered")} <StatusDot status="reviewing" /> {t("charDna.status.reviewing")}{" "}
              <StatusDot status="learning" /> {t("charDna.status.learning")} <StatusDot status="new" /> {t("charDna.status.new")}{" "}
              <StatusDot due /> {t("charDna.status.due")}
            </p>
            <p className="sub">{t("ecosystem.hint")}</p>
          </div>

          <h2 className="h2 section-title">{t("ecosystem.listTitle", { char: data.center })}</h2>
          <ul className="eco-list">
            {words.map((w) => (
              <li key={w.id}>
                <button type="button" className={`eco-list-item${selected === w.id ? " is-selected" : ""}`} onClick={() => setSelected(w.id)}>
                  <StatusDot status={w.status} due={w.due} />
                  <b lang="zh-CN">{w.text}</b>
                  <span className="sub">{w.pinyin}</span>
                  <span className="eco-list-meaning">{w.meaning}</span>
                  {w.level && <span className="badge">HSK {w.level}</span>}
                </button>
              </li>
            ))}
          </ul>
          {data.stats.compounds_total > data.stats.shown && (
            <p className="sub">{t("ecosystem.more", { shown: data.stats.shown, total: data.stats.compounds_total })}</p>
          )}
        </div>

        <aside className="ws-side">
          <div className="card side-card">
            {sel && sel.kind === "word" ? (
              <>
                <p className="side-title">{t("ecosystem.word")}</p>
                <div className="row" style={{ margin: 0, gap: 8, alignItems: "center" }}>
                  <span className="sentence-text" lang="zh-CN">{sel.text}</span>
                  <button type="button" className="btn small ghost" onClick={() => speakChinese(sel.text)}
                          aria-label={t("companionReact.hear")} title={t("companionReact.hear")}>
                    <Icon name="ear" size={14} />
                  </button>
                </div>
                <div className="sub">{sel.pinyin}</div>
                <p>{sel.meaning}</p>
                <div className="row" style={{ gap: 6, flexWrap: "wrap", margin: "8px 0 0" }}>
                  {sel.level && <span className="badge">HSK {sel.level}</span>}
                  <span className={`badge ${sel.status === "mastered" ? "good" : sel.due ? "accent" : ""}`}>
                    {t(`charDna.status.${sel.due ? "due" : sel.status}`)}
                  </span>
                </div>
                {sel.example && (
                  <div style={{ marginTop: 12 }}>
                    <p className="side-title">{t("charDna.examples")}</p>
                    <span lang="zh-CN">{sel.example}</span>
                    {sel.example_pinyin && <div className="sub">{sel.example_pinyin}</div>}
                  </div>
                )}
                <p className="side-title" style={{ marginTop: 12 }}>{t("ecosystem.itsCharacters")}</p>
                <div className="chip-row">
                  {[...new Set(sel.text)].map((c) => (
                    <Link key={c} to={`/hanzi/${encodeURIComponent(c)}`} className="char-chip"><b lang="zh-CN">{c}</b></Link>
                  ))}
                </div>
                {sel.example && (
                  <Link to={`/sentence?text=${encodeURIComponent(sel.example)}`} className="btn small" style={{ marginTop: 12 }}>
                    <Icon name="sparkles" size={13} /> {t("charDna.makeLesson")}
                  </Link>
                )}
              </>
            ) : (
              <>
                <p className="side-title">{t("ecosystem.centre")}</p>
                <div className="row" style={{ margin: 0, gap: 12, alignItems: "center" }}>
                  <span className="sentence-text" lang="zh-CN">{data.center}</span>
                  <div className="sub">{data.nodes[0]?.pinyin}<br />{data.nodes[0]?.meaning}</div>
                </div>
                <p className="sub" style={{ marginTop: 8 }}>
                  {t("ecosystem.statsLine", { total: data.stats.compounds_total, level: data.hsk_max === 7 ? "7–9" : data.hsk_max })}
                </p>
                {data.nodes[0]?.has_dna && (
                  <Link to={`/hanzi/${encodeURIComponent(data.center)}`} className="btn small" style={{ marginTop: 8 }}>
                    <Icon name="dna" size={13} /> {t("ecosystem.openDna")}
                  </Link>
                )}
              </>
            )}
          </div>
          {data.suggested.length > 0 && (
            <div className="card side-card">
              <p className="side-title">{t("ecosystem.nextToLearn")}</p>
              <ul className="scene-rules">
                {data.suggested.map((w) => (
                  <li key={w.id}><b lang="zh-CN">{w.text}</b> <span className="sub">{w.pinyin}</span> — {w.meaning}</li>
                ))}
              </ul>
              <button type="button" className="btn small" style={{ marginTop: 8 }}
                      onClick={() => navigate(`/practice?source=vocab&level=${data.suggested[0].level}`)}>
                <Icon name="target" size={13} /> {t("practice.startLevel", { level: data.suggested[0].level })}
              </button>
            </div>
          )}
        </aside>
      </div>
    </Layout>
  );
}
