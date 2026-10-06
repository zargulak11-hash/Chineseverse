// The drawing kit every ChineseVerse illustration is built from
// (components/Art.jsx renders them). One canvas (64 x 64 units), one ink
// outline (set on the <svg> in index.css), one palette (the --art-* tokens,
// day on Paper, night on Ink) and these shared pieces -- a sky and ground,
// curved Chinese roofs, windows, doors, signboards, lanterns, trees -- so a
// bank, a tea house and a metro entrance read as one hand's work, and a new
// place is a composition of parts instead of new artwork code.
//
// Conventions: the ground line is y = 46, buildings stand on y = 48, and
// everything that matters stays inside the inscribed circle (centre 32,32,
// radius 30) because the map crops the same art round. `.dt` marks fine
// detail that drops out at small sizes; `.ns` marks shapes without outline.

const range = (n) => Array.from({ length: n }, (_, i) => i);

// --------------------------------------------------------------- backdrops

const FAR = {
  city: "M0 46V37h5v-4h6v6h4v-9h7v9h3v-5h6v5h14v-7h6v3h6v-6h7v17z",
  hills: "M0 46V40Q9 31 19 38Q30 28 42 36Q52 30 64 36V46Z",
  none: null,
};

// The sky (with a sun by day, a moon and stars by night), a far skyline or
// hills, and the ground the building stands on.
export function Backdrop({ ground = "pave", far = "city", sun = true, clouds = true }) {
  return (
    <g className="ns">
      <rect className="f-sky" width="64" height="64" />
      <rect className="f-sky-2" y="30" width="64" height="16" opacity="0.7" />
      {sun && <circle className="f-sun" cx="51" cy="12" r="4.6" />}
      <g className="f-star dt">
        <circle cx="10" cy="9" r="0.7" />
        <circle cx="21" cy="5" r="0.55" />
        <circle cx="37" cy="7" r="0.7" />
        <circle cx="59" cy="23" r="0.55" />
        <circle cx="5" cy="21" r="0.5" />
        <circle cx="43" cy="17" r="0.45" />
      </g>
      {clouds && (
        <g className="f-cloud dt" opacity="0.85">
          <path d="M6 18a3 3 0 0 1 5-2a3.5 3.5 0 0 1 6 1.5a2 2 0 0 1 0 3.5H7a2 2 0 0 1-1-3z" />
          <path d="M44 26a2.4 2.4 0 0 1 4-1.6a3 3 0 0 1 5 1.2a1.7 1.7 0 0 1 0 3H45a1.6 1.6 0 0 1-1-2.6z" />
        </g>
      )}
      {FAR[far] && <path className="f-far" d={FAR[far]} />}
      <rect className={`f-${ground}`} y="46" width="64" height="18" />
      <rect className={`f-${ground}-2`} y="46" width="64" height="1.4" />
      {ground === "water" && (
        <g className="hl dt" opacity="0.7">
          <path d="M8 55h7M24 58h9M44 54h8M50 60h6M6 61h5" />
        </g>
      )}
    </g>
  );
}

// Indoors, for objects rather than buildings: a wall with a soft light and
// a wooden desk the object lies on.
export function Room({ desk = true }) {
  return (
    <g className="ns">
      <rect className="f-room" width="64" height="64" />
      <circle className="f-room-2" cx="32" cy="30" r="22" opacity="0.8" />
      <rect className="f-room-2" y="0" width="64" height="3" />
      {desk && (
        <>
          <rect className="f-wood" y="46" width="64" height="18" />
          <rect className="f-wood-2" y="46" width="64" height="1.6" />
          <path className="ln s-wood dt" d="M0 53h20M30 57h34M8 61h22" opacity="0.6" />
        </>
      )}
    </g>
  );
}

export function Shadow({ cx = 32, y = 48.4, rx = 21 }) {
  return <ellipse className="f-shadow ns" cx={cx} cy={y} rx={rx} ry="2.3" />;
}

// ------------------------------------------------------------ architecture

