import { describe, expect, it } from "vitest";
import { formatDate, timeAgo } from "./dates.js";

describe("dates in Tajik", () => {
  // Browsers have no Tajik locale data; Intl would format these in the
  // device's language (a Russian "пятница, 9 октября" on a Tajik page).
  const friday = new Date(2026, 9, 9, 14, 5);

  it("spells weekdays and months in Tajik", () => {
    expect(formatDate(friday, "tg", { weekday: "long", month: "long", day: "numeric" })).toBe("ҷумъа, 9 октябр");
    expect(formatDate(friday, "tg", { month: "short", day: "numeric" })).toBe("9 окт");
    expect(formatDate(friday, "tg", { dateStyle: "medium" })).toBe("9 окт 2026");
    expect(formatDate(friday, "tg")).toBe("09.10.2026");
  });

  it("says how long ago in Tajik", () => {
    expect(timeAgo(new Date(Date.now() - 5 * 60 * 1000), "tg")).toBe("5 дақиқа пеш");
    expect(timeAgo(new Date(Date.now() - 26 * 3600 * 1000), "tg")).toBe("дирӯз");
  });

  it("still uses Intl for the other languages", () => {
    expect(formatDate(friday, "ru", { month: "long", day: "numeric" })).toBe("9 октября");
    expect(formatDate(friday, "en", { month: "short", day: "numeric" })).toBe("Oct 9");
  });

  it("reads the API's naive UTC timestamps as UTC", () => {
    expect(formatDate("2026-10-09T23:30:00", "en", { timeZone: "UTC", day: "numeric" })).toBe("9");
  });
});
