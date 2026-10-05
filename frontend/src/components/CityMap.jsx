import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { CityBridges, CityGround, CityLanterns, buildScenery } from "./CityScenery.jsx";
import Icon from "./Icon.jsx";
import { prefersReducedMotion } from "../anime.js";
import { StateBadges } from "./CityPanels.jsx";

// The city map of /real-chinese (pages/RealChinese.jsx): districts, roads,
// places and their labels on an SVG canvas, as a pannable, zoomable viewport.
// It only draws what GET /api/real-life/world returned.

// The canvas size, the river and the district order come with the world
// (GET /api/real-life/world -> map); these are the node and label sizes in
// canvas units.
const R = 4.6;

const RING = 2 * Math.PI * R;

const EDGE = 16; // within this of a side edge a label grows inward

const NODE_STATE_ICON = { locked: "lock", mastered: "star" };

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

function PlaceNode({ p, current, selected, recommended, animal, label, onPick, W, onHover, onFocusPlace }) {
  const ratio = p.theme.total ? p.theme.known / p.theme.total : 0;
  return (
    <g
      className={`lw-node is-${p.status}${current ? " is-current" : ""}${selected ? " is-selected" : ""}${
        recommended ? " is-recommended" : ""}${p.new ? " is-new" : ""}${p.visited ? " is-visited" : ""}`}
      transform={`translate(${p.x} ${p.y})`}
      role="button"
      tabIndex={0}
      aria-label={label}
      aria-pressed={selected}
      onClick={() => onPick(p.key)}
      onPointerEnter={(e) => e.pointerType === "mouse" && onHover?.(p.key)}
      onPointerLeave={() => onHover?.(null)}
      // A mouse press focuses the node too; only keyboard focus (Tab) should
      // move the map, or the place slides out from under a click.
      onFocus={(e) => onFocusPlace?.(p, e.currentTarget.matches(":focus-visible"))}
      onBlur={() => onHover?.(null)}
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
        {recommended && <circle r={R + 2.6} className="lw-rec-ring" />}
        <circle r={R} className="lw-disc" />
        {p.status !== "locked" && ratio > 0 && (
          <circle r={R} className="lw-arc" strokeDasharray={`${ratio * RING} ${RING}`} transform="rotate(-90)" />
        )}
        <text className="lw-icon" fontSize={R * 0.85} textAnchor="middle" dominantBaseline="central">{p.icon}</text>
        {p.new && <circle cx={-R * 0.78} cy={-R * 0.78} r="1.1" className="lw-new-dot" />}
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
// `view` is the part of the city on screen: a name first looks for a spot
// inside it, so a place fully in view never has its name cut by the edge.
function layoutLabels(places, names, current, W, H, view) {
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
      // ... then hung from the disc's left or right edge, below or above,
      // for a long name near the side of the screen.
      { x: p.x - R, y: p.y + R + LABEL_SIZE * 1.3, anchor: "start" },
      { x: p.x + R, y: p.y + R + LABEL_SIZE * 1.3, anchor: "end" },
      { x: p.x - R, y: p.y - R - LABEL_SIZE * 0.55, anchor: "start" },
      { x: p.x + R, y: p.y - R - LABEL_SIZE * 0.55, anchor: "end" },
      { x: p.x + R + 1, y: p.y + LABEL_SIZE * 0.3, anchor: "start" },
      { x: p.x - R - 1, y: p.y + LABEL_SIZE * 0.3, anchor: "end" },
    ];
    const boxOf = (c) => {
      const x1 = c.anchor === "start" ? c.x : c.anchor === "end" ? c.x - w : c.x - w / 2;
      return { x1, x2: x1 + w, y1: c.y - LABEL_SIZE * 0.8, y2: c.y + LABEL_SIZE * 0.25 };
    };
    const inside = (b) => b.y1 >= 0 && b.y2 <= H && b.x1 >= 0 && b.x2 <= W;
    const onScreen = (b) => !view || (b.x1 >= view.x0 && b.x2 <= view.x1 && b.y1 >= view.y0 && b.y2 <= view.y1);
    const clear = (b) => !discs.some((d) => d.key !== p.key && overlaps(b, d)) && !placed.some((o) => overlaps(b, o));
    // Nothing clear: an overlap is still better than a name cut off the map.
    const at = candidates.find((c) => inside(boxOf(c)) && onScreen(boxOf(c)) && clear(boxOf(c)))
      || candidates.find((c) => inside(boxOf(c)) && clear(boxOf(c)))
      || candidates.find((c) => inside(boxOf(c))) || candidates[0];
    placed.push(boxOf(at));
    out[p.key] = at;
  }
  return out;
}

