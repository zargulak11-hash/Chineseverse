// How each companion SPECIES expresses an emotion, and what each MOOD looks
// like on a face. The moods come from the backend
// (app/services/companion_reaction.py MOODS); every mood there must have an
// entry in MOODS below, and every companion slug (app/seed_data.py ANIMALS)
// an entry in SPECIES -- tests/companion_reaction_test.py checks both.
//
// The portraits in public/animals/ are flat, front-facing illustrations, so
// an emotion is drawn ON the real portrait instead of swapping it for a
// generic character:
//   - `eyes` are the two pupil centres measured on each 256px portrait and
//     scaled to the 64-unit viewBox, so brows, blush, glints and tears land
//     on THAT animal's face;
//   - `motion` picks the species' body language (a fox tilts and wags, a
//     rabbit hops, a snake sways, a wolf stands tall, a phoenix rises and
//     glows...), which CSS applies to every mood;
//   - `trait` is the species' own expressive part drawn beside the portrait
//     (tail, wings, ears, flames...) that moves with positive moods.

export const SPECIES = {
  fox:         { motion: "playful",  eyes: [[22, 40], [42, 40]], trait: { type: "tail", color: "#F08A3C", tip: "#FFF6EC" } },
  wolf:        { motion: "bold",     eyes: [[23, 40], [42, 40]], trait: { type: "tail", color: "#7D8796", tip: "#E9EDF3" } },
  snake:       { motion: "slither",  eyes: [[20.5, 32], [44.5, 32]], trait: { type: "sway", color: "#5FA850" } },
  cat:         { motion: "calm",     eyes: [[22, 39.5], [41.5, 39.5]], trait: { type: "tail", color: "#8A8F99", tip: "#8A8F99" } },
  dog:         { motion: "playful",  eyes: [[23, 34], [42.5, 34]], trait: { type: "tail", color: "#D9954E", tip: "#FFF3E3" } },
  tiger:       { motion: "bold",     eyes: [[20.5, 39], [43, 39]], trait: { type: "tail", color: "#F2862E", tip: "#3A2618", stripes: true } },
  rabbit:      { motion: "hopper",   eyes: [[23, 44.5], [41, 44.5]], trait: { type: "ears", color: "#F4A7B4" } },
  bird:        { motion: "flutter",  eyes: [[21, 40], [42.5, 40]], trait: { type: "wings", color: "#3F7FD1" } },
  capybara:    { motion: "calm",     eyes: [[20, 36], [43, 36]], trait: { type: "yuzu", color: "#F7B733" } },
  panther:     { motion: "bold",     eyes: [[21.5, 39], [43, 39]], trait: { type: "tail", color: "#2B2B33", tip: "#2B2B33" } },
  sheep:       { motion: "calm",     eyes: [[24, 39.5], [41, 39.5]], trait: { type: "ears", color: "#F2B8B0" } },
  panda:       { motion: "cuddly",   eyes: [[21.5, 39], [41, 39]], trait: { type: "bamboo", color: "#5DBB63" } },
  "red-panda": { motion: "playful",  eyes: [[21.5, 41], [41, 41]], trait: { type: "tail", color: "#D2622A", tip: "#6B3A22", stripes: true } },
  phoenix:     { motion: "majestic", eyes: [[23, 42], [40, 42]], trait: { type: "flames", color: "#FF8A1E" }, glow: "#FFB347" },
  monkey:      { motion: "playful",  eyes: [[23.5, 39], [40, 39]], trait: { type: "curl", color: "#9A6238" } },
  koala:       { motion: "calm",     eyes: [[24, 37.5], [41.5, 37.5]], trait: { type: "ears", color: "#B8BEC7" } },
  elephant:    { motion: "cuddly",   eyes: [[23, 35], [41, 35]], trait: { type: "ears", color: "#7FA3D6" } },
  cow:         { motion: "cuddly",   eyes: [[24, 32.5], [40, 32.5]], trait: { type: "bell", color: "#F2C14E" } },
  penguin:     { motion: "cuddly",   eyes: [[21, 35], [41.5, 35]], trait: { type: "wings", color: "#2F3A4E" } },
  owl:         { motion: "calm",     eyes: [[23, 35.5], [40.5, 35.5]], trait: { type: "wings", color: "#8B5A34" } },
};

// face:   overlays drawn on the portrait at the species' eyes
// effect: a small scene element around the animal
// body:   the CSS animation family (species motion decides the exact move)
// trait:  whether the species trait (tail, wings...) animates
export const MOODS = {
  neutral:     { face: [], effect: null, body: "idle", trait: false },
  happy:       { face: ["blush", "glint"], effect: null, body: "bounce", trait: true },
  excited:     { face: ["blush", "star-eyes"], effect: "sparkles", body: "jump", trait: true },
  proud:       { face: ["brows-proud", "blush", "glint"], effect: "sparkle", body: "puff", trait: true },
  encouraging: { face: ["brows-soft", "blush"], effect: "heart", body: "nod", trait: true },
  worried:     { face: ["brows-worried"], effect: "sweat", body: "droop", trait: false },
  sad:         { face: ["brows-worried", "tear"], effect: null, body: "sag", trait: false },
  frustrated:  { face: ["brows-cross"], effect: "huff", body: "huff", trait: false },
  serious:     { face: ["brows-focus"], effect: "focus", body: "lean", trait: false },
  celebrating: { face: ["blush", "star-eyes"], effect: "confetti", body: "party", trait: true },
};

export function speciesOf(slug) {
  return SPECIES[slug] || { motion: "calm", eyes: [[22, 39], [42, 39]], trait: null };
}

export function moodOf(mood) {
  return MOODS[mood] ? mood : "neutral";
}
