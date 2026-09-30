import { useTranslation } from "react-i18next";
import { ANIMAL_SLUGS } from "./AnimalAvatar.jsx";
import { MOODS, moodOf, speciesOf } from "../companionSpecies.js";

// The permanent companion as a living character: the SAME portrait the
// learner chose, with the mood drawn onto that species' own face (brows,
// blush, glints, tears at its measured eye positions), the species' body
// language (companionSpecies.js `motion`, animated in index.css) and its
// expressive trait (tail, wings, ears...). `mood` must come from a real
// graded reaction; `pulse` changes whenever a new reaction arrives so the
// one-shot reaction animation replays, then settles into a calm loop.
//
// Portrait sits in a 64-unit square inside an 80-unit viewBox so traits
// and effects can peek past its edge without being clipped.

const KNOWN = new Set(ANIMAL_SLUGS);
const INK = "#35231A";
// Props held in front of the portrait; tails, wings and the like peek out
// from behind it.
const FRONT_TRAITS = new Set(["yuzu", "bamboo", "bell"]);

function brow(kind, [x, y], r, side) {
  // side: -1 for the left eye (its outer end is on the left), +1 for the right.
  const w = r * 1.15;
  const by = y - r * 2.05;
  const outer = x + side * w;
  const inner = x - side * w;
  switch (kind) {
    case "brows-proud":
      return `M${outer} ${by + 0.5} Q${x} ${by - 1.6} ${inner} ${by + 0.2}`;
    case "brows-soft":
      return `M${outer} ${by + 0.4} Q${x} ${by - 1.1} ${inner} ${by - 0.7}`;
    case "brows-worried":
      return `M${outer} ${by + 0.9} Q${x} ${by + 0.2} ${inner} ${by - 1.7}`;
    case "brows-cross":
      return `M${outer} ${by - 1.5} L${inner} ${by + 1.5}`;
    case "brows-focus":
      return `M${outer} ${by - 0.9} L${inner} ${by + 0.8}`;
    default:
      return null;
  }
}

function Face({ features, eyes }) {
  const [[x1, y1], [x2, y2]] = eyes;
  const d = x2 - x1;
  const r = d * 0.19;
  const out = [];
  for (const f of features) {
    if (f === "blush") {
      out.push(
        <g key={f} className="cf-blush" fill="#FF6F8E">
          <ellipse cx={x1 - d * 0.1} cy={y1 + d * 0.36} rx={d * 0.17} ry={d * 0.095} />
          <ellipse cx={x2 + d * 0.1} cy={y2 + d * 0.36} rx={d * 0.17} ry={d * 0.095} />
        </g>
      );
    } else if (f === "glint") {
      out.push(
        <g key={f} className="cf-glint" fill="#fff">
          {[[x1, y1], [x2, y2]].map(([x, y], i) => (
            <g key={i}>
              <circle cx={x - r * 0.25} cy={y - r * 0.5} r={r * 0.3} />
              <circle cx={x + r * 0.35} cy={y + r * 0.3} r={r * 0.15} />
            </g>
          ))}
        </g>
      );
    } else if (f === "star-eyes") {
      out.push(
        <g key={f} className="cf-stareyes" fill="#fff">
          {[[x1, y1], [x2, y2]].map(([x, y], i) => {
            const s = r * 0.85;
            return (
              <path
                key={i}
                d={`M${x} ${y - s} Q${x + s * 0.18} ${y - s * 0.18} ${x + s} ${y} Q${x + s * 0.18} ${y + s * 0.18} ${x} ${y + s} Q${x - s * 0.18} ${y + s * 0.18} ${x - s} ${y} Q${x - s * 0.18} ${y - s * 0.18} ${x} ${y - s}Z`}
              />
            );
          })}
        </g>
      );
    } else if (f === "tear") {
      const tx = x1 - r * 0.9;
      const ty = y1 + r * 1.1;
      out.push(
        <path
          key={f}
          className="cf-tear"
          d={`M${tx} ${ty} Q${tx + 1.6} ${ty + 2.6} ${tx} ${ty + 3.4} Q${tx - 1.6} ${ty + 2.6} ${tx} ${ty}Z`}
          fill="#8FD3FF"
          stroke="#4AA8E0"
          strokeWidth="0.4"
        />
      );
    } else if (f.startsWith("brows-")) {
      const paths = [brow(f, [x1, y1], r, -1), brow(f, [x2, y2], r, 1)];
      out.push(
        <g key={f} className="cf-brows" fill="none" strokeLinecap="round">
          {/* light halo first, so brows read on dark fur (panther, penguin) */}
          {paths.map((p, i) => <path key={`h${i}`} d={p} stroke="#fff" strokeWidth={r * 0.95} opacity="0.85" />)}
          {paths.map((p, i) => <path key={`b${i}`} d={p} stroke={INK} strokeWidth={r * 0.5} />)}
        </g>
      );
    }
  }
  return <g className="cf-face">{out}</g>;
}

