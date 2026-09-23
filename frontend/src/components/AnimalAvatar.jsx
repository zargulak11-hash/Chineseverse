// Hand-drawn flat-icon SVG portraits for all 16 companions — vivid,
// friendly, cartoon-mascot style (bold flat colors, big expressive eyes,
// rounded shapes) rather than a realistic or muted treatment, because this
// is a playful gamified learning app, not a dashboard. One shared renderer
// + a per-animal "recipe" (ear shape, pattern, eye style, and its own
// distinct color trio) keeps this DRY instead of 16 bespoke components,
// while every animal still gets a genuinely different silhouette AND its
// own vivid color identity — no shared "one tone for everything."

const RECIPES = {
  fox:            { ear: "pointy",     pattern: "cheeks",   eye: "round",  base: "#FF8A3D", light: "#FFE7CE", dark: "#D9631C", bg: "#FFEEDD" },
  wolf:           { ear: "pointyWide", pattern: "none",     eye: "slit",   base: "#7C93D9", light: "#E7ECFC", dark: "#4F63A8", bg: "#E7ECFC" },
  snake:          { ear: "hood",       pattern: "scale",    eye: "slit",   base: "#4CC26B", light: "#DFF9E6", dark: "#2E9A4C", bg: "#DFF9E6" },
  cheetah:        { ear: "round",      pattern: "spots",    eye: "tear",   base: "#FFC24B", light: "#FFF3D6", dark: "#C98A1F", bg: "#FFF3D9" },
  cat:            { ear: "pointy",     pattern: "whiskers", eye: "round",  base: "#C58AF2", light: "#F3E6FF", dark: "#8D57C4", bg: "#F2E6FF" },
  dog:            { ear: "droop",      pattern: "none",     eye: "round",  base: "#FFB648", light: "#FFEBC7", dark: "#D98A1E", bg: "#FFF0D9" },
  tiger:          { ear: "round",      pattern: "stripes",  eye: "slit",   base: "#FF7A45", light: "#FFDDC9", dark: "#C1441F", bg: "#FFE3D3" },
  rabbit:         { ear: "tall",       pattern: "none",     eye: "round",  base: "#FFAFC8", light: "#FFE3EC", dark: "#E0709A", bg: "#FFE9F0" },
  bird:           { ear: "none",       pattern: "beak",     eye: "round",  base: "#4FC3F7", light: "#E1F6FF", dark: "#1E93C9", bg: "#E4F7FF" },
  capybara:       { ear: "roundSmall", pattern: "none",     eye: "sleepy", base: "#C68B5B", light: "#F2E0CB", dark: "#93602E", bg: "#F5E9D8" },
  panther:        { ear: "pointy",     pattern: "none",     eye: "glow",   base: "#8B7AE8", light: "#E5E0FC", dark: "#5A48B8", bg: "#E9E5FC" },
  sheep:          { ear: "droopSmall", pattern: "wool",     eye: "round",  base: "#F6F0FF", light: "#E4D6F9", dark: "#B79ADB", bg: "#FAF6FF" },
  panda:          { ear: "roundBig",   pattern: "mask",     eye: "round",  base: "#FFFFFF", light: "#2C2C30", dark: "#2C2C30", bg: "#E3F7EC" },
  "red-panda":    { ear: "roundSmall", pattern: "facemask", eye: "round",  base: "#E8703A", light: "#FFDFC7", dark: "#A84B20", bg: "#FFE7D6" },
  phoenix:        { ear: "crest",      pattern: "beak",     eye: "glow",   base: "#FF6B4A", light: "#FFD35C", dark: "#D6431F", bg: "#FFE3CF" },
  "golden-dragon": { ear: "horn",      pattern: "ridge",    eye: "glow",   base: "#FFC93C", light: "#3DBD6B", dark: "#C99312", bg: "#FFF3CE" },
};

const FALLBACK = { ear: "round", pattern: "none", eye: "round", base: "#B0B0B8", light: "#EDEDF0", dark: "#7A7A82", bg: "#EDEDF0" };

const INK = "#2A2320"; // eye/outline ink — warm near-black, not pure black

