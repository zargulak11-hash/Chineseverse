import { describe, expect, it } from "vitest";
import { pinyinWhyLines } from "./components/PinyinWhy.jsx";
import i18n from "./i18n.js";

// The pinyin course's "why" (services/pinyin_course.py::explain) worded in
// the learner's language: what differed, never an empty or raw-key line.
const t = (...a) => i18n.t(...a);

describe("pinyin answer explanations", () => {
  it("name both tones when a tone was misheard", async () => {
    await i18n.changeLanguage("en");
    const [line] = pinyinWhyLines(t, {
      kind: "pinyin", why: "tone", correct: false, picked: "mà", answer: "mǎ", picked_tone: 4, answer_tone: 3,
    });
    expect(line).toContain("mà — tone 4 (falling)");
    expect(line).toContain("mǎ — tone 3 (low, dipping)");
  });

  it("say which initial was heard, with a listening tip", async () => {
    await i18n.changeLanguage("ru");
    const lines = pinyinWhyLines(t, {
      kind: "pinyin", why: "initial", correct: false, picked: "bà", answer: "pà",
      picked_part: "b", answer_part: "p", tip: "air",
    });
    expect(lines).toHaveLength(2);
    expect(lines[0]).toContain("инициаль — p, а не b");
    expect(lines[1]).toContain("выдох");
  });

  it("explain a spelling rule and the parts of a syllable in every language", async () => {
    for (const lang of ["en", "ru", "tg", "zh"]) {
      await i18n.changeLanguage(lang);
      const rule = pinyinWhyLines(t, { kind: "pinyin", why: "rule", rule: "u_after_jqx", parts: "j + ü + 3", answer: "jǔ" });
      const part = pinyinWhyLines(t, { kind: "pinyin", why: "part", syllable: "ài", initial: "", final: "ai", tone: 4 });
      for (const line of [...rule, ...part]) {
        expect(line).not.toMatch(/pinyinCourse\.|\{\{/);
      }
      expect(rule[0]).toContain("jǔ");
      expect(part[0]).toContain("ai");
    }
  });

  it("stay silent on a right heard answer and on other checks", () => {
    expect(pinyinWhyLines(t, { kind: "pinyin", why: "tone", correct: true, picked: "mǎ", answer: "mǎ" })).toEqual([]);
    expect(pinyinWhyLines(t, { kind: "picked" })).toEqual([]);
    expect(pinyinWhyLines(t, null)).toEqual([]);
  });
});
