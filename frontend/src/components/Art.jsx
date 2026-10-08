import { memo, useId } from "react";
import { BOOK_ART, bookFallback } from "./art/books.jsx";
import { PLACE_ART, building } from "./art/places.jsx";
import { CASE_ART, FILE_ART, NET_ART, PRON_ART, caseFallback, fileFallback, netFallback, pronFallback } from "./art/objects.jsx";

// The illustrations of ChineseVerse: the places of Живой китайский, the
// things learners meet in them (an Internet post, a case file, a
// pronunciation lesson) and the covers of the Chinese Stories books, painted from one kit (components/art/kit.jsx) in
// one palette (--art-* in index.css). The API keeps sending its `icon`
// emoji for old clients; the UI draws these instead, keyed by the same
// stable keys the API already uses (place key, scene slug, sound place,
// item slug, case key, lesson key, book slug) -- so no contract changes, and new
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
  travel: "old_town", shopping: "shopping_district", pharmacy: "pharmacy", taxi: "street", bank: "bank",
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

// The cover painting of each Chinese Stories book (seed_content/books), by
// slug: the story's own motif, or the place it happens in when we already
// paint that place. A new book takes its topic's painting until it is added
// here (art.test.js lists any book without one).
const BOOK_COVER = {
  // HSK 1
  "a-day-off-sick": "book.sick_day", "a-new-friend": "book.friends", "a-rainy-sunday": "book.rain",
  "at-the-restaurant": "place.restaurant", "dad-makes-dinner": "book.cooking", "grandpas-birthday": "book.cake",
  "movie-night": "place.cinema", "mum-at-the-hospital": "place.hospital", "my-chinese-name": "book.name_seal",
  "my-day": "book.morning", "my-family": "place.home", "my-new-room": "book.bedroom",
  "new-year-dumplings": "book.dumplings", "sunday-market": "place.market", "the-ball-game": "book.basketball",
  "the-big-watermelon": "book.watermelon", "the-library-card": "place.library", "the-lost-phone": "book.lost_phone",
  "the-taxi-ride": "book.taxi", "the-wrong-classroom": "book.classroom", "two-train-tickets": "place.train_station",
  "up-the-mountain": "book.mountain", "where-is-huahua": "book.cat", "who-ate-the-bread": "book.bread",
  "xiaohei-the-dog": "book.dog",
  // HSK 2
  "a-day-at-the-zoo": "book.panda", "a-letter-from-grandpa": "book.letter", "birthday-gift": "book.gift",
  "grandmas-garden": "book.garden", "grandmas-new-phone": "net.messages", "learning-to-swim": "book.pool",
  "moving-to-the-city": "place.street", "rainy-day": "book.rain", "seeing-the-sea": "book.sea",
  "the-bicycle": "book.bicycle", "the-big-exam": "book.exam", "the-coffee-shop": "place.cafe",
  "the-first-snow": "book.snow", "the-football-match": "book.football", "the-new-neighbour": "book.neighbour",
  "the-night-train": "place.train_station", "the-old-photo": "book.old_photo", "the-red-envelope": "book.red_envelope",
  "the-shopping-list": "place.shop", "the-umbrella": "book.rain", "the-weekend-job": "place.cafe",
  "the-wrong-bus": "place.bus_station", "the-wrong-seat": "place.cinema", "two-wang-dalis": "book.friends",
  "where-is-mimi": "book.cat",
  // HSK 3
  "a-gift-for-mum": "book.gift", "a-weekend-in-xian": "place.temple", "first-metro-ride": "place.metro",
  "grandpa-and-the-opera": "book.opera", "grandpas-watch": "book.watch", "language-partner": "book.friends",
  "learning-to-drive": "book.driving", "letters-to-dushanbe": "book.letter", "running-every-morning": "book.running",
  "stuck-in-the-lift": "book.lift", "the-cooking-class": "book.cooking", "the-lost-dog-poster": "book.dog",
  "the-lost-passport": "place.passport_office", "the-missing-cake": "book.cake", "the-mountain-school": "book.mountain_school",
  "the-new-manager": "place.office", "the-night-market": "place.food_street", "the-old-bookshop": "place.bookstore",
  "the-power-cut": "book.candle", "the-school-show": "book.stage", "the-science-project": "book.plant_music",
  "the-station-volunteer": "place.train_station", "the-tea-mountain": "book.tea_hills", "the-wrong-suitcase": "book.suitcase",
  "which-day-is-the-exam": "book.calendar",
  // HSK 4
  "a-new-city": "place.street", "a-week-without-phones": "book.no_phone", "grandma-and-the-robot": "book.robot",
  "lost-in-the-fog": "book.fog", "sorting-the-rubbish": "book.recycling", "the-calligraphy-brush": "place.calligraphy",
  "the-caves-of-dunhuang": "book.dunhuang", "the-debate": "book.debate", "the-delivery-rider": "book.scooter",
  "the-empty-frame": "book.empty_frame", "the-first-salary": "book.coins", "the-honest-driver": "book.taxi",
  "the-interpreter": "pron.dialogues", "the-interview": "place.office", "the-mid-autumn-call": "book.mooncake",
  "the-noodle-shop-online": "place.restaurant", "the-old-hutong": "place.hutong", "the-panda-keeper": "book.panda",
  "the-reunion": "book.graduation", "the-rice-harvest": "book.rice_field", "the-roommates": "book.bedroom",
  "the-voice-message": "net.chat", "the-wedding-speech": "book.wedding", "two-job-offers": "place.office",
  "volunteers-by-the-river": "place.riverside",
  // HSK 5-6
  "letters-to-my-future-self": "book.letter", "old-teahouse": "place.tea_house", "slowing-down": "book.tea_cup",
  "the-story-of-paper": "book.scroll", "the-village-teacher": "book.mountain_school",
  "forty-years-of-a-street": "place.hutong", "ink-and-patience": "place.calligraphy", "the-missing-painting": "book.empty_frame",
  "the-robot-who-spoke-dialect": "book.robot", "zheng-he": "book.voyage",
  // HSK 7-9
  "night-courier": "book.scooter", "the-hospital-interpreter": "place.hospital", "waiting-for-the-snow-leopard": "book.snow_leopard",
  "last-bookshop": "place.bookstore", "the-edges-of-language": "book.old_key", "the-last-train": "place.metro",
  "colours-of-dunhuang": "book.dunhuang", "echoes-of-the-silk-road": "book.camel", "the-shape-of-time": "book.hourglass",
};
// The stories.topic values (services/books.py) for a book not listed above.
const TOPIC_COVER = {
  daily: "book.morning", friends: "book.friends", nature: "book.mountain", food: "book.cooking", family: "place.home",
  work: "place.office", mystery: "book.empty_frame", culture: "place.calligraphy", society: "place.street",
  city: "place.street", school: "book.classroom", travel: "book.suitcase", relationships: "book.letter",
  history: "book.scroll", humor: "book.watermelon", science: "book.robot", shopping: "place.market",
};

export const placeArt = (key) => `place.${key}`;
export const sceneArt = (slug) => `place.${SCENE_PLACE[slug] || slug}`;
export const soundArt = (env) => `place.${SOUND_PLACE[env] || env}`;
export const netArt = (slugOrKind) => `net.${NET_KIND[slugOrKind] || slugOrKind}`;
export const caseArt = (key) => (key?.startsWith(FILE_PREFIX) ? `file.${key.slice(FILE_PREFIX.length)}` : `case.${key}`);
export const fileArt = (slug) => `file.${slug}`;
export const pronArt = (key) => `pron.${key}`;
export const bookArt = (slug, topic) => BOOK_COVER[slug] || TOPIC_COVER[topic] || "book.reading";

const FAMILIES = {
  place: [PLACE_ART, building],
  net: [NET_ART, netFallback],
  case: [CASE_ART, caseFallback],
  file: [FILE_ART, fileFallback],
  pron: [PRON_ART, pronFallback],
  book: [BOOK_ART, bookFallback],
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
