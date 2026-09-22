// Replaces raw Unicode emoji with real hand-drawn flat-icon SVG portraits.
// One shared renderer + a per-animal "recipe" (ear shape, pattern, eye
// style, base color) keeps this DRY instead of 16 bespoke components, while
// still giving every animal a genuinely distinct silhouette.

const RECIPES = {
  fox: { base: "#f97316", light: "#fff1e0", ear: "pointy", pattern: "cheeks", eye: "round" },
  wolf: { base: "#94a3b8", light: "#f1f5f9", ear: "pointyWide", pattern: "none", eye: "slit" },
  snake: { base: "#22c55e", light: "#dcfce7", ear: "hood", pattern: "scale", eye: "slit" },
  cheetah: { base: "#f59e0b", light: "#fff7ed", ear: "round", pattern: "spots", eye: "tear" },
  cat: { base: "#a78bfa", light: "#f5f3ff", ear: "pointy", pattern: "whiskers", eye: "round" },
  dog: { base: "#fbbf24", light: "#fffbeb", ear: "droop", pattern: "none", eye: "round" },
  tiger: { base: "#ea580c", light: "#fff7ed", ear: "round", pattern: "stripes", eye: "slit" },
  rabbit: { base: "#fda4af", light: "#fff1f2", ear: "tall", pattern: "none", eye: "round" },
  bird: { base: "#38bdf8", light: "#e0f2fe", ear: "none", pattern: "beak", eye: "round" },
  capybara: { base: "#a16207", light: "#fef3c7", ear: "roundSmall", pattern: "none", eye: "sleepy" },
  panther: { base: "#334155", light: "#64748b", ear: "pointy", pattern: "none", eye: "glow" },
  sheep: { base: "#e2e8f0", light: "#f8fafc", ear: "droopSmall", pattern: "wool", eye: "round" },
  panda: { base: "#111827", light: "#ffffff", ear: "roundBig", pattern: "mask", eye: "round" },
  "red-panda": { base: "#c2410c", light: "#fff7ed", ear: "roundSmall", pattern: "facemask", eye: "round" },
  phoenix: { base: "#f87171", light: "#fef2f2", ear: "crest", pattern: "beak", eye: "glow" },
  "golden-dragon": { base: "#eab308", light: "#fef9c3", ear: "horn", pattern: "ridge", eye: "glow" },
};

const FALLBACK = { base: "#9aa3c7", light: "#eef1fb", ear: "round", pattern: "none", eye: "round" };

function Ears({ shape, color }) {
  switch (shape) {
    case "pointy":
      return (
        <>
          <path d="M18 20 L10 4 L28 15 Z" fill={color} />
          <path d="M46 20 L54 4 L36 15 Z" fill={color} />
        </>
      );
    case "pointyWide":
      return (
        <>
          <path d="M16 22 L4 2 L30 14 Z" fill={color} />
          <path d="M48 22 L60 2 L34 14 Z" fill={color} />
        </>
      );
    case "round":
      return (
        <>
          <circle cx="16" cy="12" r="9" fill={color} />
          <circle cx="48" cy="12" r="9" fill={color} />
        </>
      );
    case "roundBig":
      return (
        <>
          <circle cx="14" cy="10" r="11" fill={color} />
          <circle cx="50" cy="10" r="11" fill={color} />
        </>
      );
    case "roundSmall":
      return (
        <>
          <circle cx="18" cy="14" r="7" fill={color} />
          <circle cx="46" cy="14" r="7" fill={color} />
        </>
      );
    case "droop":
      return (
        <>
          <ellipse cx="14" cy="26" rx="7" ry="14" fill={color} />
          <ellipse cx="50" cy="26" rx="7" ry="14" fill={color} />
        </>
      );
    case "droopSmall":
      return (
        <>
          <ellipse cx="16" cy="22" rx="6" ry="10" fill={color} />
          <ellipse cx="48" cy="22" rx="6" ry="10" fill={color} />
        </>
      );
    case "tall":
      return (
        <>
          <ellipse cx="20" cy="4" rx="6" ry="16" fill={color} />
          <ellipse cx="44" cy="4" rx="6" ry="16" fill={color} />
        </>
      );
    case "hood":
      return <path d="M10 30 Q32 2 54 30 Q32 20 10 30 Z" fill={color} />;
    case "crest":
      return (
        <>
          <path d="M28 6 Q32 -6 36 6 Q32 10 28 6 Z" fill={color} />
          <path d="M22 10 Q26 -2 31 8 Q26 12 22 10 Z" fill={color} />
          <path d="M42 10 Q38 -2 33 8 Q38 12 42 10 Z" fill={color} />
        </>
      );
    case "horn":
      return (
        <>
          <path d="M20 16 Q16 0 26 6 Q24 14 20 16 Z" fill={color} />
          <path d="M44 16 Q48 0 38 6 Q40 14 44 16 Z" fill={color} />
        </>
      );
    default:
      return null;
  }
}

