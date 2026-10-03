import { useTranslation } from "react-i18next";

// The city around the places on /real-chinese (RealChinese.jsx CityMap):
// bridges where roads cross the river, trees and parks, houses and city
// blocks, red lanterns in the food streets and the old quarter, plazas,
// ponds and the districts' names. Pure decoration -- it carries no state
// and no progress, ignores the pointer, and is laid out by a seeded
// generator so the city looks the same on every visit and for everyone.
// Nothing is drawn on a place, a road or the river.

const NODE_CLEAR = 8.5; // keep this far from a place's centre
const ROAD_CLEAR = 2.6; // ... from a road
const RIVER_CLEAR = 6.2; // ... from the river's centre line

function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function segDist(px, py, ax, ay, bx, by) {
  const dx = bx - ax;
  const dy = by - ay;
  const l = dx * dx + dy * dy || 1;
  const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / l));
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
}

// The same bowed curve RealChinese.jsx draws for a road, as points.
function roadPoints(a, b, n = 14) {
  const mx = (a.x + b.x) / 2;
  const my = (a.y + b.y) / 2;
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len = Math.hypot(dx, dy) || 1;
  const bow = Math.min(4, len * 0.12);
  const cx = mx - (dy / len) * bow;
  const cy = my + (dx / len) * bow;
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    pts.push([(1 - t) ** 2 * a.x + 2 * (1 - t) * t * cx + t * t * b.x, (1 - t) ** 2 * a.y + 2 * (1 - t) * t * cy + t * t * b.y]);
  }
  return pts;
}

function polyDist(px, py, pts) {
  let d = Infinity;
  for (let i = 0; i < pts.length - 1; i++) d = Math.min(d, segDist(px, py, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]));
  return d;
}

function intersect(p1, p2, p3, p4) {
  const d = (p2[0] - p1[0]) * (p4[1] - p3[1]) - (p2[1] - p1[1]) * (p4[0] - p3[0]);
  if (!d) return null;
  const t = ((p3[0] - p1[0]) * (p4[1] - p3[1]) - (p3[1] - p1[1]) * (p4[0] - p3[0])) / d;
  const u = ((p3[0] - p1[0]) * (p2[1] - p1[1]) - (p3[1] - p1[1]) * (p2[0] - p1[0])) / d;
  return t >= 0 && t <= 1 && u >= 0 && u <= 1 ? [p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1])] : null;
}

// What grows or stands in each district (chance per free spot).
const LOOK = {
  home: { tree: 0.35, house: 0.45 },
  campus: { tree: 0.35, block: 0.4 },
  centre: { tree: 0.12, block: 0.7 },
  health: { tree: 0.25, block: 0.5 },
  transport: { tree: 0.15, block: 0.55 },
  riverside: { tree: 0.8 },
  food: { tree: 0.15, house: 0.55, lantern: 1 },
  culture: { tree: 0.4, roof: 0.45, lantern: 1 },
  shopping: { tree: 0.12, block: 0.7 },
};

