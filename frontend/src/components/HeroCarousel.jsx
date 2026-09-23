import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";

// Four original, hand-drawn SVG scenes — not photography, so there is no
// licensing question: each is authored here as flat ink-wash-style
// silhouettes in the app's own Ink & Jade palette (brass gold / warm
// charcoal / jade), not a copy of any existing artwork or photo.

function SceneWall() {
  return (
    <svg viewBox="0 0 1600 700" preserveAspectRatio="xMidYMid slice" className="hero-scene-svg">
      <defs>
        <linearGradient id="wallSky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3a2410" />
          <stop offset="55%" stopColor="#1f1710" />
          <stop offset="100%" stopColor="#14110c" />
        </linearGradient>
        <radialGradient id="wallSun" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#f4c869" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#f4c869" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width="1600" height="700" fill="url(#wallSky)" />
      <circle cx="1180" cy="230" r="180" fill="url(#wallSun)" />
      <circle cx="1180" cy="230" r="70" fill="#f1c26b" opacity="0.85" />
      {/* Distant mountain range */}
      <path d="M0 430 L120 360 220 410 340 320 460 400 600 340 760 420 900 350 1050 410 1200 340 1360 420 1500 360 1600 410 1600 700 0 700 Z" fill="#241b10" opacity="0.55" />
      {/* The wall itself, winding along a ridge */}
      <path
        d="M0 520 C 80 500, 140 470, 220 480 C 300 490, 340 450, 420 440 C 500 430, 540 470, 620 460 C 700 450, 740 410, 820 400 C 900 390, 940 430, 1020 420 C 1100 410, 1140 380, 1220 390 C 1300 400, 1360 440, 1440 430 C 1500 423, 1550 440, 1600 430 L1600 700 0 700 Z"
        fill="#120d08"
      />
      {/* Watchtowers */}
      {[220, 420, 620, 820, 1020, 1220, 1440].map((x, i) => (
        <rect key={x} x={x - 14} y={[480, 440, 460, 400, 420, 390, 430][i] - 34} width="28" height="34" fill="#120d08" />
      ))}
    </svg>
  );
}

function SceneMountains() {
  return (
    <svg viewBox="0 0 1600 700" preserveAspectRatio="xMidYMid slice" className="hero-scene-svg">
      <defs>
        <linearGradient id="mtSky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#20180f" />
          <stop offset="100%" stopColor="#120e09" />
        </linearGradient>
      </defs>
      <rect width="1600" height="700" fill="url(#mtSky)" />
      <circle cx="300" cy="180" r="90" fill="#e8c373" opacity="0.18" />
      {/* Layered ink-wash peaks, back to front, each lighter->darker for depth */}
      <path d="M-50 480 200 260 420 440 620 220 900 460 1150 250 1400 430 1650 300 1650 700 -50 700 Z" fill="#c9974a" opacity="0.08" />
      <path d="M-50 540 250 340 500 500 780 300 1050 520 1320 330 1650 500 1650 700 -50 700 Z" fill="#c9974a" opacity="0.14" />
      <path d="M-50 600 300 420 560 560 850 400 1120 580 1400 430 1650 580 1650 700 -50 700 Z" fill="#20170d" opacity="0.9" />
      {/* A lone pine silhouette for scale */}
      <path d="M180 640 190 560 175 560 188 520 175 520 188 480 200 480 213 520 200 520 213 560 198 560 208 640Z" fill="#14100a" />
    </svg>
  );
}

