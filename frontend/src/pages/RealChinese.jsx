import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams, useSearchParams } from "react-router-dom";
import CompanionFigure from "../components/CompanionFigure.jsx";
import CompanionMemory from "../components/CompanionMemory.jsx";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import WordHelper from "../components/WordHelper.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { useApi } from "../hooks/useApi.js";
import { speakChinese } from "../zhSpeech.js";

// Живой китайский — the single living world of ChineseVerse.
//
// GET /api/real-life/world (services/world_map.py) says, from the learner's
// own records only, which places are open, which are explored or mastered,
// which conversation topics their vocabulary has lit up, where they were
// last and how Learning DNA tunes the scenes. This page only draws that:
// places lead into the systems that already exist (Real Chinese scenes on
// the practice engine, the World voice talks and cases, Sound World,
// Chinese Internet, Detective Mode, lessons, Character DNA, the Vocabulary
// Ecosystem, the Passport). Nothing here unlocks or completes anything.

// The canvas size, the river and the district order come with the world
// (GET /api/real-life/world -> map); these are the node and label sizes in
// canvas units.
const R = 4.6;
const RING = 2 * Math.PI * R;
const EDGE = 16; // within this of a side edge a label grows inward
const LINK_LABEL = {
  "/assistant": "nav.assistant", "/sentence": "nav.sentence", "/detective": "nav.detective",
  "/sound-world": "nav.soundWorld", "/ecosystem": "nav.ecosystem", "/voice-companion": "nav.voiceCompanion",
  "/hanzi": "nav.hanzi", "/review": "nav.review", "/duels": "nav.duels", "/vocabulary": "nav.vocabulary",
};
const MOOD = { locked: "encouraging", open: "happy", explored: "proud", mastered: "celebrating" };
const NODE_STATE_ICON = { locked: "lock", mastered: "star" };