export function buildScenery(data, districtName = (d) => d) {
  const W = data.map?.w || 100;
  const H = data.map?.h || 70;
  const river = data.map?.river || [];
  const byKey = Object.fromEntries(data.places.map((p) => [p.key, p]));
  const roads = data.paths.filter((r) => byKey[r.from] && byKey[r.to]).map((r) => ({ ...r, pts: roadPoints(byKey[r.from], byKey[r.to]) }));
  const rand = rng(240160);

  const free = (x, y, extra = 0) =>
    data.places.every((p) => Math.hypot(p.x - x, p.y - y) > NODE_CLEAR + extra)
    && roads.every((r) => polyDist(x, y, r.pts) > ROAD_CLEAR + extra)
    && (!river.length || polyDist(x, y, river) > RIVER_CLEAR + extra);
  const districtAt = (x, y) => {
    let best = null;
    let bd = 24;
    for (const p of data.places) {
      const d = Math.hypot(p.x - x, p.y - y);
      if (d < bd) {
        bd = d;
        best = p.district;
      }
    }
    return best;
  };

  const trees = [];
  const houses = [];
  const blocks = [];
  const roofs = [];
  const STEP = 6.2;
  for (let gy = STEP / 2; gy < H; gy += STEP) {
    for (let gx = STEP / 2; gx < W; gx += STEP) {
      const x = gx + (rand() - 0.5) * STEP * 0.8;
      const y = gy + (rand() - 0.5) * STEP * 0.8;
      const roll = rand();
      const size = 0.8 + rand() * 0.5;
      if (x < 2 || y < 2 || x > W - 2 || y > H - 2 || !free(x, y)) continue;
      const d = districtAt(x, y);
      const look = LOOK[d] || { tree: 0.22 };
      if (look.block && roll < look.block) blocks.push({ x, y, w: 3.4 * size, h: 2.6 * size + rand() * 1.6 });
      else if (look.house && roll < look.house) houses.push({ x, y, s: size });
      else if (look.roof && roll < look.roof) roofs.push({ x, y, s: size });
      else if (roll < (look.block || look.house || look.roof || 0) + (look.tree || 0)) {
        trees.push({ x, y, r: 1.1 + rand() * 0.9, bamboo: d === "riverside" && x < 40 && y > 104 });
      }
    }
  }

  // Bridges: where a road crosses the river, a deck along the road.
  const bridges = [];
  for (const r of roads) {
    for (let i = 0; i < r.pts.length - 1; i++) {
      for (let j = 0; j < river.length - 1; j++) {
        const hit = intersect(r.pts[i], r.pts[i + 1], river[j], river[j + 1]);
        if (hit) {
          const ang = (Math.atan2(r.pts[i + 1][1] - r.pts[i][1], r.pts[i + 1][0] - r.pts[i][0]) * 180) / Math.PI;
          bridges.push({ key: `${r.from}-${r.to}`, x: hit[0], y: hit[1], ang });
        }
      }
    }
  }

  // Lanterns: strings of red lanterns along the roads inside the food street
  // and the old quarter.
  const lanterns = [];
  for (const r of roads) {
    const a = byKey[r.from];
    const b = byKey[r.to];
    if (!(LOOK[a.district]?.lantern && a.district === b.district)) continue;
    for (let i = 3, side = 1; i < r.pts.length - 3; i += 3, side = -side) {
      const [x1, y1] = r.pts[i];
      const [x2, y2] = r.pts[i + 1];
      const len = Math.hypot(x2 - x1, y2 - y1) || 1;
      lanterns.push({ x: x1 - ((y2 - y1) / len) * 1.9 * side, y: y1 + ((x2 - x1) / len) * 1.9 * side });
    }
  }

  // A pond in the park and in the bamboo garden; a paved plaza round the
  // squares where people meet.
  const ponds = ["park", "bamboo_garden"].map((k) => byKey[k]).filter(Boolean).map((p) => ({ key: p.key, x: p.x + 9, y: p.y - 6 }))
    .filter((q) => free(q.x, q.y, -4));
  const plazas = ["sound_plaza", "street", "passport_office"].map((k) => byKey[k]).filter(Boolean);

  // District names: a free spot near the middle of each district.
  const names = [];
  for (const d of data.map?.districts || []) {
    const ps = data.places.filter((p) => p.district === d);
    if (!ps.length) continue;
    const mx = ps.reduce((s, p) => s + p.x, 0) / ps.length;
    const my = ps.reduce((s, p) => s + p.y, 0) / ps.length;
    // The whole name must be clear, not just its middle: its width in canvas
    // units (3-unit capitals, wide CJK) is sampled every 3 units.
    const text = districtName(d);
    const half = ([...text].reduce((w, ch) => w + (/[⺀-鿿]/.test(ch) ? 3.4 : 2.3), 0)) / 2;
    let spot = null;
    for (let rad = 0; rad <= 30 && !spot; rad += 2) {
      for (let a = 0; a < 12 && !spot; a++) {
        const x = mx + Math.cos((a / 12) * Math.PI * 2) * rad;
        const y = my + Math.sin((a / 12) * Math.PI * 2) * rad;
        // Clear of the names under the places too (they hang ~6 below a place).
        const xs = [];
        for (let sx = x - half; sx <= x + half; sx += 3) xs.push(sx);
        xs.push(x + half);
        const clear = xs.every((sx) => free(sx, y, 0.5)
          && data.places.every((p) => Math.abs(p.x - sx) > 12 || y < p.y - 7 || y > p.y + 11));
        if (x - half > 2 && x + half < W - 2 && y > 4 && y < H - 3 && clear) spot = { x, y };
      }
    }
    if (spot) names.push({ key: d, ...spot });
  }
  return { trees, houses, blocks, roofs, bridges, lanterns, ponds, plazas, names };
}