// A curved Chinese roof: upturned eaves, concave slopes, a ridge with
// little tips. `y` is the eave line, `hw` half the building's width.
export function Roof({ cx = 32, y, hw, h, tone = "roof", tiles = true }) {
  const l = cx - hw;
  const r = cx + hw;
  const top = y - h;
  const d = `M${l - 3} ${y - 1.8} Q${l} ${y + 0.7} ${l + 3.4} ${y + 0.5} L${r - 3.4} ${y + 0.5} Q${r} ${y + 0.7} ${r + 3} ${y - 1.8}`
    + ` Q${r - hw * 0.32} ${y - h * 0.42} ${cx + hw * 0.55} ${top} L${cx - hw * 0.55} ${top} Q${l + hw * 0.32} ${y - h * 0.42} ${l - 3} ${y - 1.8}Z`;
  const n = Math.max(2, Math.round((hw * 1.1) / 2.6));
  return (
    <g>
      <path className={`f-${tone}`} d={d} />
      {tiles && (
        <path className={`ln s-${tone === "roof" ? "roof-2" : tone === "gold" ? "wood" : "tile"} dt`}
              d={range(n).map((i) => {
                const x = cx - hw * 0.5 + (i * hw) / (n - 1);
                return `M${x} ${top + 1.2}L${x + (x - cx) * 0.25} ${y - 0.6}`;
              }).join("")} />
      )}
      <rect className={`f-${tone}-2`} x={cx - hw * 0.62} y={top - 1.5} width={hw * 1.24} height="1.9" rx="0.9" />
      <path className={`f-${tone}-2`} d={`M${cx - hw * 0.62} ${top - 0.6}l-1.6 -1.8l2.4 0.6zM${cx + hw * 0.62} ${top - 0.6}l1.6 -1.8l-2.4 0.6z`} />
    </g>
  );
}

// A window with a glint. Glass is daylight blue by day and lamplight at night.
export function Win({ x, y, w = 4, h = 5, r = 0.5, tone = "glass" }) {
  return (
    <g>
      <rect className={`f-${tone}`} x={x} y={y} width={w} height={h} rx={r} />
      <path className="hl dt" d={`M${x + 1} ${y + h - 1.1}V${y + 1}`} />
    </g>
  );
}

export function Wins({ x, y, cols, rows, w = 3.6, h = 4.4, gx = 2.2, gy = 2.4, tone }) {
  return (
    <g>
      {range(rows).flatMap((j) => range(cols).map((i) => (
        <Win key={`${i}-${j}`} x={x + i * (w + gx)} y={y + j * (h + gy)} w={w} h={h} tone={tone} />
      )))}
    </g>
  );
}

// A door; `double` splits it in two leaves, `studs` gives it the gold
// studs of a courtyard gate.
export function Door({ x, y, w, h, tone = "wood", double = false, studs = false, glass = false }) {
  return (
    <g>
      <rect className={`f-${tone}`} x={x} y={y} width={w} height={h} rx="0.6" />
      {glass && <rect className="f-glass ns" x={x + 1} y={y + 1.2} width={w - 2} height={h * 0.45} rx="0.4" />}
      {double && <path className="ln" d={`M${x + w / 2} ${y}V${y + h}`} />}
      {studs && (
        <g className="f-gold ns dt">
          {range(3).flatMap((j) => [0.25, 0.75].map((f) => (
            <circle key={`${j}-${f}`} cx={x + w * f} cy={y + 2.2 + j * ((h - 4) / 2)} r="0.45" />
          )))}
        </g>
      )}
      <circle className="f-gold ns" cx={x + w / 2 + (double ? -0.9 : w / 4)} cy={y + h * 0.55} r="0.55" />
      {double && <circle className="f-gold ns" cx={x + w / 2 + 0.9} cy={y + h * 0.55} r="0.55" />}
    </g>
  );
}

// A signboard with real Chinese on it -- the word a learner will meet at
// that door. Red with gold letters by default; `ink` is gold on dark wood.
const SIGN = {
  roof: ["f-roof", "f-gold"],
  wood: ["f-wood-2", "f-gold"],
  jade: ["f-jade", "f-paper"],
  blue: ["f-blue", "f-paper"],
  paper: ["f-paper", "f-roof"],
  gold: ["f-gold", "f-roof-2"],
  screen: ["f-screen", "f-gold"],
};

export function Sign({ x, y, w, h = 5, text, tone = "roof", size, vertical = false }) {
  const [bg, fg] = SIGN[tone] || SIGN.roof;
  const fs = size || (vertical ? w * 0.72 : h * 0.66);
  const chars = [...text];
  return (
    <g>
      <rect className={bg} x={x} y={y} width={w} height={h} rx="0.8" />
      {vertical
        ? chars.map((ch, i) => (
          <text key={i} className={`tx ${fg}`} x={x + w / 2} y={y + (h / chars.length) * (i + 0.5)} fontSize={fs}>{ch}</text>
        ))
        : <text className={`tx ${fg}`} x={x + w / 2} y={y + h / 2 + 0.2} fontSize={fs}>{text}</text>}
    </g>
  );
}

