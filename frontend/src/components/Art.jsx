import { memo, useId } from "react";
import { PLACE_ART, building } from "./art/places.jsx";
import { CASE_ART, FILE_ART, NET_ART, PRON_ART, caseFallback, fileFallback, netFallback, pronFallback } from "./art/objects.jsx";

// The illustrations of ChineseVerse: the places of Живой китайский and the
// things learners meet in them (an Internet post, a case file, a
// pronunciation lesson), painted from one kit (components/art/kit.jsx) in
// one palette (--art-* in index.css). The API keeps sending its `icon`
// emoji for old clients; the UI draws these instead, keyed by the same
// stable keys the API already uses (place key, scene slug, sound place,
// item slug, case key, lesson key) -- so no contract changes, and new
// content gets a family fallback rather than an emoji.
//
//   <Art name={placeArt("bank")} size={56} />          a tile in a card
//   <Art name={placeArt(p.key)} shape="round" ... />    a disc (the map)

// Real Chinese scenes (services/real_life_content.py) and the Sound World
// places (services/sound_world.py) happen at places of the map
// (world_places.py: scene=..., sound=...); they show that place.
const SCENE_PLACE = {
  university: "university", "convenience-store": "shop", "job-interview": "office", hospital: "hospital",
  "train-station": "train_station", airport: "airport", hotel: "hotel", restaurant: "restaurant",
  travel: "old_town", shopping: "shopping_district",
};
const SOUND_PLACE = {
  night_market: "food_street", restaurant: "restaurant", train_station: "train_station", school: "university",
  street: "street", airport: "airport", shopping: "shopping_district",
};
// Chinese Internet items (services/internet_content.py) are drawn by the
// kind of page they are; the panel on the map only knows an item's slug.
const NET_KIND = {
  "metro-line": "news", "hiking-post": "social", "dumpling-comments": "comments", "thermos-cup": "product",
  "hotpot-review": "review", "water-notice": "notice", "park-info": "travel", "supermarket-deals": "shopping",
  "class-group-chat": "messages", "dinner-chat": "chat",
};
const FILE_PREFIX = "file:"; // services/detective.py FILE_PREFIX: a played case file's ctx.case

export const placeArt = (key) => `place.${key}`;
export const sceneArt = (slug) => `place.${SCENE_PLACE[slug] || slug}`;
export const soundArt = (env) => `place.${SOUND_PLACE[env] || env}`;
export const netArt = (slugOrKind) => `net.${NET_KIND[slugOrKind] || slugOrKind}`;
export const caseArt = (key) => (key?.startsWith(FILE_PREFIX) ? `file.${key.slice(FILE_PREFIX.length)}` : `case.${key}`);
export const fileArt = (slug) => `file.${slug}`;
export const pronArt = (key) => `pron.${key}`;

const FAMILIES = {
  place: [PLACE_ART, building],
  net: [NET_ART, netFallback],
  case: [CASE_ART, caseFallback],
  file: [FILE_ART, fileFallback],
  pron: [PRON_ART, pronFallback],
};

function resolve(name = "") {
  const dot = name.indexOf(".");
  const [table, fallback] = FAMILIES[name.slice(0, dot)] || FAMILIES.place;
  return table[name.slice(dot + 1)] || fallback;
}

// `shape`: "tile" (rounded square, cards and rows) or "round" (the map's
// discs). `detail` defaults from the size; inside the map's SVG the size is
// in canvas units, so the map says itself whether details are readable.
// x / y place it inside a parent <svg>; outside one they are omitted.
function Art({ name, size = 56, shape = "tile", detail, flat = false, title, className = "", x, y }) {
  const id = `cvart${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  const Draw = resolve(name);
  const small = detail === undefined ? size <= 32 : !detail;
  return (
    <svg
      viewBox="0 0 64 64" width={size} height={size} x={x} y={y}
      className={`cv-art is-${shape}${small ? " is-sm" : ""}${flat ? " is-flat" : ""}${className ? ` ${className}` : ""}`}
      role={title ? "img" : undefined} aria-label={title} aria-hidden={title ? undefined : true} focusable="false"
    >
      <defs>
        <clipPath id={id}>
          {shape === "round" ? <circle cx="32" cy="32" r="32" /> : <rect width="64" height="64" rx="14" />}
        </clipPath>
      </defs>
      <g clipPath={`url(#${id})`}>
        <Draw />
      </g>
      {shape === "round"
        ? <circle className="rim" cx="32" cy="32" r="31.4" />
        : <rect className="rim" x="0.6" y="0.6" width="62.8" height="62.8" rx="13.4" />}
    </svg>
  );
}

// The map re-renders on every frame of a pan; the paintings never change
// with it, so they skip re-rendering unless their own props do.
export default memo(Art);