function Effect({ type }) {
  switch (type) {
    case "sparkle":
      return (
        <path className="cf-fx cf-twinkle" d="M60 -2 L61.8 3 L67 4.8 L61.8 6.6 L60 11.6 L58.2 6.6 L53 4.8 L58.2 3 Z" fill="#FFD54A" stroke="#E0A82E" strokeWidth="0.6" />
      );
    case "sparkles":
      return (
        <g className="cf-fx" fill="#FFD54A" stroke="#E0A82E" strokeWidth="0.5">
          <path className="cf-twinkle" d="M62 0 L63.4 4 L67.4 5.4 L63.4 6.8 L62 10.8 L60.6 6.8 L56.6 5.4 L60.6 4 Z" />
          <path className="cf-twinkle d2" d="M2 4 L3 7 L6 8 L3 9 L2 12 L1 9 L-2 8 L1 7 Z" />
          <path className="cf-twinkle d3" d="M68 26 L68.8 28.4 L71.2 29.2 L68.8 30 L68 32.4 L67.2 30 L64.8 29.2 L67.2 28.4 Z" />
        </g>
      );
    case "heart":
      return (
        <path className="cf-fx cf-float" d="M60 10 C60 6 55 6 55 9.6 C55 12.4 60 15 60 16.4 C60 15 65 12.4 65 9.6 C65 6 60 6 60 10 Z" fill="#FF7A95" stroke="#E0506F" strokeWidth="0.6" />
      );
    case "sweat":
      return <path className="cf-fx cf-drip" d="M58 0 Q62.5 6 62.5 9.5 Q62.5 13.5 58 13.5 Q53.5 13.5 53.5 9.5 Q53.5 6 58 0 Z" fill="#9ED8F7" stroke="#3E9BD6" strokeWidth="0.8" />;
    case "huff":
      return (
        <g className="cf-fx">
          <g className="cf-pop" stroke="#F0743E" strokeWidth="1.8" strokeLinecap="round" fill="none">
            <path d="M54 2 Q56.5 4.5 54 7" />
            <path d="M62 2 Q59.5 4.5 62 7" />
            <path d="M55 10 Q58 7.5 61 10" />
            <path d="M55 -1 Q58 1.5 61 -1" />
          </g>
          <g className="cf-puff" fill="#E6E9EF" stroke="#C4CAD4" strokeWidth="0.5">
            <circle cx="3" cy="14" r="3" />
            <circle cx="-1" cy="10" r="2" />
          </g>
        </g>
      );
    case "focus":
      return (
        <g className="cf-fx cf-flicker" stroke="#8B7AE8" strokeWidth="1.8" strokeLinecap="round">
          <path d="M58 6 L64 0" />
          <path d="M61 11 L69 9" />
          <path d="M54 3 L55.5 -4" />
        </g>
      );
    case "confetti":
      return (
        <g className="cf-fx cf-confetti">
          {[
            ["#FF6B6B", 4, 6, 20], ["#4FC3F7", 60, 4, -15], ["#FFD54A", 32, -5, 35], ["#4CC26B", -3, 26, 10],
            ["#C58AF2", 67, 24, -30], ["#FF9F43", 14, -3, 50], ["#4FC3F7", 50, -4, 5], ["#FF6B6B", 70, 44, 25],
          ].map(([c, x, y, rot], i) => (
            <rect key={i} className={`cf-bit b${i}`} x={x} y={y} width="3.2" height="2" rx="0.5" fill={c} transform={`rotate(${rot} ${x + 1.6} ${y + 1})`} />
          ))}
        </g>
      );
    default:
      return null;
  }
}