function useNarrow(query = "(max-width: 640px)") {
  const [narrow, setNarrow] = useState(() => typeof window !== "undefined" && window.matchMedia(query).matches);
  useEffect(() => {
    const m = window.matchMedia(query);
    const on = () => setNarrow(m.matches);
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, [query]);
  return narrow;
}

// A soft curve between two places (bowed sideways so the roads read as
// streets, not a wiring diagram).
function road(a, b) {
  const mx = (a.x + b.x) / 2;
  const my = (a.y + b.y) / 2;
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len = Math.hypot(dx, dy) || 1;
  const bow = Math.min(4, len * 0.12);
  return `M ${a.x} ${a.y} Q ${mx - (dy / len) * bow} ${my + (dx / len) * bow} ${b.x} ${b.y}`;
}

// A smooth line through points (Catmull-Rom as cubic Béziers) -- the river.
function smoothPath(pts) {
  if (pts.length < 2) return "";
  let d = `M ${pts[0][0]} ${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const [p0, p1, p2, p3] = [pts[i - 1] || pts[i], pts[i], pts[i + 1], pts[i + 2] || pts[i + 1]];
    d += ` C ${p1[0] + (p2[0] - p0[0]) / 6} ${p1[1] + (p2[1] - p0[1]) / 6} ${p2[0] - (p3[0] - p1[0]) / 6} ${p2[1] - (p3[1] - p1[1]) / 6} ${p2[0]} ${p2[1]}`;
  }
  return d;
}

// A district is the ground its places and the streets between them stand
// on: a soft disc under each place joined by wide strokes along its own
// roads, drawn as one shape (the group's opacity, not each piece's, so the
// overlaps don't darken). Organic areas instead of boxes -- the riverside
// district follows the water, the centre fills the middle of the city.
function DistrictArea({ district, places, paths, tone, title }) {
  const ps = places.filter((p) => p.district === district);
  const inside = new Set(ps.map((p) => p.key));
  const byKey = Object.fromEntries(ps.map((p) => [p.key, p]));
  return (
    <g className={`lw-district tone-${tone}`}>
      <title>{title}</title>
      {ps.map((p) => <circle key={p.key} cx={p.x} cy={p.y} r={R * 2.6} />)}
      {paths.filter((r) => inside.has(r.from) && inside.has(r.to)).map((r) => (
        <line key={`${r.from}-${r.to}`} x1={byKey[r.from].x} y1={byKey[r.from].y} x2={byKey[r.to].x} y2={byKey[r.to].y}
              strokeWidth={R * 3.4} strokeLinecap="round" />
      ))}
    </g>
  );
}

function PlaceNode({ p, current, selected, animal, label, onPick, W }) {
  const ratio = p.theme.total ? p.theme.known / p.theme.total : 0;
  return (
    <g
      className={`lw-node is-${p.status}${current ? " is-current" : ""}${selected ? " is-selected" : ""}`}
      transform={`translate(${p.x} ${p.y})`}
      role="button"
      tabIndex={0}
      aria-label={label}
      aria-pressed={selected}
      onClick={() => onPick(p.key)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onPick(p.key);
        }
      }}
    >
      {/* Positioning stays on the outer <g>; everything that moves on hover
          lives in this child, scaled around its own box (transform-box:
          fill-box) so the node never slides out from under the pointer. */}
      <g className="lw-node-body">
        {current && <circle r={R + 1.6} className="lw-pulse" />}
        <circle r={R} className="lw-disc" />
        {p.status !== "locked" && ratio > 0 && (
          <circle r={R} className="lw-arc" strokeDasharray={`${ratio * RING} ${RING}`} transform="rotate(-90)" />
        )}
        <text className="lw-icon" fontSize={R * 0.85} textAnchor="middle" dominantBaseline="central">{p.icon}</text>
        {NODE_STATE_ICON[p.status] && (
          <g transform={`translate(${R * 0.78} ${-R * 0.78})`}>
            <circle r="1.35" className={`lw-badge is-${p.status}`} />
            <text fontSize="1.5" textAnchor="middle" dominantBaseline="central" className="lw-badge-text">
              {p.status === "locked" ? "🔒" : "★"}
            </text>
          </g>
        )}
      </g>
      {current && animal?.slug && (
        <image
          href={`${import.meta.env.BASE_URL}animals/${animal.slug}.png`}
          x={companionX(p, W)} y={-COMPANION / 2} width={COMPANION} height={COMPANION}
          className="lw-companion"
          preserveAspectRatio="xMidYMid slice"
        />
      )}
    </g>
  );
}

// The companion stands beside the current place's disc (labels sit above or
// below discs, never beside them); near the right edge it stands on the left.
const COMPANION = 5.6; // the companion's picture beside the current place

function companionX(p, w) {
  return p.x > w - EDGE ? -R - COMPANION - 0.4 : R + 0.4;
}

const LABEL_SIZE = 2.5;

// Rough rendered width of a label: CJK glyphs are a full em, Latin and
// Cyrillic letters about 0.58 em in the UI font at this weight.
function labelWidth(name) {
  let w = 0;
  for (const ch of name) w += /[⺀-鿿＀-￯]/.test(ch) ? LABEL_SIZE : LABEL_SIZE * 0.58;
  return w;
}

const overlaps = (a, b) => a.x1 < b.x2 && b.x1 < a.x2 && a.y1 < b.y2 && b.y1 < a.y2;

// Where each place's name goes. Below the disc by default; above when below
// would leave the canvas or run into another place's disc, the companion or
// a name already placed -- names differ in length across EN/RU/TG/ZH, so this
// is measured per locale instead of hand-tuned for one. Near the side edges a
// label grows inward instead of running off the canvas.
function layoutLabels(places, names, current, W, H) {
  const discs = places.map((p) => ({ key: p.key, x1: p.x - R, x2: p.x + R, y1: p.y - R, y2: p.y + R }));
  const cur = places.find((p) => p.key === current);
  if (cur) {
    const cx = cur.x + companionX(cur, W);
    discs.push({ key: "", x1: cx, x2: cx + COMPANION, y1: cur.y - COMPANION / 2, y2: cur.y + COMPANION / 2 });
  }
  const placed = [];
  const out = {};
  for (const p of places) {
    const w = labelWidth(names[p.key]);
    const edge = p.x < EDGE ? "start" : p.x > W - EDGE ? "end" : "middle";
    const edgeX = edge === "start" ? p.x - R : edge === "end" ? p.x + R : p.x;
    // Below, above, then beside the disc (right, left) when a long name has
    // nowhere else to go.
    const candidates = [
      { x: edgeX, y: p.y + R + LABEL_SIZE * 1.3, anchor: edge },
      { x: edgeX, y: p.y - R - LABEL_SIZE * 0.55, anchor: edge },
      { x: p.x + R + 1, y: p.y + LABEL_SIZE * 0.3, anchor: "start" },
      { x: p.x - R - 1, y: p.y + LABEL_SIZE * 0.3, anchor: "end" },
    ];
    const boxOf = (c) => {
      const x1 = c.anchor === "start" ? c.x : c.anchor === "end" ? c.x - w : c.x - w / 2;
      return { x1, x2: x1 + w, y1: c.y - LABEL_SIZE * 0.8, y2: c.y + LABEL_SIZE * 0.25 };
    };
    const inside = (b) => b.y1 >= 0 && b.y2 <= H && b.x1 >= 0 && b.x2 <= W;
    const clear = (b) => !discs.some((d) => d.key !== p.key && overlaps(b, d)) && !placed.some((o) => overlaps(b, o));
    // Nothing clear: an overlap is still better than a name cut off the map.
    const at = candidates.find((c) => inside(boxOf(c)) && clear(boxOf(c)))
      || candidates.find((c) => inside(boxOf(c))) || candidates[0];
    placed.push(boxOf(at));
    out[p.key] = at;
  }
  return out;
}

// Labels are drawn in their own layer above every node, so a node drawn
// later can never cover an earlier node's name.
function PlaceLabel({ p, name, at }) {
  return (
    <text className={`lw-label is-${p.status}`} fontSize={LABEL_SIZE} x={at.x} y={at.y} textAnchor={at.anchor}>
      {name}
    </text>
  );
}

function companionLine(t, p) {
  const lit = p.topics.filter((x) => x.lit).length;
  if (p.status === "locked") {
    return t("world.companion.locked", { words: p.to_open.map((w) => w.text).join("、"), level: p.min_level });
  }
  if (p.status === "mastered") return t("world.companion.mastered", { score: Math.round(p.scene?.best || 0) });
  if (p.status === "explored") {
    return p.scene?.rounds
      ? t("world.companion.explored", { score: Math.round(p.scene.best) })
      : t("world.companion.exploredOther");
  }
  if (p.opened_by === "words") return t("world.companion.openedByWords");
  return p.topics.length ? t("world.companion.freshTopics", { lit, total: p.topics.length }) : t("world.companion.fresh");
}

function Greeting({ g, onWord, picked }) {
  const { t } = useTranslation();
  if (!g) return null;
  return (
    <div className="lw-greeting">
      <span className="speaker">
        <span lang="zh-CN">{g.speaker?.zh}</span>
        {g.speaker?.role && g.speaker.role !== g.speaker.zh && <> · {g.speaker.role}</>}
      </span>
      <p lang="zh-CN">
        {g.tokens.map((tk, i) =>
          tk.word_id ? (
            <button key={i} type="button" className={`net-word${picked === tk.word_id ? " is-selected" : ""}`}
                    onClick={() => onWord(tk.word_id)} title={tk.meaning}>
              {tk.text}
            </button>
          ) : (
            <span key={i}>{tk.text}</span>
          )
        )}
        <button type="button" className="btn small ghost net-say" onClick={() => speakChinese(g.zh)}
                aria-label={t("companionReact.hear")} title={t("companionReact.hear")}>
          <Icon name="ear" size={12} />
        </button>
      </p>
      {g.py && <span className="pinyin">{g.py}</span>}
      <span className="sub lw-hint">{t("world.tapWords")}</span>
    </div>
  );
}

function PlacePanel({ p, animal, onClose }) {
  const { t } = useTranslation();
  const [word, setWord] = useState(null);
  useEffect(() => setWord(null), [p.key]);
  const status = t(`world.status.${p.status}`);
  return (
    <div className="lw-panel" aria-live="polite">
      <div className="row spread" style={{ margin: 0, gap: 8 }}>
        <div className="row" style={{ margin: 0, gap: 12, minWidth: 0 }}>
          <span className="scene-icon" aria-hidden="true">{p.icon}</span>
          <div style={{ minWidth: 0 }}>
            <h2 className="h2" style={{ margin: 0 }}>{t(`world.place.${p.key}.name`)}</h2>
            <span className="sub">{t(`world.district.${p.district}`)}</span>
          </div>
        </div>
        {onClose && (
          <button type="button" className="icon-btn" onClick={onClose} aria-label={t("pages.hanzi.close")}>
            <Icon name="x" size={15} />
          </button>
        )}
      </div>
      <div className="row" style={{ gap: 6, flexWrap: "wrap", margin: "12px 0 0" }}>
        <span className={`badge ${p.status === "mastered" ? "good" : p.status === "locked" ? "" : "accent"}`}>{status}</span>
        {p.status !== "locked" && p.theme.total > 0 && (
          <span className="badge">{t("world.wordsKnown", { known: p.theme.known, total: p.theme.total })}</span>
        )}
      </div>
      <p className="sub" style={{ marginTop: 8 }}>{t(`world.place.${p.key}.desc`)}</p>

      <div className={`companion-reaction mood-${MOOD[p.status]} lw-companion-line`}>
        {animal?.slug && <CompanionFigure slug={animal.slug} mood={MOOD[p.status]} size={56} />}
        <p className="cr-line" style={{ margin: 0 }}>{companionLine(t, p)}</p>
      </div>

      {p.status === "locked" ? (
        <div className="lw-section">
          <p className="side-title">{t("world.toOpen")}</p>
          <p className="sub">{t("world.toOpenText", { level: p.min_level })}</p>
          <div className="chip-row">
            {p.to_open.map((w) => (
              <button key={w.text} type="button" className="char-chip" onClick={() => w.id && setWord(w.id)}>
                <b lang="zh-CN">{w.text}</b>
                <span className="sub">{w.pinyin}</span>
                <span className="char-chip-meaning">{w.meaning}</span>
              </button>
            ))}
          </div>
          {p.to_open.length > 0 && (
            <Link to={`/sentence?text=${encodeURIComponent(p.topics[0]?.sentence || p.to_open.map((w) => w.text).join(""))}`}
                  className="btn small" style={{ marginTop: 12 }}>
              <Icon name="sparkles" size={13} /> {t("world.learnThem")}
            </Link>
          )}
        </div>
      ) : (
        <>
          <Greeting g={p.greeting} onWord={setWord} picked={word} />

          <div className="lw-actions">
            {p.scene && (
              <Link to={`/practice?source=scene&scene=${p.scene.slug}`} className="btn primary">
                <Icon name="play" size={15} /> {p.scene.rounds ? t("world.sceneAgain") : t("world.sceneStart")}
              </Link>
            )}
            {p.gateway && (
              <Link to={p.gateway} className="btn primary">
                <Icon name="arrowRight" size={15} /> {t(`world.place.${p.key}.enter`)}
              </Link>
            )}
            {p.scene && (
              <Link to={`/real-chinese/${p.scene.slug}`} className="btn small ghost">{t("world.sceneDetails")}</Link>
            )}
          </div>
          {p.scene && (
            <p className="sub" style={{ marginTop: 8 }}>
              {p.scene.rounds
                ? t("world.sceneRecord", { best: Math.round(p.scene.best), count: p.scene.rounds })
                : t("world.sceneNew", { count: p.scene.exchanges })}
            </p>
          )}

          {p.talks.length > 0 && (
            <div className="lw-section">
              <p className="side-title">{t("world.people")}</p>
              <ul className="lw-list-plain">
                {p.talks.map((tk) => (
                  <li key={tk.slug}>
                    {tk.locked ? (
                      <span className="lw-talk is-locked">
                        <Icon name="lock" size={13} /> {tk.title}
                        <span className="badge">HSK {tk.min_level}</span>
                      </span>
                    ) : (
                      <Link to={`/real-chinese/${tk.case ? "case" : "talk"}/${tk.slug}?place=${p.key}`} className="lw-talk">
                        <Icon name={tk.case ? "search" : "mic"} size={13} /> {tk.title}
                        {tk.tried && <span className="badge good">{t("world.talked")}</span>}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {p.topics.length > 0 && (
            <div className="lw-section">
              <p className="side-title">{t("world.topics")}</p>
              <ul className="lw-topics">
                {p.topics.map((tp) => (
                  <li key={tp.key} className={`lw-topic${tp.lit ? " is-lit" : ""}`}>
                    <div className="row spread" style={{ margin: 0, gap: 8 }}>
                      <b>{t(`world.topic.${tp.key}`)}</b>
                      <span className={`badge ${tp.lit ? "good" : ""}`}>{tp.lit ? t("world.topicLit") : t("world.topicDim")}</span>
                    </div>
                    <div className="chip-row" style={{ marginTop: 8 }}>
                      {tp.words.map((w) => (
                        <button key={w.text} type="button" className={`lw-word is-${w.status}`} onClick={() => w.id && setWord(w.id)}>
                          <span lang="zh-CN">{w.text}</span>
                        </button>
                      ))}
                    </div>
                    <Link to={`/sentence?text=${encodeURIComponent(tp.sentence)}`} className="lw-topic-link">
                      <span lang="zh-CN">{tp.sentence}</span> <Icon name="arrowRight" size={12} />
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(p.sound || p.internet.length > 0 || p.links?.length > 0) && (
            <div className="lw-section">
              <p className="side-title">{t("world.alsoHere")}</p>
              <ul className="lw-list-plain">
                {p.sound && (
                  <li>
                    <Link to={`/practice?source=sound&env=${p.sound.env}`} className="lw-talk">
                      <Icon name="ear" size={13} /> {t("world.listenHere")}
                      {p.sound.rounds > 0 && <span className="badge good">{Math.round(p.sound.best)}%</span>}
                    </Link>
                  </li>
                )}
                {(p.links || []).filter((to) => LINK_LABEL[to]).map((to) => (
                  <li key={to}>
                    <Link to={to} className="lw-talk">
                      <Icon name="arrowRight" size={13} /> {t(LINK_LABEL[to])}
                    </Link>
                  </li>
                ))}
                {p.internet.map((it) => (
                  <li key={it.slug}>
                    <Link to={`/internet/${it.slug}`} className="lw-talk">
                      <span aria-hidden="true">{it.icon}</span> <span lang="zh-CN">{it.title}</span>
                      {it.read && <span className="badge good">{Math.round(it.best)}%</span>}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      {word && (
        <div className="lw-section">
          <WordHelper wordId={word} onClose={() => setWord(null)} />
        </div>
      )}
    </div>
  );
}

function AdaptationCard({ ad, tier }) {
  const { t } = useTranslation();
  return (
    <div className="card side-card">
      <p className="side-title">{t("world.adaptTitle")}</p>
      <span className="badge accent">{t(`realLife.tier.${tier}`)}</span>
      <ul className="scene-rules">
        <li>{t(`world.adapt.speech.${ad.speech}`, { value: Math.round(ad.listening) })}</li>
        <li>{t(`world.adapt.words.${ad.words}`, { value: Math.round(ad.vocabulary) })}</li>
        <li>{t(`world.adapt.grammar.${ad.grammar}`, { value: Math.round(ad.grammar_value) })}</li>
      </ul>
      {!ad.evidence && <p className="sub">{t("world.adaptNoEvidence")}</p>}
      <Link to="/dna" className="btn small ghost" style={{ marginTop: 8 }}>{t("dashboard.fullDna")}</Link>
    </div>
  );
}

export default function RealChinese() {
  const { t } = useTranslation();
  const { dashboard } = useDashboard() || {};
  const animal = dashboard?.animal;
  const { data, error } = useApi("/real-life/world");
  const [params, setParams] = useSearchParams();
  const narrow = useNarrow();
  const panelRef = useRef(null);
  const selectedKey = params.get("place") || data?.current;

  const byKey = useMemo(() => Object.fromEntries((data?.places || []).map((p) => [p.key, p])), [data]);

  function pick(key) {
    setParams({ place: key }, { replace: true });
    if (narrow) setTimeout(() => panelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  }

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading>{t("world.loading")}</Loading></Layout>;

  const selected = byKey[selectedKey] || byKey[data.current];
  const pp = data.passport;
  // On a phone only the chosen place and the current one are named on the
  // map (the district list below names the rest), so only those take space.
  const shown = data.places.filter((p) => !narrow || p.key === selected?.key || p.key === data.current);
  const names = Object.fromEntries(data.places.map((p) => [p.key, t(`world.place.${p.key}.name`)]));
  const W = data.map?.w || 100;
  const H = data.map?.h || 70;
  const order = data.map?.districts || [...new Set(data.places.map((p) => p.district))];
  const labels = layoutLabels(shown, names, data.current, W, H);
  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="mapPin" size={13} /> {t("nav.realChinese")}</div>
          <h1 className="h1">{t("world.title")}</h1>
          <p className="sub">{t("world.subtitle")}</p>
        </div>
        <Link to="/passport" className="kpi-row lw-passport" aria-label={t("world.passportLink")}>
          <span className="kpi">
            <span className="kpi-value">{pp.explored}/{pp.total}</span>
            <span className="kpi-label">{t("world.explored")}</span>
          </span>
          <span className="kpi">
            <span className="kpi-value">{pp.scenes_done}/{pp.scenes_total}</span>
            <span className="kpi-label">{t("world.scenesDone")}</span>
          </span>
          <span className="kpi">
            <span className="kpi-value">{pp.skills_shown}/{pp.skills_total}</span>
            <span className="kpi-label">{t("world.skillsShown")}</span>
          </span>
        </Link>
      </header>

      <div className="ws">
        <div className="ws-main">
          <div className="lw-map" data-self-animate="true">
            <svg viewBox={`0 0 ${W} ${H}`} className="lw-svg" role="group" aria-label={t("world.mapLabel")}>
              <defs>
                <radialGradient id="lw-glow" cx="50%" cy="45%" r="70%">
                  <stop offset="0%" className="lw-glow-in" />
                  <stop offset="100%" className="lw-glow-out" />
                </radialGradient>
              </defs>
              <rect x="0" y="0" width={W} height={H} fill="url(#lw-glow)" />
              {order.map((d, i) => (
                <DistrictArea key={d} district={d} places={data.places} paths={data.paths} tone={i % 2 ? "b" : "a"}
                              title={t(`world.district.${d}`)} />
              ))}
              {data.map?.river && (
                <g className="lw-river" aria-hidden="true">
                  <path d={smoothPath(data.map.river)} className="lw-river-bank" />
                  <path d={smoothPath(data.map.river)} className="lw-river-water" />
                  <path d={smoothPath(data.map.river)} className="lw-river-shine" />
                </g>
              )}
              {data.paths.map((r) => {
                const a = byKey[r.from];
                const b = byKey[r.to];
                if (!a || !b) return null;
                const walked = ["explored", "mastered"].includes(a.status) && ["explored", "mastered"].includes(b.status);
                return <path key={`${r.from}-${r.to}`} d={road(a, b)} className={`lw-road${r.open ? " is-open" : ""}${walked ? " is-walked" : ""}`} />;
              })}
              {data.places.map((p) => (
                <PlaceNode
                  key={p.key}
                  p={p}
                  label={`${t(`world.place.${p.key}.name`)} — ${t(`world.status.${p.status}`)}`}
                  current={p.key === data.current}
                  selected={p.key === selected?.key}
                  animal={animal}
                  onPick={pick}
                  W={W}
                />
              ))}
              {shown.map((p) => <PlaceLabel key={p.key} p={p} name={names[p.key]} at={labels[p.key]} />)}
            </svg>
            <div className="lw-legend sub">
              <span><i className="lw-dot is-mastered" /> {t("world.status.mastered")}</span>
              <span><i className="lw-dot is-explored" /> {t("world.status.explored")}</span>
              <span><i className="lw-dot is-open" /> {t("world.status.open")}</span>
              <span><i className="lw-dot is-locked" /> {t("world.status.locked")}</span>
            </div>
          </div>

          {narrow && (
            <div className="lw-places" aria-label={t("world.allPlaces")}>
              {order.map((d) => (
                <div key={d}>
                  <p className="side-title">{t(`world.district.${d}`)}</p>
                  <ul className="lw-list-plain">
                    {data.places.filter((p) => p.district === d).map((p) => (
                      <li key={p.key}>
                        <button type="button" className={`lw-place-row is-${p.status}${p.key === selected?.key ? " is-selected" : ""}`}
                                onClick={() => pick(p.key)}>
                          <span aria-hidden="true" className="lw-place-icon">{p.icon}</span>
                          <span className="lw-place-name">{t(`world.place.${p.key}.name`)}</span>
                          <span className={`badge ${p.status === "mastered" ? "good" : p.status === "locked" ? "" : "accent"}`}>
                            {t(`world.status.${p.status}`)}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}

          <div className="card">
            <h2 className="h2">{t("world.companionTitle", { name: animal?.name || t("companionReact.fallbackName") })}</h2>
            <CompanionMemory animal={animal} />
          </div>
        </div>

        <aside className="ws-side">
          <div className="card side-card" ref={panelRef}>
            {selected ? <PlacePanel p={selected} animal={animal} /> : <Empty>{t("world.pickPlace")}</Empty>}
          </div>
          <AdaptationCard ad={data.adaptation} tier={data.tier} />
          <div className="card side-card">
            <p className="side-title">{t("world.howTitle")}</p>
            <p className="sub">{t("world.how", { count: data.open_by_words })}</p>
            <Bar value={data.passport.open} max={data.passport.total} />
            <p className="sub" style={{ marginTop: 8 }}>{t("world.openCount", { open: pp.open, total: pp.total })}</p>
          </div>
        </aside>
      </div>
    </Layout>
  );
}

function TierCard({ tier, rules }) {
  const { t } = useTranslation();
  return (
    <div className="card side-card">
      <p className="side-title">{t("realLife.yourTier")}</p>
      <span className="badge accent">{t(`realLife.tier.${tier}`)}</span>
      <p className="sub" style={{ marginTop: 8 }}>{t(`realLife.tierHow.${tier}`)}</p>
      <ul className="scene-rules">
        <li>{t("realLife.rule.options", { count: rules.options })}</li>
        <li>{t(rules.show_text ? (rules.show_pinyin ? "realLife.rule.textPinyin" : "realLife.rule.text") : "realLife.rule.audioFirst")}</li>
        <li>{t("realLife.rule.listening", { count: rules.listening })}</li>
        <li>{t("realLife.rule.newWords", { count: rules.new_words })}</li>
      </ul>
    </div>
  );
}

export function RealChineseScene() {
  const { t } = useTranslation();
  const { slug } = useParams();
  const { data, error } = useApi(`/real-life/scenes/${slug}`);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading /></Layout>;

  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="mapPin" size={13} /> {t("nav.realChinese")}</div>
          <h1 className="h1"><span aria-hidden="true">{data.icon}</span> {data.title}</h1>
          <p className="sub">{data.description}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">{data.exchanges}</span>
            <span className="kpi-label">{t("realLife.exchangesLabel")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{data.completed ? `${Math.round(data.best_score)}%` : "—"}</span>
            <span className="kpi-label">{t("realLife.bestLabel")}</span>
          </div>
        </div>
      </header>

      <div className="ws">
        <div className="ws-main">
          <div className="card">
            <p className="sub">
              {t("realLife.youTalkTo")} <b lang="zh-CN">{data.npc.zh}</b> · {data.npc.role}
            </p>
            <div className="row" style={{ marginTop: 16, flexWrap: "wrap" }}>
              <Link to={`/practice?source=scene&scene=${data.slug}`} className="btn primary">
                <Icon name="play" size={15} /> {data.completed ? t("realLife.playAgain") : t("realLife.start")}
              </Link>
              <Link to="/real-chinese" className="btn ghost">{t("practice.back")}</Link>
            </div>
          </div>

          <h2 className="h2 section-title">{t("realLife.wordsForYou")}</h2>
          {data.new_words.length === 0 ? (
            <Empty>{t("realLife.noNewWords")}</Empty>
          ) : (
            <div className="grid cards">
              {data.new_words.map((w) => (
                <div key={w.hanzi} className="card flat scene-word">
                  <div className="row spread" style={{ margin: 0 }}>
                    <span className="scene-line-zh" lang="zh-CN">{w.hanzi}</span>
                    {w.level && <span className="badge">HSK {w.level}</span>}
                  </div>
                  <div className="sub">{w.pinyin}</div>
                  <div>{w.meaning}</div>
                </div>
              ))}
            </div>
          )}

          {data.grammar.length > 0 && (
            <>
              <h2 className="h2 section-title">{t("realLife.grammarInScene")}</h2>
              <div className="card">
                <ul className="scene-rules" style={{ marginTop: 0 }}>
                  {data.grammar.map((g) => (
                    <li key={g.title}>
                      <b>{g.title}</b> {g.pattern && <span className="sub">· <span lang="zh-CN">{g.pattern}</span></span>}
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </div>
        <aside className="ws-side">
          <TierCard tier={data.tier} rules={data.rules} />
        </aside>
      </div>
    </Layout>
  );
}
