// Shared Anime.js (v4) helpers — one place for the reduced-motion guard and
// the easing vocabulary reused across pages, instead of bespoke configs
// scattered per component.
export function prefersReducedMotion() {
  return typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

// A springy "pop" used for card entrances and celebratory moments — real
// elastic overshoot, not a linear/eased fade.
export const ELASTIC_POP = "outElastic(1, .6)";
export const ELASTIC_SOFT = "outElastic(1, .8)";
export const OUT_EXPO = "outExpo";
