// Hand-drawn flat-icon SVG portraits for all 16 companions. One shared
// renderer + a per-animal "recipe" (ear shape, pattern, eye style) keeps
// this DRY instead of 16 bespoke components, while still giving every
// animal a genuinely distinct silhouette.
//
// Color treatment is deliberately monochrome — every animal renders in the
// same warm off-white/graphite palette, so differentiation comes entirely
// from shape (not a rainbow of per-animal brand colors, which is what this
// replaced). The two "legendary" companions — Phoenix and Golden Dragon —
// are the one place the system's single accent color appears here, used as
// a rarity signal rather than decoration.

const MONO = "#e9e6df"; // body fill — consistent across every animal
const MONO_EAR = "#c7c3ba"; // ear/secondary fill — one step darker
const MONO_DARK = "#151412"; // eyes, dark pattern lines
const LEGENDARY = "#eab244"; // the system accent — rarity signal only
const LEGENDARY_EAR = "#b8842f";

const RECIPES = {
  fox: { ear: "pointy", pattern: "cheeks", eye: "round" },
  wolf: { ear: "pointyWide", pattern: "none", eye: "slit" },
  snake: { ear: "hood", pattern: "scale", eye: "slit" },
  cheetah: { ear: "round", pattern: "spots", eye: "tear" },
  cat: { ear: "pointy", pattern: "whiskers", eye: "round" },
  dog: { ear: "droop", pattern: "none", eye: "round" },
  tiger: { ear: "round", pattern: "stripes", eye: "slit" },
  rabbit: { ear: "tall", pattern: "none", eye: "round" },
  bird: { ear: "none", pattern: "beak", eye: "round" },
  capybara: { ear: "roundSmall", pattern: "none", eye: "sleepy" },
  panther: { ear: "pointy", pattern: "none", eye: "glow" },
  sheep: { ear: "droopSmall", pattern: "wool", eye: "round" },
  panda: { ear: "roundBig", pattern: "mask", eye: "round" },
  "red-panda": { ear: "roundSmall", pattern: "facemask", eye: "round" },
  phoenix: { ear: "crest", pattern: "beak", eye: "glow", legendary: true },
  "golden-dragon": { ear: "horn", pattern: "ridge", eye: "glow", legendary: true },
};

const FALLBACK = { ear: "round", pattern: "none", eye: "round" };

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

function Eyes({ style, glowColor }) {
  switch (style) {
    case "slit":
      return (
        <>
          <path d="M20 32 Q24 30 28 32" stroke={MONO_DARK} strokeWidth="2.4" fill="none" strokeLinecap="round" />
          <path d="M36 32 Q40 30 44 32" stroke={MONO_DARK} strokeWidth="2.4" fill="none" strokeLinecap="round" />
        </>
      );
    case "sleepy":
      return (
        <>
          <path d="M19 32 Q23.5 35 28 32" stroke={MONO_DARK} strokeWidth="2.2" fill="none" strokeLinecap="round" />
          <path d="M36 32 Q40.5 35 45 32" stroke={MONO_DARK} strokeWidth="2.2" fill="none" strokeLinecap="round" />
        </>
      );
    case "tear":
      return (
        <>
          <circle cx="24" cy="32" r="2.6" fill={MONO_DARK} />
          <circle cx="40" cy="32" r="2.6" fill={MONO_DARK} />
          <path d="M24 35 L22 40" stroke={MONO_DARK} strokeWidth="1.6" strokeLinecap="round" />
          <path d="M40 35 L42 40" stroke={MONO_DARK} strokeWidth="1.6" strokeLinecap="round" />
        </>
      );
    case "glow":
      return (
        <>
          <circle cx="24" cy="32" r="3.2" fill={glowColor} />
          <circle cx="40" cy="32" r="3.2" fill={glowColor} />
          <circle cx="24" cy="32" r="1.3" fill={MONO_DARK} />
          <circle cx="40" cy="32" r="1.3" fill={MONO_DARK} />
        </>
      );
    default:
      return (
        <>
          <circle cx="24" cy="32" r="3" fill={MONO_DARK} />
          <circle cx="40" cy="32" r="3" fill={MONO_DARK} />
        </>
      );
  }
}