// Classical columns between a base and a beam.
export function Columns({ x, y, h, n, gap, w = 2.4, tone = "paper" }) {
  return (
    <g>
      {range(n).map((i) => (
        <g key={i}>
          <rect className={`f-${tone}`} x={x + i * gap} y={y} width={w} height={h} />
          <rect className={`f-${tone}`} x={x + i * gap - 0.6} y={y} width={w + 1.2} height="1.2" />
        </g>
      ))}
    </g>
  );
}

export function Steps({ cx = 32, y = 48, w = 24, n = 2 }) {
  return (
    <g>
      {range(n).map((i) => (
        <rect key={i} className="f-stone" x={cx - w / 2 + i * 1.6} y={y - (n - i) * 1.6} width={w - i * 3.2} height="1.6" />
      ))}
    </g>
  );
}

// A striped shop awning with a scalloped edge.
export function Awning({ x, y, w, n = 6, h = 4, a = "roof", b = "paper" }) {
  const s = w / n;
  const scallops = range(n).map(() => `a${s / 2} ${s * 0.42} 0 0 1 ${-s} 0`).join("");
  return (
    <g>
      {range(n).map((i) => (
        <path key={i} className={`f-${i % 2 ? b : a} ns`}
              d={`M${x + i * s} ${y}h${s}v${h}a${s / 2} ${s * 0.42} 0 0 1 ${-s} 0z`} />
      ))}
      <path d={`M${x} ${y}H${x + w}V${y + h}${scallops}Z`} />
    </g>
  );
}

export function Flag({ x, y, h = 10, tone = "roof" }) {
  return (
    <g>
      <path className="ln" d={`M${x} ${y}V${y - h}`} style={{ strokeWidth: 0.9 }} />
      <path className={`f-${tone}`} d={`M${x} ${y - h}q3 -1 6 0.4t5 0v4.6q-2.5 1.4 -5 0t-6 0z`} />
    </g>
  );
}

// ------------------------------------------------------------ street life

export function Tree({ x, y = 48, r = 5, tone = "leaf" }) {
  return (
    <g>
      <rect className="f-wood" x={x - 0.9} y={y - r * 1.2} width="1.8" height={r * 1.2} />
      <circle className={`f-${tone}`} cx={x} cy={y - r * 1.5} r={r} />
      <circle className={`f-${tone}-2 ns`} cx={x + r * 0.32} cy={y - r * 1.25} r={r * 0.55} opacity="0.7" />
      <ellipse className="f-paper ns dt" cx={x - r * 0.38} cy={y - r * 1.95} rx={r * 0.32} ry={r * 0.2} opacity="0.35"
               transform={`rotate(-35 ${x - r * 0.38} ${y - r * 1.95})`} />
    </g>
  );
}

// A red lantern hanging from (x, y).
export function Lantern({ x, y, s = 1 }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <path className="ln" d="M0 0v1.4" />
      <rect className="f-gold" x="-1" y="1.3" width="2" height="0.9" rx="0.3" />
      <ellipse className="f-roof" cx="0" cy="4" rx="2.2" ry="2.1" />
      <path className="ln s-roof-2 dt" d="M0 2v4M-1.3 2.4q-0.6 1.6 0 3.2M1.3 2.4q0.6 1.6 0 3.2" />
      <rect className="f-gold" x="-0.9" y="5.9" width="1.8" height="0.8" rx="0.3" />
      <path className="ln s-gold" d="M0 6.8v1.4" />
    </g>
  );
}

export function StreetLamp({ x, y = 48, h = 16 }) {
  return (
    <g>
      <circle className="f-sun ns dt" cx={x} cy={y - h + 1} r="3" opacity="0.35" />
      <path className="ln" d={`M${x} ${y}V${y - h + 2}`} style={{ strokeWidth: 1 }} />
      <rect className="f-glass" x={x - 1.4} y={y - h} width="2.8" height="2.8" rx="0.6" />
    </g>
  );
}

export function Bush({ x, y = 48, r = 3, tone = "leaf" }) {
  return <path className={`f-${tone}`} d={`M${x - r} ${y}a${r} ${r} 0 0 1 ${r * 0.9} ${-r * 1.2}a${r} ${r} 0 0 1 ${r * 1.4} 0.2a${r * 0.8} ${r * 0.8} 0 0 1 ${r * 0.7} ${r}z`} />;
}

