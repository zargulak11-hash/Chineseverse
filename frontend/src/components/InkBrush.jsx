// Thin, abstract ink-brush strokes used as ambient background texture on
// hero sections (landing, dashboard). Hand-drawn bezier paths, not a
// literal illustration — a few confident lines, the way a few strokes of
// a brush suggest a mountain or a branch in ink-wash painting (水墨畫).
// Purely decorative: aria-hidden, and never the only carrier of information.

const VARIANTS = {
  hero: (
    <svg width="900" height="560" viewBox="0 0 900 560" fill="none" style={{ top: "-8%", right: "-10%" }}>
      <path
        d="M120 480 C 260 420, 300 280, 480 260 C 610 244, 660 140, 820 90"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        opacity="0.5"
      />
      <path
        d="M60 520 C 200 500, 250 430, 420 420"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        opacity="0.3"
      />
      <path
        d="M700 40 C 760 70, 800 130, 860 150"
        stroke="currentColor"
        strokeWidth="5"
        strokeLinecap="round"
        opacity="0.4"
      />
      <circle cx="826" cy="86" r="5.5" fill="currentColor" opacity="0.55" />
    </svg>
  ),
  corner: (
    <svg width="520" height="520" viewBox="0 0 520 520" fill="none" style={{ bottom: "-14%", left: "-12%" }}>
      <path
        d="M20 500 C 140 460, 180 340, 320 320 C 400 310, 440 240, 500 200"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        opacity="0.4"
      />
      <path d="M40 420 C 120 410, 160 360, 260 350" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.28" />
    </svg>
  ),
};

export default function InkBrush({ variant = "hero", color = "var(--text-faint)" }) {
  return (
    <div className="ink-brush" aria-hidden="true" style={{ color }}>
      {VARIANTS[variant] || VARIANTS.hero}
    </div>
  );
}
