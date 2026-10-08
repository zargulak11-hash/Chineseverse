// How a stored mistake (GET /api/mistakes, LearningMistake) is shown. For a
// word or a character the Chinese leads -- the form the learner got wrong,
// with its gloss after -- instead of the English prompt, which made the
// notebook read like a list of English words ("you", "good, fine"). Spoken
// and grammar mistakes keep their prompt text.
const CHINESE_FIRST = new Set(["word", "hanzi", "character", "hanzi_write"]);

export function mistakeView(m) {
  if (CHINESE_FIRST.has(m.mistake_type)) {
    const zh = m.correct_answer || m.reference;
    const gloss = m.question_text && m.question_text !== zh ? m.question_text : null;
    return { zh, gloss, chose: m.answer_given || null };
  }
  return { zh: null, text: m.question_text || m.reference, said: m.answer_given || null };
}