// Labels are drawn in their own layer above every node, so a node drawn
// later can never cover an earlier node's name.
function PlaceLabel({ p, name, at, recommended }) {
  return (
    <text className={`lw-label is-${p.status}${recommended ? " is-recommended" : ""}`} fontSize={LABEL_SIZE} x={at.x} y={at.y} textAnchor={at.anchor}>
      {name}
    </text>
  );
}

// ---------------------------------------------------------------- navigation
// The city is larger than the screen, so the map is a viewport onto it: a
// centre (cx, cy) and a zoom k, where k = 1 shows the whole width. Drag (or
// one finger) pans, Ctrl/⌘ + wheel or two fingers zoom, the buttons and the
// keyboard do both. The view never leaves the city. A place chosen anywhere
// (the map, the district list, the topbar search) is flown to.
const K_MAX = 4;

const LABEL_MIN_PX = 8; // below this on screen, only the important names show

function fitK(W, H, aspect) {
  return Math.min(1, W / (H * aspect));
}

// `pad` (canvas units) lets the view run past the city's right/bottom edge
// by as much as a details panel covers there, so a place on that edge can
// still be brought out from under the panel.
function clampView(v, W, H, aspect, pad = { r: 0, b: 0 }) {
  const k = Math.min(K_MAX, Math.max(fitK(W, H, aspect), v.k));
  const vw = W / k;
  const vh = vw / aspect;
  const w = W + pad.r;
  const h = H + pad.b;
  return {
    k,
    cx: vw >= w ? w / 2 : Math.min(w - vw / 2, Math.max(vw / 2, v.cx)),
    cy: vh >= h ? h / 2 : Math.min(h - vh / 2, Math.max(vh / 2, v.cy)),
  };
}

function useElementSize(ref) {
  const [size, setSize] = useState({ w: 0, h: 0 });
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === "undefined") return undefined;
    const ro = new ResizeObserver(([entry]) => setSize({ w: entry.contentRect.width, h: entry.contentRect.height }));
    ro.observe(el);
    return () => ro.disconnect();
  }, [ref]);
  return size;
}

function HoverCard({ p, at, recommended }) {
  const { t } = useTranslation();
  return (
    <div className="lw-hovercard" style={{ left: at.x, top: at.y }} role="presentation">
      <b>{p.icon} {t(`world.place.${p.key}.name`)}</b>
      <span className="sub">{t(`world.district.${p.district}`)}</span>
      <span className="row" style={{ gap: 6, margin: "6px 0 0", flexWrap: "wrap" }}>
        <span className={`badge ${p.status === "mastered" ? "good" : p.status === "locked" ? "" : "accent"}`}>
          {t(`world.status.${p.status}`)}
        </span>
        {p.status === "locked"
          ? <span className="badge">HSK {p.min_level}</span>
          : p.theme.total > 0 && <span className="badge">{t("world.wordsKnown", { known: p.theme.known, total: p.theme.total })}</span>}
        <StateBadges p={p} recommended={recommended} />
      </span>
    </div>
  );
}

