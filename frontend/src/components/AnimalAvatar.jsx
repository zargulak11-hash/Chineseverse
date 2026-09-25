// ChineseVerse companion portraits. Each of the 20 companions is a hand-picked
// illustration in frontend/public/animals/<slug>.png (round, with its own
// pastel background baked in). The roster itself lives in the backend
// (app/seed_data.py ANIMALS) — ANIMAL_SLUGS below must list exactly the same
// slugs, one per image file.
//
// `state` (optional, defaults to "idle") draws a small accessory overlay
// (sparkle, checkmark, question mark...) on top of the SAME portrait to cover
// the app's interaction states (happy, excited, thinking, confused, correct,
// wrong, celebrating, encouraging, speaking, listening) without needing a
// separate illustration per animal per state.

export const ANIMAL_SLUGS = [
  "fox", "wolf", "snake", "cat", "dog",
  "tiger", "rabbit", "bird", "capybara", "panther",
  "sheep", "panda", "red-panda", "phoenix", "monkey",
  "koala", "elephant", "cow", "penguin", "owl",
];

const KNOWN = new Set(ANIMAL_SLUGS);

// Small icon drawn near the top-right of the frame to carry the state's
// meaning — reusable across every animal, independent of species.
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

const STATE_ACCESSORY = {
  idle: "none",
  happy: "none",
  excited: "sparkle",
  thinking: "thoughtDots",
  confused: "questionMark",
  correct: "checkmark",
  wrong: "sweatDrop",
  celebrating: "confetti",
  encouraging: "none",
  speaking: "soundWaves",
  listening: "earLines",
};

export default function AnimalAvatar({ slug, size = 48, className = "", state = "idle" }) {
  const accessory = STATE_ACCESSORY[state] || "none";
  const src = KNOWN.has(slug) ? `${import.meta.env.BASE_URL}animals/${slug}.png` : null;

  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      className={`animal-avatar ${className}`}
      role="img"
      aria-label={`${slug} avatar, ${state}`}
    >
      {src ? (
        <image href={src} x="0" y="0" width="64" height="64" preserveAspectRatio="xMidYMid slice" />
      ) : (
        // Unknown / not-yet-chosen companion: neutral placeholder circle.
        <>
          <circle cx="32" cy="32" r="31" fill="#EDEDF0" />
          <text x="32" y="41" textAnchor="middle" fontSize="26" fontWeight="700" fill="#9A9AA3">?</text>
        </>
      )}
      <Accessory type={accessory} />
    </svg>
  );
}
