import fs from "node:fs";
import path from "node:path";
import { beforeEach, describe, expect, it } from "vitest";
import { localizeApiError } from "./apiErrors.js";
import i18n from "./i18n.js";
import en from "./locales/en.json";
import ru from "./locales/ru.json";
import tg from "./locales/tg.json";
import zh from "./locales/zh.json";

const LOCALES = { en, ru, tg, zh };
// The detail -> key table, read from the source so a new mapping is
// checked without having to be listed here too.
const source = fs.readFileSync(path.join(__dirname, "apiErrors.js"), "utf8");
const exact = [...source.matchAll(/^\s*"([^"]+)":\s*"(\w+)",/gm)].map((m) => [m[1], m[2]]);

beforeEach(async () => {
  await i18n.changeLanguage("en");
});

describe("server error messages", () => {
  it("every mapped message has a translation in all four languages", () => {
    expect(exact.length).toBeGreaterThan(30);
    for (const [, key] of exact) {
      for (const [code, locale] of Object.entries(LOCALES)) {
        expect(locale.apiErrors[key], `${code}: apiErrors.${key}`).toBeTruthy();
      }
    }
  });

  it.each(["ru", "tg", "zh"])("a mapped message is shown in %s, not in English", async (code) => {
    await i18n.changeLanguage(code);
    for (const [detail, key] of exact) {
      expect(localizeApiError(detail, 400), detail).toBe(LOCALES[code].apiErrors[key]);
    }
  });

  it("messages with a level keep the number", async () => {
    await i18n.changeLanguage("ru");
    expect(localizeApiError("This mission opens at HSK 3", 403)).toContain("3");
    expect(localizeApiError("This place opens at HSK 4", 403)).toContain("4");
    expect(localizeApiError("This story opens at HSK 5", 403)).toContain("5");
    expect(localizeApiError("This mission opens at HSK 3", 403)).not.toMatch(/opens at/);
  });

  it("file errors keep the file's name and translate the problem", async () => {
    await i18n.changeLanguage("ru");
    const shown = localizeApiError("notes.txt: the file is too large", 413);
    expect(shown).toContain("notes.txt");
    expect(shown).not.toContain("the file is too large");
  });

  it("anything unmapped (admin tools, rare internals) keeps the server's own text", () => {
    expect(localizeApiError("You cannot delete your own admin account", 400)).toBe("You cannot delete your own admin account");
  });

  it("a missing row is a generic 'not found' in the learner's language", async () => {
    await i18n.changeLanguage("zh");
    expect(localizeApiError("Scenario not found", 404)).toBe(zh.apiErrors.notFound);
  });

  it("bodies without a sentence fall back by status", async () => {
    await i18n.changeLanguage("ru");
    expect(localizeApiError([{ loc: ["body"], msg: "x" }], 422)).toBe(ru.apiErrors.invalidInput);
    expect(localizeApiError(null, 502)).toBe(ru.apiErrors.server);
    expect(localizeApiError(undefined, 418)).toContain("418");
  });
});