export default function CityMap({ data, W, H, order, names, selected, animal, onPick, narrow, sheet, overlay }) {
  const { t } = useTranslation();
  const boxRef = useRef(null);
  const svgRef = useRef(null);
  const size = useElementSize(boxRef);
  const aspect = size.w && size.h ? size.w / size.h : 1.5;
  // The zoom a visit starts at: names about 13px on a desktop, 11px on a
  // phone, whatever the map's real width.
  const home = size.w ? Math.max(fitK(W, H, aspect), (W * (narrow ? 4.4 : 5.4)) / size.w) : narrow ? 3 : 1.2;
  const focus = selected || data.places.find((p) => p.key === data.current);
  const [view, setView] = useState(() => ({ cx: focus?.x ?? W / 2, cy: focus?.y ?? H / 2, k: home }));
  // The details panel covers the right of the map on a desktop; a place
  // flown to is centred in the part left uncovered.
  const sheetPx = sheet && !narrow && size.w ? Math.min(400, size.w * 0.4) + 16 : 0;
  // ... and on a phone the bottom sheet's peek covers the bottom of the map.
  const sheetPy = sheet && narrow ? 240 : 0;
  const [hover, setHover] = useState(null);
  const perPx = size.w ? W / Math.max(view.k, fitK(W, H, aspect)) / size.w : 0;
  const v = clampView(view, W, H, aspect, { r: sheetPx * perPx, b: Math.min(sheetPy, size.h * 0.45) * perPx });
  const viewRef = useRef(v);
  viewRef.current = v;
  const vw = W / v.k;
  const vh = vw / aspect;
  const x0 = v.cx - vw / 2;
  const y0 = v.cy - vh / 2;
  const pxPerUnit = size.w ? size.w / vw : 0;
  const byKey = useMemo(() => Object.fromEntries(data.places.map((p) => [p.key, p])), [data]);
  const scenery = useMemo(() => buildScenery(data, (d) => t(`world.district.${d}`)), [data, t]);

  // Fullscreen: the whole map card (toolbar, city, details) takes the screen.
  // Hidden where the browser can't do it for an element (iPhone Safari).
  const mapRef = useRef(null);
  const [full, setFull] = useState(false);
  const canFull = typeof document !== "undefined" && document.fullscreenEnabled;
  useEffect(() => {
    const on = () => setFull(document.fullscreenElement === mapRef.current);
    document.addEventListener("fullscreenchange", on);
    return () => document.removeEventListener("fullscreenchange", on);
  }, []);
  const toggleFull = () => {
    if (document.fullscreenElement) document.exitFullscreen?.();
    else mapRef.current?.requestFullscreen?.().catch(() => {});
  };

  const anim = useRef(0);
  const flyTo = (target) => {
    cancelAnimationFrame(anim.current);
    const from = viewRef.current;
    const to = { ...from, ...target };
    if (prefersReducedMotion()) {
      setView(to);
      return;
    }
    const t0 = performance.now();
    const step = (now) => {
      const f = Math.min(1, (now - t0) / 420);
      const e = 1 - (1 - f) ** 3;
      setView({ cx: from.cx + (to.cx - from.cx) * e, cy: from.cy + (to.cy - from.cy) * e, k: from.k + (to.k - from.k) * e });
      if (f < 1) anim.current = requestAnimationFrame(step);
    };
    anim.current = requestAnimationFrame(step);
  };
  useEffect(() => () => cancelAnimationFrame(anim.current), []);

  // Once the map knows its size: start at the right zoom, on the chosen
  // place (or the companion's), clear of the details panel.
  const sized = useRef(false);
  useEffect(() => {
    if (sized.current || !size.w) return;
    sized.current = true;
    const k = home;
    setView({ k, cx: (focus?.x ?? W / 2) + (sheetPx / 2) * (W / k / size.w), cy: focus?.y ?? H / 2 });
  }, [size.w]); // eslint-disable-line react-hooks/exhaustive-deps

  // Fly to the chosen place whenever it changes (map tap, list, search).
  const selKey = selected?.key;
  useEffect(() => {
    if (!sized.current) return;
    const p = byKey[selKey];
    if (!p) return;
    const k = Math.max(viewRef.current.k, home);
    const unit = W / k / (size.w || 1);
    flyTo({ cx: p.x + (sheetPx / 2) * unit, cy: p.y + (Math.min(sheetPy, size.h * 0.45) / 2) * unit, k });
  }, [selKey]); // eslint-disable-line react-hooks/exhaustive-deps

  // Zoom by a factor around a canvas point that stays where it is on screen.
  const zoomAt = (factor, ux = viewRef.current.cx, uy = viewRef.current.cy, animate = false) => {
    const cur = viewRef.current;
    const k = Math.min(K_MAX, Math.max(fitK(W, H, aspect), cur.k * factor));
    const ow = W / cur.k;
    const nw = W / k;
    const fx = (ux - (cur.cx - ow / 2)) / ow;
    const fy = (uy - (cur.cy - ow / aspect / 2)) / (ow / aspect);
    const target = { k, cx: ux - fx * nw + nw / 2, cy: uy - fy * (nw / aspect) + nw / aspect / 2 };
    if (animate) flyTo(target);
    else setView(target);
  };

  const toUnits = (clientX, clientY) => {
    const r = svgRef.current.getBoundingClientRect();
    const cur = viewRef.current;
    const w = W / cur.k;
    return { x: cur.cx - w / 2 + ((clientX - r.left) / r.width) * w, y: cur.cy - w / aspect / 2 + ((clientY - r.top) / r.height) * (w / aspect) };
  };

  // Ctrl/⌘ + wheel zooms (a plain wheel keeps scrolling the page).
  useEffect(() => {
    const el = svgRef.current;
    if (!el) return undefined;
    const onWheel = (e) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      e.preventDefault();
      const u = toUnits(e.clientX, e.clientY);
      // Firefox reports a mouse wheel in lines (deltaMode 1, ~3 a notch)
      // where Chrome reports pixels (~100): measure both in pixels, or a
      // notch barely zooms in Firefox.
      const px = e.deltaY * (e.deltaMode === 1 ? 33 : e.deltaMode === 2 ? size.h || 800 : 1);
      zoomAt(Math.exp(-px * 0.0022), u.x, u.y);
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  });

  // Drag to pan, two fingers to pinch. The pointer is captured only once it
  // really moves, so a plain tap still reaches the place under it; a drag
  // swallows the click that ends it.
  const pointers = useRef(new Map());
  const gesture = useRef(null);
  const dragged = useRef(false);
  const onPointerDown = (e) => {
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    dragged.current = false;
    cancelAnimationFrame(anim.current);
    const pts = [...pointers.current.values()];
    gesture.current = {
      view: viewRef.current, start: pts.map((q) => ({ ...q })),
      dist: pts.length === 2 ? Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y) : 0,
    };
  };
  const onPointerMove = (e) => {
    if (!pointers.current.has(e.pointerId) || !gesture.current) return;
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const g = gesture.current;
    const pts = [...pointers.current.values()];
    const r = svgRef.current.getBoundingClientRect();
    const unitsPerPx = W / g.view.k / r.width;
    if (pts.length >= 2 && g.dist) {
      const d = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
      const mid = { x: (pts[0].x + pts[1].x) / 2, y: (pts[0].y + pts[1].y) / 2 };
      const mid0 = { x: (g.start[0].x + g.start[1].x) / 2, y: (g.start[0].y + g.start[1].y) / 2 };
      setView({ k: g.view.k * (d / g.dist), cx: g.view.cx - (mid.x - mid0.x) * unitsPerPx, cy: g.view.cy - (mid.y - mid0.y) * unitsPerPx });
      dragged.current = true;
      return;
    }
    const dx = e.clientX - g.start[0].x;
    const dy = e.clientY - g.start[0].y;
    if (!dragged.current && Math.hypot(dx, dy) < 5) return;
    if (!dragged.current) {
      dragged.current = true;
      svgRef.current.setPointerCapture?.(e.pointerId);
    }
    setView({ k: g.view.k, cx: g.view.cx - dx * unitsPerPx, cy: g.view.cy - dy * unitsPerPx });
  };
  const onPointerUp = (e) => {
    pointers.current.delete(e.pointerId);
    const pts = [...pointers.current.values()];
    gesture.current = pts.length ? { view: viewRef.current, start: pts.map((q) => ({ ...q })), dist: 0 } : null;
  };

  const onKeyDown = (e) => {
    // Only the map's own keys: arrows inside a floating panel scroll it.
    if (e.target !== boxRef.current && !svgRef.current?.contains(e.target)) return;
    const step = (W / viewRef.current.k) * 0.12;
    const move = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] }[e.key];
    if (move) {
      e.preventDefault();
      flyTo({ cx: viewRef.current.cx + move[0], cy: viewRef.current.cy + move[1] });
    } else if (e.key === "+" || e.key === "=") {
      zoomAt(1.4, undefined, undefined, true);
    } else if (e.key === "-" || e.key === "_") {
      zoomAt(1 / 1.4, undefined, undefined, true);
    } else if (e.key === "0") {
      flyTo({ k: fitK(W, H, aspect), cx: W / 2, cy: H / 2 });
    }
  };

  // A place reached with Tab that is off screen comes into view.
  const onFocusPlace = (p, keyboard) => {
    // A click focuses the place as well. Panning then would slide it out
    // from under the pointer between press and release, and the browser
    // sends the click to the map behind it -- Firefox lost those clicks on
    // places near the edge. Only Tab-focus brings a place into view.
    if (!keyboard) return;
    setHover(p.key);
    const cur = viewRef.current;
    const w = W / cur.k;
    const h = w / aspect;
    if (Math.abs(p.x - cur.cx) > w / 2 - R * 2 || Math.abs(p.y - cur.cy) > h / 2 - R * 2) flyTo({ cx: p.x, cy: p.y });
  };

  // Names: all of them once they are readable at this zoom, otherwise only
  // the chosen place, the current one and the one under the pointer.
  const readable = LABEL_SIZE * pxPerUnit >= LABEL_MIN_PX;
  const important = new Set([selected?.key, data.current, hover, data.recommended?.key].filter(Boolean));
  const shown = data.places.filter((p) => readable || important.has(p.key));
  const labels = layoutLabels(shown, names, data.current, W, H, { x0, y0, x1: x0 + vw, y1: y0 + vh });
  const hovered = hover && byKey[hover];

  return (
    <div className={`lw-map is-hero${full ? " is-fullscreen" : ""}`} data-self-animate="true" ref={mapRef}>
      {/* Above the city, never on it: the next stop and the map's controls. */}
      <div className="lw-toolbar">
        {overlay || <span />}
          <div className="lw-controls">
            <button type="button" className="icon-btn" onClick={() => zoomAt(1.4, undefined, undefined, true)}
                    aria-label={t("world.nav.zoomIn")} title={t("world.nav.zoomIn")} disabled={v.k >= K_MAX - 0.01}>
              <Icon name="plus" size={16} />
            </button>
            <button type="button" className="icon-btn" onClick={() => zoomAt(1 / 1.4, undefined, undefined, true)}
                    aria-label={t("world.nav.zoomOut")} title={t("world.nav.zoomOut")} disabled={v.k <= fitK(W, H, aspect) + 0.01}>
              <Icon name="minus" size={16} />
            </button>
            <button type="button" className="icon-btn" title={t("world.nav.toCompanion")} aria-label={t("world.nav.toCompanion")}
                    onClick={() => {
                      const c = byKey[data.current];
                      if (c) flyTo({ cx: c.x, cy: c.y, k: Math.max(viewRef.current.k, home) });
                    }}>
              <Icon name="crosshair" size={16} />
            </button>
            <button type="button" className="icon-btn" title={t("world.nav.whole")} aria-label={t("world.nav.whole")}
                    onClick={() => flyTo({ k: fitK(W, H, aspect), cx: W / 2, cy: H / 2 })}>
              <Icon name="world" size={16} />
            </button>
            {canFull && (
              <button type="button" className="icon-btn" aria-pressed={full} onClick={toggleFull}
                      title={t(full ? "world.nav.exitFullscreen" : "world.nav.fullscreen")}
                      aria-label={t(full ? "world.nav.exitFullscreen" : "world.nav.fullscreen")}>
                <Icon name={full ? "x" : "expand"} size={16} />
              </button>
            )}
          </div>
      </div>
      <div className="lw-viewport" ref={boxRef} tabIndex={0} onKeyDown={onKeyDown}
           role="region" aria-label={`${t("world.mapLabel")}. ${t("world.nav.keys")}`}>
        <svg ref={svgRef} viewBox={`${x0} ${y0} ${vw} ${vh}`} className="lw-svg" role="group" aria-label={t("world.mapLabel")}
             onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp}
             onPointerCancel={onPointerUp}
             onClickCapture={(e) => {
               if (dragged.current) {
                 e.stopPropagation();
                 dragged.current = false;
               }
             }}>
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
          <CityGround sc={scenery} />
          <CityBridges sc={scenery} />
          {data.paths.map((r) => {
            const a = byKey[r.from];
            const b = byKey[r.to];
            if (!a || !b) return null;
            const walked = ["explored", "mastered"].includes(a.status) && ["explored", "mastered"].includes(b.status);
            return <path key={`${r.from}-${r.to}`} d={road(a, b)} className={`lw-road${r.open ? " is-open" : ""}${walked ? " is-walked" : ""}`} />;
          })}
          <CityLanterns sc={scenery} />
          {data.places.map((p) => (
            <PlaceNode
              key={p.key}
              p={p}
              label={`${names[p.key]} — ${t(`world.status.${p.status}`)}`}
              current={p.key === data.current}
              selected={p.key === selected?.key}
              recommended={p.key === data.recommended?.key}
              animal={animal}
              onPick={onPick}
              W={W}
              onHover={setHover}
              onFocusPlace={onFocusPlace}
            />
          ))}
          {shown.map((p) => (
            <PlaceLabel key={p.key} p={p} name={names[p.key]} at={labels[p.key]} recommended={p.key === data.recommended?.key} />
          ))}
        </svg>
        {hovered && size.w > 0 && (
          <HoverCard p={hovered} recommended={hovered.key === data.recommended?.key} at={{ x: ((hovered.x - x0) / vw) * size.w, y: ((hovered.y - y0) / vh) * size.h - R * pxPerUnit - 8 }} />
        )}
        {!narrow && sheet}
      </div>
      {/* The key to the map: a strip on wide screens, folded away on a phone. */}
      <details className="lw-legend sub" open={!narrow}>
        <summary>{t("world.legend")}</summary>
        <div className="lw-legend-items">
        <span><i className="lw-dot is-mastered" /> {t("world.status.mastered")}</span>
        <span><i className="lw-dot is-explored" /> {t("world.status.explored")}</span>
        <span><i className="lw-dot is-open" /> {t("world.status.open")}</span>
        <span><i className="lw-dot is-locked" /> {t("world.status.locked")}</span>
        <span><i className="lw-dot is-current" /> {t("world.state.current")}</span>
        <span><i className="lw-dot is-recommended" /> {t("world.state.recommended")}</span>
        <span><i className="lw-dot is-new" /> {t("world.state.new")}</span>
        <span><i className="lw-dot is-visited" /> {t("world.state.visited")}</span>
        <span className="lw-hint-nav">{t(narrow ? "world.nav.hintTouch" : "world.nav.hintMouse")}</span>
        </div>
      </details>
    </div>
  );
}
