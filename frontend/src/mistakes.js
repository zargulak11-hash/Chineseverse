// How a stored mistake (GET /api/mistakes, LearningMistake) is shown. For a
// word or a character the Chinese leads -- the form the learner got wrong,
// with its gloss after -- instead of the English prompt, which made the
// notebook read like a list of English words ("you", "good, fine"). Spoken
// and grammar mistakes keep their prompt text.
const CHINESE_FIRST = new Set(["word", "hanzi", "character", "hanzi_write"]);
const HAS_HANZI = /[㐀-鿿]/;

export function mistakeView(m) {
  const zh = m.correct_answer || m.reference;
  // A spoken answer that missed on its words is a "word" mistake too, but
  // its reference is the conversation line's instruction ("Say: I'm not
  // hungry, thank you.") -- shown as the Chinese headword, in English, in
  // every language. Only Chinese leads.
  if (CHINESE_FIRST.has(m.mistake_type) && HAS_HANZI.test(zh || "")) {
    const gloss = m.question_text && m.question_text !== zh ? m.question_text : null;
    return { zh, gloss, chose: m.answer_given || null };
  }
  return { zh: null, text: m.question_text || m.reference, said: m.answer_given || null };
}
