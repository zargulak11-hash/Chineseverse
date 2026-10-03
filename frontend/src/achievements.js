// Achievement text and icons, shared by the Achievements page, the unlock
// note, the Dashboard and the Passport/Companion timelines. Text is keyed by
// the achievement's code (achievements.items.<code>.*, in all four
// locales); the backend's own title/description is only the fallback, for a
// code the UI doesn't know yet.

export const CATEGORY_ICON = {
  start: "sparkles",
  places: "mapPin",
  words: "type",
  characters: "pen",
  listening: "ear",
  speaking: "mic",
  reading: "book",
  stories: "bookOpen",
  hsk: "trending",
  review: "clock",
  habit: "flame",
  companion: "paw",
  world: "world",
};

export function achievementIcon(a) {
  return CATEGORY_ICON[a?.category] || "award";
}

export function achievementTitle(t, code, fallback = "") {
  return code ? t(`achievements.items.${code}.title`, { defaultValue: fallback }) : fallback;
}

export function achievementHow(t, a) {
  return t(`achievements.items.${a.code}.how`, { defaultValue: a.description || "" });
}

export function achievementDone(t, a) {
  return t(`achievements.items.${a.code}.done`, { defaultValue: a.description || "" });
}

// "7/10" or "64%/80%" — the numbers the backend counted, never estimated.
export function progressText(a) {
  return a.unit === "percent" ? `${a.progress}% / ${a.target}%` : `${a.progress}/${a.target}`;
}

// What is still missing, in plain words. A one-step achievement needs no
// count: its "how" already says the single thing to do.
export function remainingText(t, a) {
  if (a.unlocked || a.target <= 1) return "";
  if (a.unit === "percent") return t("achievements.leftPercent", { value: a.progress, target: a.target });
  return t(`achievements.left.${a.unit}`, { count: a.target - a.progress, defaultValue: "" });
}

export function ratio(a) {
  return a.target ? Math.min(1, a.progress / a.target) : 0;
}
