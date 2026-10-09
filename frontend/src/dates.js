// Dates and relative times in the interface language.
//
// Browsers ship no Tajik locale data: Intl.DateTimeFormat("tg") silently
// formats in the device's own locale, so a Tajik learner on a Russian
// Windows read "пятница, 9 октября" at the top of every page (and English on
// other devices). English, Russian and Chinese still go through Intl; Tajik
// is spelled out here for the few shapes the app uses.

export const DATE_LOCALE = { en: "en-US", ru: "ru-RU", tg: "tg-TJ", zh: "zh-CN" };

const TG_MONTHS = ["январ", "феврал", "март", "апрел", "май", "июн", "июл", "август", "сентябр", "октябр", "ноябр", "декабр"];
const TG_MONTHS_SHORT = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"];
const TG_WEEKDAYS = ["якшанбе", "душанбе", "сешанбе", "чоршанбе", "панҷшанбе", "ҷумъа", "шанбе"];

const pad = (n) => String(n).padStart(2, "0");

function base(lang) {
  return (lang || "en").split("-")[0];
}

function toDate(value) {
  if (value instanceof Date) return value;
  // The API returns naive UTC timestamps ("2026-10-09T07:39:49").
  if (typeof value === "string" && /T\d/.test(value) && !/[zZ]|[+-]\d\d:?\d\d$/.test(value)) return new Date(`${value}Z`);
  return new Date(value);
}

function tajik(d, opts) {
  const day = d.getDate();
  const year = d.getFullYear();
  const time = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
  if (opts.timeStyle) {
    return `${day} ${TG_MONTHS_SHORT[d.getMonth()]} ${year}, ${time}`;
  }
  if (opts.dateStyle === "long" || (opts.month === "long" && opts.year)) {
    return `${day} ${TG_MONTHS[d.getMonth()]} ${year}`;
  }
  if (opts.dateStyle === "medium" || (opts.month === "short" && opts.year)) {
    return `${day} ${TG_MONTHS_SHORT[d.getMonth()]} ${year}`;
  }
  if (opts.weekday && opts.month === "long") {
    return `${TG_WEEKDAYS[d.getDay()]}, ${day} ${TG_MONTHS[d.getMonth()]}`;
  }
  if (opts.month && opts.day) {
    return `${day} ${(opts.month === "long" ? TG_MONTHS : TG_MONTHS_SHORT)[d.getMonth()]}`;
  }
  if (opts.month === "short") return TG_MONTHS_SHORT[d.getMonth()];
  if (opts.month === "long") return TG_MONTHS[d.getMonth()];
  if (opts.weekday) return TG_WEEKDAYS[d.getDay()];
  return `${pad(day)}.${pad(d.getMonth() + 1)}.${year}`;
}

// formatDate(value, lang, Intl options). With no options: the short numeric
// date, like toLocaleDateString().
export function formatDate(value, lang, opts = {}) {
  const d = toDate(value);
  if (Number.isNaN(d.getTime())) return "";
  if (base(lang) === "tg") return tajik(d, opts);
  try {
    return new Intl.DateTimeFormat(DATE_LOCALE[base(lang)] || "en-US", opts).format(d);
  } catch {
    return d.toLocaleDateString();
  }
}

const TG_UNITS = { second: "сония", minute: "дақиқа", hour: "соат", day: "рӯз" };

// "5 minutes ago" / "yesterday" in the interface language.
export function timeAgo(value, lang) {
  if (!value) return "";
  const then = toDate(value).getTime();
  const secs = Math.round((then - Date.now()) / 1000);
  const abs = Math.abs(secs);
  const [amount, unit] = abs < 60 ? [secs, "second"]
    : abs < 3600 ? [Math.round(secs / 60), "minute"]
    : abs < 86400 ? [Math.round(secs / 3600), "hour"]
    : abs < 86400 * 30 ? [Math.round(secs / 86400), "day"]
    : [null, null];
  if (unit === null) return formatDate(then, lang, { month: "short", day: "numeric" });
  if (base(lang) === "tg") {
    if (unit === "second") return "ҳозир";
    if (unit === "day" && amount === -1) return "дирӯз";
    if (unit === "day" && amount === 1) return "фардо";
    const n = Math.abs(amount);
    return amount < 0 ? `${n} ${TG_UNITS[unit]} пеш` : `пас аз ${n} ${TG_UNITS[unit]}`;
  }
  return new Intl.RelativeTimeFormat(DATE_LOCALE[base(lang)] || "en-US", { numeric: "auto" }).format(amount, unit);
}
