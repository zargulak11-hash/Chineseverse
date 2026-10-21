import { describe, expect, it } from "vitest";
import { phraseAsk, phraseOptionsInChinese } from "./components/LessonSteps.jsx";
import i18n from "./i18n.js";

// The guided lesson's questions and explanations (components/LessonSteps.jsx,
// backend services/lesson_flow.py) read in every language, with nothing left
// as a raw key or an unfilled {{placeholder}}.
const t = (...a) => i18n.t(...a);
const RULES = ["particle_end", "subject_first", "bu_before", "hen_before", "time_early", "de_between", "le_after"];
const ASKS = [
  { type: "phrase_build", prompt: {} },
  { type: "phrase_build", prompt: { final: true } },
  { type: "phrase_listen", prompt: { by: "meaning" } },
  { type: "phrase_listen", prompt: { by: "phrase" } },
  { type: "phrase_gap", prompt: {} },
  { type: "phrase_meaning", prompt: {} },
  { type: "phrase_situation", prompt: {} },
  { type: "phrase_reply", prompt: {} },
];

describe("guided lesson wording", () => {
  it("asks every question type in every language", async () => {
    for (const lang of ["en", "ru", "tg", "zh"]) {
      await i18n.changeLanguage(lang);
      const asks = ASKS.map((q) => phraseAsk(t, q));
      asks.forEach((a) => expect(a).not.toMatch(/lessonFlow\./));
      expect(new Set(asks).size).toBe(asks.length);
    }
  });

  it("explains every word-order rule with the word filled in", async () => {
    for (const lang of ["en", "ru", "tg", "zh"]) {
      await i18n.changeLanguage(lang);
      for (const rule of RULES) {
        const line = t(`lessonFlow.rule.${rule}`, { word: "吗" });
        expect(line).not.toMatch(/\{\{|lessonFlow\./);
        expect(line).toContain("吗");
      }
    }
  });

  it("answers a heard phrase by meaning without Chinese options, the rest in Chinese", () => {
    expect(phraseOptionsInChinese({ type: "phrase_listen", prompt: { by: "meaning" } })).toBe(false);
    expect(phraseOptionsInChinese({ type: "phrase_listen", prompt: { by: "phrase" } })).toBe(true);
    expect(phraseOptionsInChinese({ type: "phrase_reply", prompt: {} })).toBe(true);
  });

  it("names the stages in Tajik", async () => {
    await i18n.changeLanguage("tg");
    expect(["learn", "listen", "build", "recall", "apply", "check"].map((s) => t(`lessonFlow.stage.${s}`)))
      .toEqual(["Омӯзиш", "Шунидан", "Сохтан", "Ба ёд овардан", "Истифода", "Санҷиш"]);
  });
});