function SceneLanterns() {
  const lanterns = [
    { x: 180, y: 90, r: 1 }, { x: 360, y: 160, r: 0.8 }, { x: 560, y: 70, r: 1.15 },
    { x: 760, y: 190, r: 0.9 }, { x: 980, y: 100, r: 1.05 }, { x: 1180, y: 170, r: 0.85 },
    { x: 1380, y: 90, r: 1.1 },
  ];
  return (
    <svg viewBox="0 0 1600 700" preserveAspectRatio="xMidYMid slice" className="hero-scene-svg">
      <defs>
        <linearGradient id="lanternSky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#241208" />
          <stop offset="100%" stopColor="#140c08" />
        </linearGradient>
        <radialGradient id="lanternGlow" cx="50%" cy="45%" r="55%">
          <stop offset="0%" stopColor="#ff8a3d" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#ff8a3d" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width="1600" height="700" fill="url(#lanternSky)" />
      <path d="M-50 560 300 480 650 540 1000 470 1350 550 1650 480 1650 700 -50 700 Z" fill="#0f0a06" />
      {lanterns.map((l, i) => (
        <g key={i} transform={`translate(${l.x} ${l.y}) scale(${l.r})`}>
          <line x1="0" y1="-70" x2="0" y2="-38" stroke="#3a2a16" strokeWidth="2" />
          <ellipse cx="0" cy="120" rx="90" ry="90" fill="url(#lanternGlow)" />
          <rect x="-6" y="-40" width="12" height="8" rx="2" fill="#caa15a" />
          <ellipse cx="0" cy="0" rx="34" ry="42" fill="#d3542c" stroke="#a83a1f" strokeWidth="2" />
          <ellipse cx="0" cy="0" rx="34" ry="42" fill="none" stroke="#f4c869" strokeWidth="1" opacity="0.5" />
          <rect x="-6" y="42" width="12" height="8" rx="2" fill="#caa15a" />
          <line x1="0" y1="50" x2="0" y2="68" stroke="#caa15a" strokeWidth="2" />
          <path d="M-6 66 L6 66 L0 80 Z" fill="#f4c869" />
        </g>
      ))}
    </svg>
  );
}

function ScenePagoda() {
  return (
    <svg viewBox="0 0 1600 700" preserveAspectRatio="xMidYMid slice" className="hero-scene-svg">
      <defs>
        <linearGradient id="pagodaSky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1a2420" />
          <stop offset="60%" stopColor="#161810" />
          <stop offset="100%" stopColor="#120f0a" />
        </linearGradient>
        <radialGradient id="moonGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#f3ecdb" stopOpacity="0.7" />
          <stop offset="100%" stopColor="#f3ecdb" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width="1600" height="700" fill="url(#pagodaSky)" />
      <circle cx="1250" cy="160" r="140" fill="url(#moonGlow)" />
      <circle cx="1250" cy="160" r="55" fill="#f3ecdb" opacity="0.9" />
      <path d="M-50 520 400 440 800 500 1200 430 1650 500 1650 700 -50 700 Z" fill="#0e1310" opacity="0.9" />
      {/* Pagoda: five stacked eaves narrowing upward */}
      <g transform="translate(330 640)">
        {[0, 1, 2, 3, 4].map((i) => {
          const w = 190 - i * 30;
          const y = -60 - i * 78;
          return (
            <g key={i}>
              <path d={`M${-w / 2} ${y} L0 ${y - 34} L${w / 2} ${y} L${w / 2 - 14} ${y + 14} L${-w / 2 + 14} ${y + 14} Z`} fill="#0c0f0b" />
              <rect x={-14} y={y + 14} width="28" height="44" fill="#0c0f0b" />
            </g>
          );
        })}
        <line x1="0" y1="-450" x2="0" y2="-370" stroke="#0c0f0b" strokeWidth="4" />
      </g>
    </svg>
  );
}

const SCENES = [SceneWall, SceneMountains, SceneLanterns, ScenePagoda];
const INTERVAL_MS = 6500;

// Smooth crossfade carousel behind the landing hero — pure decoration, so
// it fully respects prefers-reduced-motion by just holding the first scene
// static instead of cycling.
export default function HeroCarousel() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const reduceMotion = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) return undefined;
    const id = setInterval(() => setIndex((i) => (i + 1) % SCENES.length), INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  const Scene = SCENES[index];

  return (
    <div className="hero-carousel" aria-hidden="true">
      <AnimatePresence mode="sync">
        <motion.div
          key={index}
          className="hero-scene"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 1.4, ease: "easeInOut" }}
        >
          <Scene />
        </motion.div>
      </AnimatePresence>
      <div className="hero-carousel-veil" />
    </div>
  );
}
