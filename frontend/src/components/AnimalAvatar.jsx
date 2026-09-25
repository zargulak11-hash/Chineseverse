// Original ChineseVerse character system — polished flat-vector cartoon
// portraits for all 16 companions (bold flat colors, big expressive eyes,
// clean rounded geometry, strong readable silhouettes). One shared renderer
// + a per-animal "recipe" (body plan, snout, ear shape, pattern, eye style,
// its own color trio) keeps this DRY instead of 16 bespoke components,
// while every animal still reads as a genuinely different creature — not
// "one mascot body with a different head swapped on". Snake, Bird, Phoenix
// and Golden Dragon get their own non-circular body plans since a portrait
// bust silhouette would misrepresent those species; the twelve round-bodied
// mammals share the bust *frame* (a common, legitimate convention for a
// character-portrait family) but are told apart at a glance by ear shape,
// snout, pattern, eye style and color the moment you see them.
//
// `state` (optional, defaults to "idle") swaps a small mouth/eyebrow/
// accessory overlay on the SAME base character to cover the app's
// interaction states (happy, excited, thinking, confused, correct, wrong,
// celebrating, encouraging, speaking, listening) without needing a
// separate illustration per animal per state.

const RECIPES = {
  fox:            { ear: "pointy",     snout: "pointed", pattern: "cheeks",   eye: "round",  base: "#FF8A3D", light: "#FFE7CE", dark: "#D9631C", bg: "#FFEEDD" },
  wolf:           { ear: "pointyWide", snout: "long",    pattern: "none",     eye: "slit",   base: "#7C93D9", light: "#E7ECFC", dark: "#4F63A8", bg: "#E7ECFC" },
  snake:          { body: "coil",      snout: "none",    pattern: "scale",    eye: "slit",   base: "#4CC26B", light: "#DFF9E6", dark: "#2E9A4C", bg: "#DFF9E6" },
  cheetah:        { ear: "round",      snout: "round",   pattern: "spots",    eye: "tear",   base: "#FFC24B", light: "#FFF3D6", dark: "#C98A1F", bg: "#FFF3D9" },
  cat:            { ear: "pointy",     snout: "small",   pattern: "whiskers", eye: "round",  base: "#C58AF2", light: "#F3E6FF", dark: "#8D57C4", bg: "#F2E6FF" },
  dog:            { ear: "droop",      snout: "round",   pattern: "none",     eye: "round",  base: "#FFB648", light: "#FFEBC7", dark: "#D98A1E", bg: "#FFF0D9" },
  tiger:          { ear: "round",      snout: "wide",    pattern: "stripes",  eye: "slit",   base: "#FF7A45", light: "#FFDDC9", dark: "#C1441F", bg: "#FFE3D3" },
  rabbit:         { ear: "tall",       snout: "bunny",   pattern: "none",     eye: "round",  base: "#FFAFC8", light: "#FFE3EC", dark: "#E0709A", bg: "#FFE9F0" },
  bird:           { body: "wing",      snout: "beak",    pattern: "none",     eye: "round",  base: "#4FC3F7", light: "#E1F6FF", dark: "#1E93C9", bg: "#E4F7FF" },
  capybara:       { ear: "roundSmall", snout: "flat",    pattern: "none",     eye: "sleepy", base: "#C68B5B", light: "#F2E0CB", dark: "#93602E", bg: "#F5E9D8" },
  panther:        { ear: "pointy",     snout: "small",   pattern: "none",     eye: "glow",   base: "#8B7AE8", light: "#E5E0FC", dark: "#5A48B8", bg: "#E9E5FC" },
  sheep:          { ear: "droopSmall", snout: "flat",    pattern: "wool",     eye: "round",  base: "#F6F0FF", light: "#E4D6F9", dark: "#B79ADB", bg: "#FAF6FF" },
  panda:          { ear: "roundBig",   snout: "flat",    pattern: "mask",     eye: "round",  base: "#FFFFFF", light: "#2C2C30", dark: "#2C2C30", bg: "#E3F7EC" },
  "red-panda":    { ear: "roundSmall", snout: "small",   pattern: "facemask", eye: "round",  base: "#E8703A", light: "#FFDFC7", dark: "#A84B20", bg: "#FFE7D6" },
  phoenix:        { ear: "crest",  body: "wing",    snout: "beak",  pattern: "none",  eye: "glow",   base: "#FF6B4A", light: "#FFD35C", dark: "#D6431F", bg: "#FFE3CF", tail: "flame" },
  "golden-dragon": { ear: "horn",  body: "serpent", snout: "long",  pattern: "none",  eye: "glow",   base: "#FFC93C", light: "#3DBD6B", dark: "#C99312", bg: "#FFF3CE" },
};