function Ears({ shape, color, outline }) {
  const p = { fill: color, stroke: outline, strokeWidth: 2, strokeLinejoin: "round" };
  switch (shape) {
    case "pointy":
      return (
        <>
          <path d="M18 20 L10 4 L28 15 Z" {...p} />
          <path d="M46 20 L54 4 L36 15 Z" {...p} />
        </>
      );
    case "pointyWide":
      return (
        <>
          <path d="M16 22 L4 2 L30 14 Z" {...p} />
          <path d="M48 22 L60 2 L34 14 Z" {...p} />
        </>
      );
    case "round":
      return (
        <>
          <circle cx="16" cy="12" r="9" {...p} />
          <circle cx="48" cy="12" r="9" {...p} />
        </>
      );
    case "roundBig":
      return (
        <>
          <circle cx="14" cy="10" r="11" {...p} />
          <circle cx="50" cy="10" r="11" {...p} />
        </>
      );
    case "roundSmall":
      return (
        <>
          <circle cx="18" cy="14" r="7" {...p} />
          <circle cx="46" cy="14" r="7" {...p} />
        </>
      );
    case "droop":
      return (
        <>
          <ellipse cx="14" cy="26" rx="7" ry="14" {...p} />
          <ellipse cx="50" cy="26" rx="7" ry="14" {...p} />
        </>
      );
    case "droopSmall":
      return (
        <>
          <ellipse cx="16" cy="22" rx="6" ry="10" {...p} />
          <ellipse cx="48" cy="22" rx="6" ry="10" {...p} />
        </>
      );
    case "tall":
      return (
        <>
          <ellipse cx="20" cy="4" rx="6" ry="16" {...p} />
          <ellipse cx="44" cy="4" rx="6" ry="16" {...p} />
        </>
      );
    case "hood":
      return <path d="M10 30 Q32 2 54 30 Q32 20 10 30 Z" {...p} />;
    case "crest":
      return (
        <>
          <path d="M28 6 Q32 -6 36 6 Q32 10 28 6 Z" {...p} />
          <path d="M22 10 Q26 -2 31 8 Q26 12 22 10 Z" {...p} />
          <path d="M42 10 Q38 -2 33 8 Q38 12 42 10 Z" {...p} />
        </>
      );
    case "horn":
      return (
        <>
          <path d="M20 16 Q16 0 26 6 Q24 14 20 16 Z" {...p} />
          <path d="M44 16 Q48 0 38 6 Q40 14 44 16 Z" {...p} />
        </>
      );
    default:
      return null;
  }
}

// Big, round, friendly eyes with a white sparkle highlight — the single
// biggest lever for "cute mascot" vs "muted silhouette".
function Eyes({ style, glowColor }) {
  const Sparkle = ({ cx, cy }) => <circle cx={cx - 1.1} cy={cy - 1.1} r="1.1" fill="#fff" opacity="0.9" />;
  switch (style) {
    case "slit":
      return (
        <>
          <ellipse cx="24" cy="32" rx="4.4" ry="5" fill={INK} />
          <ellipse cx="40" cy="32" rx="4.4" ry="5" fill={INK} />
          <Sparkle cx={24} cy={30} />
          <Sparkle cx={40} cy={30} />
        </>
      );
    case "sleepy":
      return (
        <>
          <path d="M19 32 Q23.5 35.5 28 32" stroke={INK} strokeWidth="2.6" fill="none" strokeLinecap="round" />
          <path d="M36 32 Q40.5 35.5 45 32" stroke={INK} strokeWidth="2.6" fill="none" strokeLinecap="round" />
        </>
      );
    case "tear":
      return (
        <>
          <circle cx="24" cy="32" r="4" fill={INK} />
          <circle cx="40" cy="32" r="4" fill={INK} />
          <Sparkle cx={24} cy={30} />
          <Sparkle cx={40} cy={30} />
          <path d="M24 36.5 L22 41" stroke={INK} strokeWidth="1.8" strokeLinecap="round" />
          <path d="M40 36.5 L42 41" stroke={INK} strokeWidth="1.8" strokeLinecap="round" />
        </>
      );
    case "glow":
      return (
        <>
          <circle cx="24" cy="32" r="4.6" fill={glowColor} />
          <circle cx="40" cy="32" r="4.6" fill={glowColor} />
          <circle cx="24" cy="32" r="2" fill={INK} />
          <circle cx="40" cy="32" r="2" fill={INK} />
          <Sparkle cx={24} cy={30} />
          <Sparkle cx={40} cy={30} />
        </>
      );
    default:
      return (
        <>
          <circle cx="24" cy="32" r="4.4" fill={INK} />
          <circle cx="40" cy="32" r="4.4" fill={INK} />
          <Sparkle cx={24} cy={30} />
          <Sparkle cx={40} cy={30} />
        </>
      );
  }
}