function Pattern({ type, dark, light }) {
  switch (type) {
    case "stripes":
      return (
        <g stroke={dark} strokeWidth="2.4" strokeLinecap="round" opacity="0.4">
          <path d="M14 24 L20 30" />
          <path d="M50 24 L44 30" />
          <path d="M12 38 L19 40" />
          <path d="M52 38 L45 40" />
        </g>
      );
    case "spots":
      return (
        <g fill={dark} opacity="0.4">
          <circle cx="16" cy="30" r="2" />
          <circle cx="48" cy="30" r="2" />
          <circle cx="13" cy="40" r="1.6" />
          <circle cx="51" cy="40" r="1.6" />
        </g>
      );
    case "mask":
      return (
        <g fill={MONO_DARK} opacity="0.88">
          <ellipse cx="24" cy="31" rx="6" ry="5" />
          <ellipse cx="40" cy="31" rx="6" ry="5" />
        </g>
      );
    case "facemask":
      return <path d="M16 24 Q32 40 48 24 Q32 34 16 24 Z" fill={dark} opacity="0.3" />;
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
        <g fill={light} opacity="0.6">
          <path d="M28 40 L32 44 L36 40 L32 36 Z" />
          <path d="M28 48 L32 52 L36 48 L32 44 Z" />
        </g>
      );
    case "cheeks":
      return (
        <g fill={light} opacity="0.75">
          <ellipse cx="18" cy="40" rx="6" ry="4" />
          <ellipse cx="46" cy="40" rx="6" ry="4" />
        </g>
      );
    case "whiskers":
      return (
        <g stroke={MONO_DARK} strokeWidth="1" opacity="0.4" strokeLinecap="round">
          <path d="M14 38 L2 36" />
          <path d="M14 41 L2 42" />
          <path d="M50 38 L62 36" />
          <path d="M50 41 L62 42" />
        </g>
      );
    case "beak":
      return <path d="M26 36 Q32 46 38 36 Q32 40 26 36 Z" fill={dark} opacity="0.55" />;
    case "ridge":
      return (
        <g fill={light} opacity="0.85">
          <path d="M30 6 L32 12 L34 6 Z" />
          <path d="M27 10 L29 15 L31 10 Z" />
          <path d="M35 10 L37 15 L33 10 Z" />
        </g>
      );
    default:
      return null;
  }
}

export default function AnimalAvatar({ slug, size = 48, className = "" }) {
  const recipe = RECIPES[slug] || FALLBACK;
  const body = recipe.legendary ? LEGENDARY : MONO;
  const ear = recipe.legendary ? LEGENDARY_EAR : MONO_EAR;
  const glowColor = recipe.legendary ? "#fff3d6" : "#eceae5";

  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      className={`animal-avatar ${className}`}
      role="img"
      aria-label={`${slug} avatar`}
    >
      <circle cx="32" cy="32" r="31" fill="var(--surface-2)" stroke="var(--border)" />
      {recipe.legendary && (
        <circle cx="32" cy="32" r="31" fill="none" stroke={LEGENDARY} strokeOpacity="0.5" strokeWidth="1.5" />
      )}
      <Ears shape={recipe.ear} color={ear} />
      <circle cx="32" cy="34" r="20" fill={recipe.pattern === "mask" ? MONO : body} />
      <Pattern
        type={recipe.pattern === "beak" || recipe.pattern === "mask" ? "none" : recipe.pattern}
        dark={ear}
        light={recipe.legendary ? "#fff8e8" : "#ffffff"}
      />
      {(slug === "bird" || slug === "phoenix") && <Pattern type="beak" dark={ear} light="#fff" />}
      {recipe.pattern === "mask" && <Pattern type="mask" dark={ear} light="#fff" />}
      <Eyes style={recipe.eye} glowColor={glowColor} />
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