// A potted plant beside a door.
export function Pot({ x, y = 48 }) {
  return (
    <g>
      <circle className="f-leaf" cx={x} cy={y - 5.2} r="2.4" />
      <path className="f-wood" d={`M${x - 1.8} ${y - 3}h3.6l-0.6 3h-2.4z`} />
    </g>
  );
}

export function Notes({ x, y, s = 1, tone = "gold" }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`} className="dt">
      <path className={`f-${tone}`} d="M0 4a1.4 1.1 0 1 0 1.4 0.6V-1.4l3.4 -1v4.6a1.4 1.1 0 1 0 1.4 0.6V-4.4l-6.2 1.8z" />
    </g>
  );
}

// ------------------------------------------------------------ indoor props

// A phone lying in the light: dark body, bright screen. Children draw on
// the screen (x+2 .. x+w-2, y+3 .. y+h-3).
export function Phone({ x = 21, y = 8, w = 22, h = 38, children }) {
  return (
    <g>
      <rect className="f-shadow ns" x={x + 1.5} y={y + 2} width={w} height={h} rx="4" />
      <rect className="f-tile-2" x={x} y={y} width={w} height={h} rx="4" />
      <rect className="f-paper" x={x + 2} y={y + 3} width={w - 4} height={h - 6} rx="1.5" />
      <rect className="f-tile-2 ns" x={x + w / 2 - 3} y={y + 1} width="6" height="1.1" rx="0.5" />
      {children}
    </g>
  );
}

// A case folder (manila, with a tab and the red 案 stamp of a case file).
export function Dossier() {
  return (
    <g>
      <path className="f-shadow ns" d="M10 18h46v32H10z" transform="translate(1.5 2)" />
      <path className="f-gold-2" d="M9 14h14l3 3h30v33H9z" />
      <rect className="f-gold" x="9" y="18.5" width="47" height="31.5" rx="1" />
      <g transform="translate(47 42) rotate(-12)">
        <rect className="f-roof ns" x="-4.2" y="-4.2" width="8.4" height="8.4" rx="1.2" opacity="0.9" />
        <text className="tx f-paper" x="0" y="0.3" fontSize="5.6">案</text>
      </g>
    </g>
  );
}

// A magnifying glass: the detective's tool, also used on the map's
// detective agency sign.
export function Magnifier({ x, y, r = 5, angle = 40 }) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${angle})`}>
      <rect className="f-wood-2" x="-1.1" y={r} width="2.2" height={r * 1.3} rx="1" />
      <circle className="f-glass" r={r} />
      <circle className="ln s-gold" r={r - 0.8} style={{ strokeWidth: 1.4 }} />
      <path className="hl" d={`M${-r * 0.5} ${-r * 0.1}a${r * 0.55} ${r * 0.55} 0 0 1 ${r * 0.45} ${-r * 0.45}`} />
    </g>
  );
}

// A speech bubble (tail bottom-left unless `flip`).
export function Bubble({ x, y, w, h, tone = "paper", flip = false, children }) {
  const tail = flip
    ? `M${x + w - 5} ${y + h}l2.5 3.5l0.5 -3.5z`
    : `M${x + 4} ${y + h}l-0.5 3.5l3 -3.5z`;
  return (
    <g>
      <path className={`f-${tone}`} d={`M${x + 2} ${y}h${w - 4}a2 2 0 0 1 2 2v${h - 4}a2 2 0 0 1 -2 2H${x + 2}a2 2 0 0 1 -2 -2V${y + 2}a2 2 0 0 1 2 -2z`} />
      <path className={`f-${tone}`} d={tail} />
      <path className={`f-${tone} ns`} d={`M${x + (flip ? w - 6 : 3)} ${y + h - 1.2}h3.4v1.6h-3.4z`} />
      {children}
    </g>
  );
}

// A flat card (paper on the desk) for the pronunciation boards.
export function Card({ x = 9, y = 9, w = 46, h = 36, tone = "paper" }) {
  return (
    <g>
      <rect className="f-shadow ns" x={x + 1.5} y={y + 2} width={w} height={h} rx="3" />
      <rect className={`f-${tone}`} x={x} y={y} width={w} height={h} rx="3" />
    </g>
  );
}

export function Star({ x, y, r = 2, tone = "gold" }) {
  const pts = range(10).map((i) => {
    const a = (Math.PI / 5) * i - Math.PI / 2;
    const rr = i % 2 ? r * 0.45 : r;
    return `${(x + Math.cos(a) * rr).toFixed(2)},${(y + Math.sin(a) * rr).toFixed(2)}`;
  });
  return <polygon className={`f-${tone}`} points={pts.join(" ")} />;
}

export { range };