function Pattern({ type, dark, light }) {
  switch (type) {
    case "stripes":
      return (
        <g stroke={dark} strokeWidth="2.6" strokeLinecap="round" opacity="0.85">
          <path d="M14 22 L21 29" />
          <path d="M50 22 L43 29" />
          <path d="M12 37 L20 40" />
          <path d="M52 37 L44 40" />
        </g>
      );
    case "spots":
      return (
        <g fill={dark} opacity="0.8">
          <circle cx="16" cy="29" r="2.2" />
          <circle cx="48" cy="29" r="2.2" />
          <circle cx="13" cy="40" r="1.8" />
          <circle cx="51" cy="40" r="1.8" />
        </g>
      );
    case "mask":
      return (
        <g fill={dark} opacity="0.95">
          <ellipse cx="24" cy="31" rx="6.5" ry="5.5" />
          <ellipse cx="40" cy="31" rx="6.5" ry="5.5" />
        </g>
      );
    case "facemask":
      return <path d="M15 23 Q32 42 49 23 Q32 34 15 23 Z" fill={dark} opacity="0.5" />;
    case "wool":
      return (
        <g fill={light} opacity="1">
          <circle cx="12" cy="17" r="7" />
          <circle cx="52" cy="17" r="7" />
          <circle cx="7" cy="30" r="6" />
          <circle cx="57" cy="30" r="6" />
        </g>
      );
    case "scale":
      return (
        <g fill={light} opacity="0.85">
          <path d="M28 40 L32 44 L36 40 L32 36 Z" />
          <path d="M28 48 L32 52 L36 48 L32 44 Z" />
        </g>
      );
    case "cheeks":
      return null; // handled by the universal blush below
    case "whiskers":
      return (
        <g stroke={dark} strokeWidth="1.2" opacity="0.6" strokeLinecap="round">
          <path d="M14 38 L2 36" />
          <path d="M14 41 L2 42" />
          <path d="M50 38 L62 36" />
          <path d="M50 41 L62 42" />
        </g>
      );
    case "beak":
      return <path d="M26 36 Q32 47 38 36 Q32 41 26 36 Z" fill="#FFB648" stroke="#D98A1E" strokeWidth="1.4" />;
    case "ridge":
      return (
        <g fill={light} opacity="1">
          <path d="M30 5 L32 12 L34 5 Z" />
          <path d="M26 9 L28 15 L30 9 Z" />
          <path d="M36 9 L38 15 L34 9 Z" />
        </g>
      );
    default:
      return null;
  }
}

export default function AnimalAvatar({ slug, size = 48, className = "" }) {
  const r = RECIPES[slug] || FALLBACK;
  const showMaskBody = r.pattern === "mask"; // panda: white face, dark patches drawn on top

  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      className={`animal-avatar ${className}`}
      role="img"
      aria-label={`${slug} avatar`}
    >
      <circle cx="32" cy="32" r="31" fill={r.bg} />
      <Ears shape={r.ear} color={r.base} outline={r.dark} />
      <circle cx="32" cy="34" r="20" fill={showMaskBody ? r.base : r.base} stroke={r.dark} strokeWidth="2" />
      {/* Universal rosy blush — the cheap, high-value "cute" signal every mascot in this style shares. */}
      <g opacity="0.55">
        <ellipse cx="17" cy="40" rx="4.6" ry="3" fill="#FF9E9E" />
        <ellipse cx="47" cy="40" rx="4.6" ry="3" fill="#FF9E9E" />
      </g>
      <Pattern
        type={r.pattern === "beak" ? "none" : r.pattern}
        dark={r.dark}
        light={r.light}
      />
      {(slug === "bird" || slug === "phoenix") && <Pattern type="beak" dark={r.dark} light={r.light} />}
      <Eyes style={r.eye} glowColor={r.light} />
    </svg>
  );
}

const TEXT_FALLBACK = {
  fox: "🦊", wolf: "🐺", snake: "🐍", cheetah: "🐆", cat: "🐱", dog: "🐶",
  tiger: "🐯", rabbit: "🐰", bird: "🐦", capybara: "🦫", panther: "🐈‍⬛",
  sheep: "🐑", panda: "🐼", "red-panda": "🦝", phoenix: "🐦‍🔥", "golden-dragon": "🐉",
};

export function animalFace(slug) {
  return TEXT_FALLBACK[slug] || "🐾";
}