const FALLBACK = { ear: "round", snout: "round", pattern: "none", eye: "round", base: "#B0B0B8", light: "#EDEDF0", dark: "#7A7A82", bg: "#EDEDF0" };

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
    case "horn":
      // Golden Dragon: two curved horns, bold enough to read at avatar size.
      return (
        <>
          <path d="M20 15 Q11 1 26 5 Q27 13 20 15 Z" {...p} />
          <path d="M44 15 Q53 1 38 5 Q37 13 44 15 Z" {...p} />
        </>
      );
    case "crest":
      // Phoenix: three flame-shaped feathers swept back and up, wider and
      // taller than a simple sliver so it reads as a crest, not a bow.
      return (
        <>
          <path d="M32 12 Q30 1 36 6 Q37 12 32 12 Z" {...p} />
          <path d="M24 15 Q18 2 28 7 Q29 14 24 15 Z" {...p} />
          <path d="M40 15 Q46 2 36 7 Q35 14 40 15 Z" {...p} />
        </>
      );
    default:
      return null;
  }
}

// Big, round, friendly eyes with a white sparkle highlight — the single
// biggest lever for "cute mascot" vs "muted silhouette". Kept constant per
// animal across every `state` -- eye style is a species/personality trait
// (slit = calm predator, glow = mystical, sleepy = laid-back...), not
// something a mood swap should override.
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

