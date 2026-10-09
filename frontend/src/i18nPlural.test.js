import { describe, expect, it } from "vitest";
import i18n from "./i18n.js";
import tg from "./locales/tg.json";

describe("Tajik plurals", () => {
  // Node, like browsers, has no Tajik plural data: Intl.PluralRules("tg")
  // becomes the machine's own locale. Without the fixed rule in i18n.js a
  // count that is "few"/"many" there fell back to the English string.
  it("never fall back to English, whatever the device's own plural rules", async () => {
    await i18n.changeLanguage("tg");
    for (const count of [0, 1, 2, 3, 5, 11, 21]) {
      expect(i18n.t("dashboard.built.words", { count })).toBe(tg.dashboard.built.words_other);
    }
  });
});