// Under the roads and places: ground details. Over the roads: bridges.
export function CityGround({ sc }) {
  const { t } = useTranslation();
  return (
    <g className="lw-scenery" aria-hidden="true">
      {sc.ponds.map((p) => <ellipse key={p.key} cx={p.x} cy={p.y} rx="4.2" ry="2.6" className="lw-pond" />)}
      {sc.plazas.map((p) => <circle key={p.key} cx={p.x} cy={p.y} r="8.5" className="lw-plaza" />)}
      {sc.blocks.map((b, i) => <rect key={`b${i}`} x={b.x - b.w / 2} y={b.y - b.h / 2} width={b.w} height={b.h} rx="0.5" className="lw-block" />)}
      {sc.houses.map((h, i) => (
        <g key={`h${i}`} transform={`translate(${h.x} ${h.y}) scale(${h.s})`} className="lw-house">
          <rect x="-1.4" y="-0.6" width="2.8" height="2" rx="0.2" />
          <path d="M -1.9 -0.5 L 0 -2 L 1.9 -0.5 Z" />
        </g>
      ))}
      {sc.roofs.map((h, i) => (
        <g key={`r${i}`} transform={`translate(${h.x} ${h.y}) scale(${h.s})`} className="lw-roof">
          <rect x="-1.6" y="-0.3" width="3.2" height="1.9" />
          <path d="M -2.6 -0.2 Q 0 -1.6 2.6 -0.2 L 2 -1 Q 0 -2.1 -2 -1 Z" />
        </g>
      ))}
      {sc.trees.map((tr, i) =>
        tr.bamboo ? (
          <g key={`t${i}`} className="lw-bamboo">
            <line x1={tr.x - 0.6} y1={tr.y + 1.4} x2={tr.x - 0.8} y2={tr.y - 1.6} />
            <line x1={tr.x} y1={tr.y + 1.4} x2={tr.x + 0.1} y2={tr.y - 2} />
            <line x1={tr.x + 0.6} y1={tr.y + 1.4} x2={tr.x + 0.9} y2={tr.y - 1.4} />
          </g>
        ) : (
          <circle key={`t${i}`} cx={tr.x} cy={tr.y} r={tr.r} className="lw-tree" />
        ),
      )}
      {sc.names.map((n) => (
        <text key={n.key} x={n.x} y={n.y} fontSize="3" className="lw-district-name" textAnchor="middle" dominantBaseline="central">
          {t(`world.district.${n.key}`)}
        </text>
      ))}
    </g>
  );
}

export function CityBridges({ sc }) {
  return (
    <g className="lw-scenery" aria-hidden="true">
      {sc.bridges.map((b) => (
        <g key={b.key} transform={`translate(${b.x} ${b.y}) rotate(${b.ang})`} className="lw-bridge">
          <rect x="-6.2" y="-1.7" width="12.4" height="3.4" rx="0.8" />
          <line x1="-5.6" y1="-1.7" x2="5.6" y2="-1.7" />
          <line x1="-5.6" y1="1.7" x2="5.6" y2="1.7" />
        </g>
      ))}
    </g>
  );
}

export function CityLanterns({ sc }) {
  return (
    <g className="lw-scenery" aria-hidden="true">
      {sc.lanterns.map((l, i) => (
        <g key={i} className="lw-lantern">
          <circle cx={l.x} cy={l.y} r="1.05" className="lw-lantern-glow" />
          <ellipse cx={l.x} cy={l.y} rx="0.48" ry="0.6" />
        </g>
      ))}
    </g>
  );
}
