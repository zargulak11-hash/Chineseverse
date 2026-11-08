import { describe, expect, it } from "vitest";
import { mistakeView } from "./mistakes.js";

describe("mistakeView", () => {
  it("leads with the Chinese for a word mistake", () => {
    const v = mistakeView({ mistake_type: "word", reference: "我", correct_answer: "我 wǒ", question_text: "I, me", answer_given: "你" });
    expect(v).toEqual({ zh: "我 wǒ", gloss: "I, me", chose: "你" });
  });

  it("drops a gloss that only repeats the headword", () => {
    expect(mistakeView({ mistake_type: "hanzi", reference: "好", question_text: "好" }).gloss).toBeNull();
  });

  it("shows a missed conversation line as its (localized) prompt, not as a headword", () => {
    const v = mistakeView({
      mistake_type: "word",
      reference: "Say: I'm not hungry, thank you.",
      question_text: "Гӯй: Ман гурусна нестам, ташаккур.",
      answer_given: "我不",
    });
    expect(v).toEqual({ zh: null, text: "Гӯй: Ман гурусна нестам, ташаккур.", said: "我不" });
  });

  it("keeps spoken and grammar mistakes as prompt text", () => {
    expect(mistakeView({ mistake_type: "tone", reference: "你好", question_text: "Say hello" }))
      .toEqual({ zh: null, text: "Say hello", said: null });
  });
});