function Trait({ trait }) {
  if (!trait) return null;
  const c = trait.color;
  switch (trait.type) {
    case "tail":
      return (
        <g className="cf-trait cf-tail">
          <path d="M52 60 Q66 60 70 46 Q72 38 66 34" fill="none" stroke={c} strokeWidth="7" strokeLinecap="round" />
          {trait.stripes && (
            <g stroke={trait.tip === c ? "#00000055" : trait.tip} strokeWidth="2" strokeLinecap="round">
              <path d="M60 56.5 L62 61" />
              <path d="M67 49 L71.5 51" />
            </g>
          )}
          <path d="M69 39 Q70 35 66 34" fill="none" stroke={trait.tip} strokeWidth="7" strokeLinecap="round" />
        </g>
      );
    case "curl":
      return (
        <path className="cf-trait cf-tail" d="M52 60 Q66 62 68 50 Q70 40 62 40 Q57 41 60 46" fill="none" stroke={c} strokeWidth="3.4" strokeLinecap="round" />
      );
    case "wings":
      return (
        <g className="cf-trait" fill={c} stroke="#00000033" strokeWidth="0.6">
          <path className="cf-wing l" d="M4 44 Q-6 42 -6 52 Q-2 50 1 54 Q2 50 6 52 Z" />
          <path className="cf-wing r" d="M60 44 Q70 42 70 52 Q66 50 63 54 Q62 50 58 52 Z" />
        </g>
      );
    case "ears":
      return (
        <g className="cf-trait cf-earlines" fill="none" stroke={c} strokeWidth="1.6" strokeLinecap="round">
          <path d="M2 10 Q-2 14 2 18" />
          <path d="M-2 7 Q-8 14 -2 21" />
          <path d="M62 10 Q66 14 62 18" />
          <path d="M66 7 Q72 14 66 21" />
        </g>
      );
    case "sway":
      return (
        <g className="cf-trait cf-earlines" fill="none" stroke={c} strokeWidth="1.8" strokeLinecap="round">
          <path d="M-4 40 Q-1 44 -4 48 Q-7 52 -4 56" />
          <path d="M68 40 Q65 44 68 48 Q71 52 68 56" />
        </g>
      );
    case "flames":
      return (
        <g className="cf-trait cf-embers" fill={c}>
          <path className="cf-ember e1" d="M-2 40 Q-4 34 0 30 Q0 35 3 36 Q3 40 -2 40 Z" />
          <path className="cf-ember e2" d="M66 38 Q64 32 68 28 Q68 33 71 34 Q71 38 66 38 Z" />
          <path className="cf-ember e3" d="M8 4 Q7 0 10 -3 Q10 1 12 2 Q12 5 8 4 Z" fill="#FFC857" />
          <path className="cf-ember e4" d="M56 2 Q55 -2 58 -5 Q58 -1 60 0 Q60 3 56 2 Z" fill="#FFC857" />
        </g>
      );
    case "yuzu":
      return (
        <g className="cf-trait cf-bob">
          <circle cx="32" cy="-1" r="4.6" fill={c} stroke="#D68E13" strokeWidth="0.7" />
          <path d="M32 -5.6 Q34 -8.5 36.5 -7.5 Q34.5 -5.6 32 -5.6 Z" fill="#6BBF59" />
        </g>
      );
    case "bamboo":
      return (
        <g className="cf-trait cf-bob">
          <path d="M-2 70 L4 44" stroke={c} strokeWidth="3" strokeLinecap="round" />
          <path d="M1 57 L3.5 57.6" stroke="#3E8E45" strokeWidth="1" />
          <path d="M4 46 Q12 40 14 44 Q9 46 4 46 Z" fill={c} stroke="#3E8E45" strokeWidth="0.6" />
        </g>
      );
    case "bell":
      return (
        <g className="cf-trait cf-swing">
          <path d="M28 64 Q32 58 36 64 L37 67 L27 67 Z" fill={c} stroke="#C89520" strokeWidth="0.7" />
          <circle cx="32" cy="68" r="1.2" fill="#C89520" />
        </g>
      );
    default:
      return null;
  }
}

export default function CompanionFigure({ slug, mood = "neutral", size = 84, pulse = 0, className = "" }) {
  const { t } = useTranslation();
  const m = moodOf(mood);
  const look = MOODS[m];
  const sp = speciesOf(slug);
  const known = KNOWN.has(slug);
  const src = known ? `${import.meta.env.BASE_URL}animals/${slug}.png` : null;
  const label = t("companionReact.figureLabel", {
    animal: slug || "?",
    mood: t(`companionReact.mood.${m}`),
  });

  return (
    <div
      className={`cfig ${className}`}
      data-species={slug || "unknown"}
      data-motion={sp.motion}
      data-mood={m}
      data-body={look.body}
      data-trait-live={look.trait ? "1" : "0"}
      style={{ width: size, height: size, "--cf-glow": sp.glow || "transparent" }}
      role="img"
      aria-label={label}
    >
      <div className="cf-pose">
        {/* Re-keyed per reaction: the one-shot animation replays each time. */}
        <div className="cf-anim" key={pulse}>
          <svg viewBox="-8 -8 80 80" width={size} height={size} aria-hidden="true" focusable="false">
            {known && !FRONT_TRAITS.has(sp.trait?.type) && <Trait trait={sp.trait} />}
            {src ? (
              <image href={src} x="0" y="0" width="64" height="64" preserveAspectRatio="xMidYMid slice" />
            ) : (
              <>
                <circle cx="32" cy="32" r="31" fill="#EDEDF0" />
                <text x="32" y="41" textAnchor="middle" fontSize="26" fontWeight="700" fill="#9A9AA3">?</text>
              </>
            )}
            {known && FRONT_TRAITS.has(sp.trait?.type) && <Trait trait={sp.trait} />}
            {known && <Face features={look.face} eyes={sp.eyes} />}
            <Effect type={look.effect} />
          </svg>
        </div>
      </div>
    </div>
  );
}