// Small muzzle/nose shape drawn under the eyes — this (plus ear shape) is
// what keeps a fox from reading as "a dog with orange fur": a fox's snout
// is a slim wedge, a bulldog-ish dog gets a round bump, a big cat's face is
// flatter with almost no protruding snout, a rabbit gets a tiny bunny nose.
function Snout({ type, dark, base }) {
  switch (type) {
    case "pointed":
      return <path d="M28 38 L32 45 L36 38 Q32 41.5 28 38 Z" fill={base} stroke={dark} strokeWidth="1.3" strokeLinejoin="round" />;
    case "long":
      return <path d="M26 37 Q32 47 38 37 Q32 43 26 37 Z" fill={base} stroke={dark} strokeWidth="1.3" strokeLinejoin="round" />;
    case "round":
      return <ellipse cx="32" cy="40" rx="5.5" ry="4" fill={base} stroke={dark} strokeWidth="1.3" />;
    case "wide":
      return <path d="M24 37 Q32 45 40 37 Q32 40 24 37 Z" fill={base} stroke={dark} strokeWidth="1.3" strokeLinejoin="round" />;
    case "small":
      return <ellipse cx="32" cy="38.5" rx="2.6" ry="2" fill={dark} />;
    case "flat":
      return <ellipse cx="32" cy="38" rx="3.4" ry="2.2" fill={dark} opacity="0.85" />;
    case "bunny":
      return (
        <>
          <path d="M29.5 37.5 L32 40 L34.5 37.5 Z" fill={dark} />
          <path d="M28 43 L30 41" stroke={dark} strokeWidth="1" strokeLinecap="round" />
          <path d="M36 43 L34 41" stroke={dark} strokeWidth="1" strokeLinecap="round" />
        </>
      );
    case "beak":
      return <path d="M26 36 Q32 47 38 36 Q32 41 26 36 Z" fill="#FFB648" stroke="#D98A1E" strokeWidth="1.4" />;
    default:
      return null;
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
      // Classic panda eye-patches: bigger than the eye itself and tilted
      // like a petal, so the white eye-sparkle still pops instead of the
      // whole patch reading as one flat blob with the pupil.
      return (
        <g fill={dark} opacity="0.95">
          <ellipse cx="23" cy="30" rx="7.5" ry="9" transform="rotate(-18 23 30)" />
          <ellipse cx="41" cy="30" rx="7.5" ry="9" transform="rotate(18 41 30)" />
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
      // Snake's scale texture lives on its coiled body (see SpecialBody),
      // not the face — an empty case here on purpose.
      return null;
    case "whiskers":
      return (
        <g stroke={dark} strokeWidth="1.2" opacity="0.6" strokeLinecap="round">
          <path d="M14 38 L2 36" />
          <path d="M14 41 L2 42" />
          <path d="M50 38 L62 36" />
          <path d="M50 41 L62 42" />
        </g>
      );
    default:
      return null;
  }
}

// Small eyebrow accents above the eyes -- the lightest-weight way to shift
// mood (raised = curious/thinking, furrowed = uh-oh, happy arch = joyful)
// without touching the animal's own eye style.
function Eyebrows({ type, dark }) {
  const p = { stroke: dark, strokeWidth: 2, strokeLinecap: "round", fill: "none", opacity: 0.8 };
  switch (type) {
    case "raised":
      return (
        <>
          <path d="M19 23 Q23.5 19.5 28.5 22" {...p} />
          <path d="M35.5 22 Q40.5 19.5 45 23" {...p} />
        </>
      );
    case "furrowed":
      return (
        <>
          <path d="M20 24 L28 26" {...p} />
          <path d="M36 26 L44 24" {...p} />
        </>
      );
    case "happyArch":
      return (
        <>
          <path d="M19 24 Q23.5 20 28.5 23.5" {...p} />
          <path d="M35.5 23.5 Q40.5 20 45 24" {...p} />
        </>
      );
    default:
      return null;
  }
}

// The mouth is the single biggest state signal, so every state maps to one
// of a small, reusable set of shapes rather than a bespoke curve per animal.
function Mouth({ type }) {
  const p = { stroke: INK, strokeWidth: 2.2, strokeLinecap: "round", fill: "none" };
  switch (type) {
    case "smile":
      return <path d="M26 44 Q32 49 38 44" {...p} />;
    case "grin":
      return <path d="M24 43 Q32 52 40 43 Q32 47 24 43 Z" fill={INK} opacity="0.92" />;
    case "flat":
      return <path d="M27 45.5 L37 45.5" {...p} />;
    case "wavy":
      return <path d="M25 45 Q28.5 42.5 32 45 Q35.5 47.5 39 45" {...p} />;
    case "smallO":
      return <ellipse cx="32" cy="45.5" rx="3.4" ry="4.2" fill={INK} opacity="0.9" />;
    case "frown":
      return <path d="M26 47 Q32 42.5 38 47" {...p} />;
    default:
      return <path d="M28 45 Q32 47 36 45" {...p} />;
  }
}

// Small icon drawn near the top-right of the frame to carry the rest of the
// state's meaning (sparkle, checkmark, question mark...) — reusable across
// every animal, independent of species.
function Accessory({ type }) {
  switch (type) {
    case "sparkle":
      return (
        <g fill="#FFD54A" stroke="#E0A82E" strokeWidth="0.6">
          <path d="M52 8 L53.6 12 L57.6 13.6 L53.6 15.2 L52 19.2 L50.4 15.2 L46.4 13.6 L50.4 12 Z" />
        </g>
      );
    case "confetti":
      return (
        <g strokeLinecap="round">
          <rect x="6" y="6" width="3" height="3" fill="#FF6B6B" transform="rotate(20 7.5 7.5)" />
          <rect x="52" y="10" width="3" height="3" fill="#4FC3F7" transform="rotate(-15 53.5 11.5)" />
          <rect x="48" y="4" width="2.5" height="2.5" fill="#FFD54A" transform="rotate(35 49 5)" />
          <circle cx="10" cy="16" r="1.6" fill="#4CC26B" />
          <circle cx="58" cy="20" r="1.6" fill="#C58AF2" />
        </g>
      );
    case "checkmark":
      return (
        <g>
          <circle cx="52" cy="14" r="9" fill="#4CC26B" stroke="#fff" strokeWidth="2" />
          <path d="M48 14 L51 17 L57 10" stroke="#fff" strokeWidth="2.2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </g>
      );
    case "questionMark":
      return (
        <g fill="none" stroke="#8B7AE8" strokeWidth="2.4" strokeLinecap="round">
          <path d="M50 6 Q56 4 56 9 Q56 12.5 52 13.5 L52 16" />
          <circle cx="52" cy="20.5" r="0.4" fill="#8B7AE8" stroke="none" />
        </g>
      );
    case "sweatDrop":
      return <path d="M52 6 Q56 12 56 16 Q56 20 52 20 Q48 20 48 16 Q48 12 52 6 Z" fill="#7EC8F0" stroke="#3E9BD6" strokeWidth="1" />;
    case "soundWaves":
      return (
        <g stroke="#4FC3F7" strokeWidth="1.8" fill="none" strokeLinecap="round" opacity="0.9">
          <path d="M50 28 Q54 32 50 36" />
          <path d="M54 24 Q60 32 54 40" />
        </g>
      );
    case "earLines":
      return (
        <g stroke="#7C93D9" strokeWidth="1.8" fill="none" strokeLinecap="round" opacity="0.9">
          <path d="M8 28 Q4 32 8 36" />
          <path d="M4 24 Q-2 32 4 40" transform="translate(2,0)" />
        </g>
      );
    case "thoughtDots":
      return (
        <g fill="#B0B0B8">
          <circle cx="50" cy="18" r="1.6" />
          <circle cx="54.5" cy="13" r="2.2" />
          <circle cx="60" cy="7" r="3" />
        </g>
      );
    default:
      return null;
  }
}

const STATES = {
  idle:        { mouth: "neutral", brow: "none",      accessory: "none" },
  happy:       { mouth: "smile",   brow: "none",       accessory: "none" },
  excited:     { mouth: "grin",    brow: "happyArch",  accessory: "sparkle" },
  thinking:    { mouth: "flat",    brow: "raised",     accessory: "thoughtDots" },
  confused:    { mouth: "wavy",    brow: "raised",     accessory: "questionMark" },
  correct:     { mouth: "grin",    brow: "happyArch",  accessory: "checkmark" },
  wrong:       { mouth: "frown",   brow: "furrowed",   accessory: "sweatDrop" },
  celebrating: { mouth: "grin",    brow: "happyArch",  accessory: "confetti" },
  encouraging: { mouth: "smile",   brow: "happyArch",  accessory: "none" },
  speaking:    { mouth: "smallO",  brow: "none",       accessory: "soundWaves" },
  listening:   { mouth: "flat",    brow: "raised",     accessory: "earLines" },
};

// Non-circular body plans for the species a round "bust" silhouette would
// misrepresent. Drawn instead of the default body circle further down.
function SpecialBody({ body, base, dark, light, tail }) {
  if (body === "coil") {
    // Snake: a bold S-curve coil looping behind/below the head instead of
    // a round torso, with pale scale marks along it — reads as serpentine
    // at a glance, even at small size, and keeps the scale texture off the
    // face (see Pattern's "scale" case).
    return (
      <>
        <path
          d="M16 58 Q3 50 12 39 Q25 26 14 16 Q5 8 14 3"
          fill="none"
          stroke={base}
          strokeWidth="14"
          strokeLinecap="round"
        />
        <g fill={light} opacity="0.8">
          <ellipse cx="14" cy="50" rx="3.2" ry="4" transform="rotate(35 14 50)" />
          <ellipse cx="12" cy="34" rx="3.2" ry="4" transform="rotate(-25 12 34)" />
          <ellipse cx="13" cy="16" rx="3" ry="3.8" transform="rotate(30 13 16)" />
        </g>
      </>
    );
  }
  if (body === "wing") {
    // Bird / Phoenix: swept wings anchored at the head's upper edge and
    // sweeping well outside it (the plain head circle is drawn on top of
    // this, so the wing root must tuck just inside r=20 while the visible
    // blade extends clearly past it), optional layered flame tail for Phoenix.
    return (
      <>
        {tail === "flame" && (
          <g>
            <path d="M32 53 Q22 64 11 61 Q23 57 20 49 Z" fill={base} opacity="0.95" />
            <path d="M32 53 Q42 64 53 61 Q41 57 44 49 Z" fill={light} opacity="0.95" />
            <path d="M32 53 Q28 62 32 61 Q36 62 32 53 Z" fill="#FFF4D6" opacity="0.9" />
          </g>
        )}
        <path
          d="M17 20 Q-1 22 0 38 Q1 52 12 49 Q21 46 20 34 Q20 26 17 20 Z"
          fill={base} stroke={dark} strokeWidth="1.8" strokeLinejoin="round"
        />
        <path d="M4 32 Q10 34 15 33" fill="none" stroke={dark} strokeWidth="1.1" opacity="0.5" strokeLinecap="round" />
        <path d="M3 41 Q9 42 14 40" fill="none" stroke={dark} strokeWidth="1.1" opacity="0.5" strokeLinecap="round" />
        <path
          d="M47 20 Q65 22 64 38 Q63 52 52 49 Q43 46 44 34 Q44 26 47 20 Z"
          fill={base} stroke={dark} strokeWidth="1.8" strokeLinejoin="round"
        />
        <path d="M60 32 Q54 34 49 33" fill="none" stroke={dark} strokeWidth="1.1" opacity="0.5" strokeLinecap="round" />
        <path d="M61 41 Q55 42 50 40" fill="none" stroke={dark} strokeWidth="1.1" opacity="0.5" strokeLinecap="round" />
      </>
    );
  }
  if (body === "serpent") {
    // Golden Dragon: a thick sinuous neck/tail flourish trailing from the
    // head, with small cloud-wisp accents — a classic dragon motif that
    // also fills out the silhouette beyond "round face with horns".
    return (
      <>
        <path
          d="M45 44 Q60 46 58 56 Q57 63 44 61 Q37 59 40 55"
          fill="none"
          stroke={base}
          strokeWidth="9"
          strokeLinecap="round"
        />
        <g fill={light} opacity="0.85">
          <circle cx="57" cy="50" r="2.4" />
          <circle cx="60" cy="55" r="1.7" />
          <circle cx="49" cy="60" r="1.9" />
        </g>
      </>
    );
  }
  return null;
}

export default function AnimalAvatar({ slug, size = 48, className = "", state = "idle" }) {
  const r = RECIPES[slug] || FALLBACK;
  const st = STATES[state] || STATES.idle;
  const hasSpecialBody = r.body === "coil" || r.body === "wing" || r.body === "serpent";

  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      className={`animal-avatar ${className}`}
      role="img"
      aria-label={`${slug} avatar, ${state}`}
    >
      <circle cx="32" cy="32" r="31" fill={r.bg} />
      {hasSpecialBody && <SpecialBody body={r.body} base={r.base} dark={r.dark} light={r.light} tail={r.tail} />}
      {r.ear && <Ears shape={r.ear} color={r.base} outline={r.dark} />}
      <circle cx="32" cy="34" r="20" fill={r.base} stroke={r.dark} strokeWidth="2" />
      {/* Universal rosy blush — the cheap, high-value "cute" signal every mascot in this style shares. */}
      <g opacity="0.5">
        <ellipse cx="17" cy="40" rx="4.6" ry="3" fill="#FF9E9E" />
        <ellipse cx="47" cy="40" rx="4.6" ry="3" fill="#FF9E9E" />
      </g>
      <Pattern type={r.pattern} dark={r.dark} light={r.light} />
      <Eyebrows type={st.brow} dark={r.dark} />
      <Eyes style={r.eye} glowColor={r.light} />
      <Snout type={r.snout} dark={r.dark} base={r.dark} />
      <Mouth type={st.mouth} />
      <Accessory type={st.accessory} />
    </svg>
  );
}
