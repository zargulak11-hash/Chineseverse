// A single, consistent line-icon set (24x24, 1.8px stroke, round caps) used
// everywhere in place of the old mix of emoji — one visual language instead
// of whatever glyphs happened to be typed into each page. Hand-authored
// instead of a new dependency: this is a small, fixed vocabulary, not a
// general-purpose icon library the app needs to pull arbitrary names from.

const PATHS = {
  home: "M4 11.5 12 4l8 7.5 M6 10v9a1 1 0 0 0 1 1h4v-6h2v6h4a1 1 0 0 0 1-1v-9",
  world: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM3.6 9h16.8M3.6 15h16.8M12 3a13 13 0 0 1 0 18M12 3a13 13 0 0 0 0 18",
  book: "M4 19.5V5a2 2 0 0 1 2-2h13v15H6a2 2 0 0 0 0 4h13 M4 19.5A2 2 0 0 1 6 18",
  type: "M5 6h14M12 6v13M9 19h6",
  dna: "M7 3c0 6 10 12 10 18M17 3c0 6-10 12-10 18M6 8h12M6 16h12",
  trending: "M4 16l6-6 4 4 6-8M14 6h6v6",
  target: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z",
  flag: "M6 21V4M6 4h12l-3 4 3 4H6",
  swords: "m14.5 17.5 3 3L21 17l-3-3M3 21l7-7M14.5 6.5l3-3L21 7l-3 3M3 3l7 7M9 15l-2 2-2-2 2-2Z",
  heart: "M12 20s-7-4.4-9.5-9A5.5 5.5 0 0 1 12 5.5 5.5 5.5 0 0 1 21.5 11c-2.5 4.6-9.5 9-9.5 9Z",
  teach: "M2 8l10-4 10 4-10 4-10-4Zm4 2.4V16c0 1.7 2.7 3 6 3s6-1.3 6-3v-5.6",
  award: "M12 15a5 5 0 1 0 0-10 5 5 0 0 0 0 10ZM8.2 14 7 21l5-2 5 2-1.2-7",
  alert: "M12 3 2 20h20L12 3ZM12 10v4M12 17h.01",
  chart: "M5 21V10M12 21V4M19 21v-7",
  user: "M12 12a4.5 4.5 0 1 0 0-9 4.5 4.5 0 0 0 0 9ZM4.5 21a7.5 7.5 0 0 1 15 0",
  settings:
    "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z M19.4 13a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V19a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 17.09a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 13 1.65 1.65 0 0 0 3 12h-.09a2 2 0 1 1 0-4H3a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68 1.65 1.65 0 0 0 10 3V2.91a2 2 0 1 1 4 0V3c0 .68.4 1.29 1 1.51.62.24 1.32.13 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.32 9c.24.62.83 1 1.51 1H21a2 2 0 1 1 0 4h-.09c-.68 0-1.27.4-1.51 1Z",
  logout: "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9",
  flame: "M12 22c4 0 7-2.7 7-6.8 0-3-1.8-4.7-3-6.6-.3 1.4-1 2.4-2 3 .3-3-1-5.7-3.5-7.6.3 2 0 3.6-1.3 5.2C7.8 11 7 12.8 7 15.2 7 19.3 8 22 12 22Z",
  coin: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM9.5 15.5c0 1 1 1.8 2.5 1.8s2.5-.7 2.5-1.7c0-2.6-5-1.2-5-3.8 0-1 1-1.7 2.5-1.7s2.5.7 2.5 1.7M12 6.5v1.2M12 16.2v1.3",
  check: "M4 12.5 9.5 18 20 6",
  x: "M6 6l12 12M18 6 6 18",
  chevronRight: "M9 6l6 6-6 6",
  chevronLeft: "M15 6l-6 6 6 6",
  mic: "M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3ZM6 11v1a6 6 0 0 0 12 0v-1M12 18v3",
  play: "M7 4.5v15l13-7.5-13-7.5Z",
  arrowRight: "M5 12h14M13 6l6 6-6 6",
  arrowLeft: "M19 12H5M11 18l-6-6 6-6",
  search: "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16ZM21 21l-4.3-4.3",
  sparkles: "M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18",
  mapPin: "M12 21s7-6.3 7-12a7 7 0 1 0-14 0c0 5.7 7 12 7 12ZM12 12a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z",
  clock: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM12 7v5l3.5 2",
  paw: "M8.5 7.5a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM19.5 7.5a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM5.5 13a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM22.5 13a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM12 22c3 0 5.5-1.8 5.5-4.7 0-2.6-2-4.4-5.5-4.4S6.5 14.7 6.5 17.3C6.5 20.2 9 22 12 22Z",
  lock: "M6 11V8a6 6 0 1 1 12 0v3M5 11h14v9a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-9Z",
  chat: "M4 4h16v11H8l-4 4V4Z",
  trophy: "M8 4h8v4a4 4 0 0 1-8 0V4ZM6 4H4v2a3 3 0 0 0 3 3M18 4h2v2a3 3 0 0 1-3 3M10 15v3H8v2h8v-2h-2v-3",
  ear: "M6 10a6 6 0 1 1 8 5.6c-.7.3-1 1-1 1.7V19a2 2 0 1 1-4 0M9 10a3 3 0 0 1 3-3",
  pen: "M4 20h4L18.5 9.5a2.1 2.1 0 0 0-3-3L5 16v4Z M14 6l4 4",
  eye: "M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7ZM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z",
  star: "M12 2.5l2.8 6.2 6.7.6-5.1 4.5 1.6 6.6-6-3.6-6 3.6 1.6-6.6-5.1-4.5 6.7-.6L12 2.5Z",
  stop: "M6 6h12v12H6Z",
  droplet: "M12 2.5s7 8 7 12.5a7 7 0 1 1-14 0c0-4.5 7-12.5 7-12.5Z",
  seal: "M12 3 4 7v10l8 4 8-4V7l-8-4Z M12 8v8M8 12h8",
  bell: "M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0",
  menu: "M4 7h16M4 12h16M4 17h16",
};

export default function Icon({ name, size = 18, strokeWidth = 1.8, className = "", style }) {
  const d = PATHS[name];
  if (!d) return null;
  return (
    <svg
      className={`icon ${className}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      style={style}
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  );
}