function Eyes({ style }) {
  switch (style) {
    case "slit":
      return (
        <>
          <path d="M20 32 Q24 30 28 32" stroke="#14100a" strokeWidth="2.4" fill="none" strokeLinecap="round" />
          <path d="M36 32 Q40 30 44 32" stroke="#14100a" strokeWidth="2.4" fill="none" strokeLinecap="round" />
        </>
      );
    case "sleepy":
      return (
        <>
          <path d="M19 32 Q23.5 35 28 32" stroke="#14100a" strokeWidth="2.2" fill="none" strokeLinecap="round" />
          <path d="M36 32 Q40.5 35 45 32" stroke="#14100a" strokeWidth="2.2" fill="none" strokeLinecap="round" />
        </>
      );
    case "tear":
      return (
        <>
          <circle cx="24" cy="32" r="2.6" fill="#14100a" />
          <circle cx="40" cy="32" r="2.6" fill="#14100a" />
          <path d="M24 35 L22 40" stroke="#14100a" strokeWidth="1.6" strokeLinecap="round" />
          <path d="M40 35 L42 40" stroke="#14100a" strokeWidth="1.6" strokeLinecap="round" />
        </>
      );
    case "glow":
      return (
        <>
          <circle cx="24" cy="32" r="3.2" fill="#fde68a" />
          <circle cx="40" cy="32" r="3.2" fill="#fde68a" />
          <circle cx="24" cy="32" r="1.3" fill="#14100a" />
          <circle cx="40" cy="32" r="1.3" fill="#14100a" />
        </>
      );
    default:
      return (
        <>
          <circle cx="24" cy="32" r="3" fill="#14100a" />
          <circle cx="40" cy="32" r="3" fill="#14100a" />
        </>
      );
  }
}

function Pattern({ type, base, light }) {
  switch (type) {
    case "stripes":
      return (
        <g stroke={base} strokeWidth="2.4" strokeLinecap="round" opacity="0.55">
          <path d="M14 24 L20 30" />
          <path d="M50 24 L44 30" />
          <path d="M12 38 L19 40" />
          <path d="M52 38 L45 40" />
        </g>
      );
    case "spots":
      return (
        <g fill={base} opacity="0.55">
          <circle cx="16" cy="30" r="2" />
          <circle cx="48" cy="30" r="2" />
          <circle cx="13" cy="40" r="1.6" />
          <circle cx="51" cy="40" r="1.6" />
        </g>
      );
    case "mask":
      return (
        <g fill="#111827" opacity="0.9">
          <ellipse cx="24" cy="31" rx="6" ry="5" />
          <ellipse cx="40" cy="31" rx="6" ry="5" />
        </g>
      );
    case "facemask":
      return <path d="M16 24 Q32 40 48 24 Q32 34 16 24 Z" fill="#7c2d12" opacity="0.5" />;
    case "wool":
      return (
        <g fill={light} opacity="0.9">
          <circle cx="12" cy="18" r="6" />
          <circle cx="52" cy="18" r="6" />
          <circle cx="8" cy="30" r="5" />
          <circle cx="56" cy="30" r="5" />
        </g>
      );
    case "scale":
      return (
        <g fill={light} opacity="0.7">
          <path d="M28 40 L32 44 L36 40 L32 36 Z" />
          <path d="M28 48 L32 52 L36 48 L32 44 Z" />
        </g>
      );
    case "cheeks":
      return (
        <g fill="#fff" opacity="0.85">
          <ellipse cx="18" cy="40" rx="6" ry="4" />
          <ellipse cx="46" cy="40" rx="6" ry="4" />
        </g>
      );
    case "whiskers":
      return (
        <g stroke="#111827" strokeWidth="1" opacity="0.5" strokeLinecap="round">
          <path d="M14 38 L2 36" />
          <path d="M14 41 L2 42" />
          <path d="M50 38 L62 36" />
          <path d="M50 41 L62 42" />
        </g>
      );
    case "beak":
      return <path d="M26 36 Q32 46 38 36 Q32 40 26 36 Z" fill="#fbbf24" />;
    case "ridge":
      return (
        <g fill={light} opacity="0.8">
          <path d="M30 6 L32 12 L34 6 Z" />
          <path d="M27 10 L29 15 L31 10 Z" />
          <path d="M35 10 L37 15 L33 10 Z" />
        </g>
      );
    default:
      return null;
  }
}

export default function AnimalAvatar({ slug, accentColor, size = 48, className = "" }) {
  const recipe = RECIPES[slug] || FALLBACK;
  const base = accentColor || recipe.base;
  const earColor = recipe.ear === "roundBig" || recipe.ear === "hood" ? recipe.base : base;

  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      className={`animal-avatar ${className}`}
      role="img"
      aria-label={`${slug} avatar`}
    >
      <defs>
        <radialGradient id={`av-bg-${slug}`} cx="50%" cy="35%" r="75%">
          <stop offset="0%" stopColor={recipe.light} stopOpacity="0.9" />
          <stop offset="100%" stopColor={base} stopOpacity="0.35" />
        </radialGradient>
      </defs>
      <circle cx="32" cy="32" r="31" fill={`url(#av-bg-${slug})`} />
      <Ears shape={recipe.ear} color={earColor} />
      <circle cx="32" cy="34" r="20" fill={recipe.pattern === "mask" ? recipe.light : base} />
      <Pattern type={recipe.pattern === "beak" || recipe.pattern === "mask" ? "none" : recipe.pattern} base={base} light={recipe.light} />
      {(slug === "bird" || slug === "phoenix") && <Pattern type="beak" base={base} light={recipe.light} />}
      {recipe.pattern === "mask" && <Pattern type="mask" base={base} light={recipe.light} />}
      <Eyes style={recipe.eye} />
    </svg>
  );
}

// Kept for any spot that only needs a quick text glyph (e.g. document
// titles); the real visual everywhere else is AnimalAvatar above.
const TEXT_FALLBACK = {
  fox: "🦊", wolf: "🐺", snake: "🐍", cheetah: "🐆", cat: "🐱", dog: "🐶",
  tiger: "🐯", rabbit: "🐰", bird: "🐦", capybara: "🦫", panther: "🐈‍⬛",
  sheep: "🐑", panda: "🐼", "red-panda": "🦝", phoenix: "🐦‍🔥", "golden-dragon": "🐉",
};

export function animalFace(slug) {
  return TEXT_FALLBACK[slug] || "🐾";
}
