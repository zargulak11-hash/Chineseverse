// Framer Motion is now reserved for the handful of spots where a real
// React component-level transition fits better than an imperative Anime.js
// call — specifically AnimatePresence-driven mount/unmount of list items
// (chat bubbles, feedback cards) where React itself decides when the DOM
// node appears/disappears. Page transitions, staggered grid/card
// entrances, celebratory moments, buttons and the sidebar indicator have
// all moved to Anime.js (see anime.js, buttonFx.js, and the per-page
// useEffect-driven animations) for real spring/elastic physics.
const snapSpring = { type: "spring", stiffness: 420, damping: 22 };

export const popIn = {
  initial: { opacity: 0, scale: 0.85 },
  animate: { opacity: 1, scale: 1, transition: snapSpring },
  exit: { opacity: 0, scale: 0.9, transition: { duration: 0.15 } },
};
