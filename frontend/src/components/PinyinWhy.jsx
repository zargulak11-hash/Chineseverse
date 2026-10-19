import { useTranslation } from "react-i18next";

// Why a pinyin answer was right or wrong, worded from the structured check
// the server sends (services/pinyin_course.py::explain): which part of the
// syllable differed -- the initial, the final, the tone -- or which spelling
// rule applies, with a listening tip for the pair that was confused.
export function pinyinWhyLines(t, check) {
  if (!check || check.kind !== "pinyin") return [];
  const plain = { interpolation: { escapeValue: false } };
  const tone = (n) => t(`pinyinCourse.toneName.${n ?? 0}`);
  const lines = [];
  switch (check.why) {
    case "tone":
      if (check.picked && !check.correct) {
        lines.push(t("pinyinCourse.why.tone", {
          picked: check.picked, pickedTone: tone(check.picked_tone),
          answer: check.answer, answerTone: tone(check.answer_tone), ...plain,
        }));
      }
      break;
    case "mark":
      lines.push(t("pinyinCourse.why.mark", { syllable: check.syllable, answerTone: tone(check.answer_tone), ...plain }));
      if (!check.correct && check.picked_tone) lines.push(t("pinyinCourse.why.markPicked", { pickedTone: tone(check.picked_tone) }));
      break;
    case "part":
      lines.push(check.initial
        ? t("pinyinCourse.why.part", { syllable: check.syllable, initial: check.initial, final: check.final, tone: tone(check.tone), ...plain })
        : t("pinyinCourse.why.partNoInitial", { syllable: check.syllable, final: check.final, tone: tone(check.tone), ...plain }));
      break;
    case "rule":
      lines.push(t("pinyinCourse.why.rule", { parts: check.parts, answer: check.answer, ...plain }));
      lines.push(t(`pinyinCourse.rule.${check.rule}`));
      break;
    case "initial":
    case "final":
      if (!check.correct) {
        lines.push(t(`pinyinCourse.why.${check.why}`, {
          picked: check.picked, answer: check.answer, pickedPart: check.picked_part, answerPart: check.answer_part, ...plain,
        }));
        if (check.tip) lines.push(t(`pinyinCourse.tip.${check.tip}`));
      }
      break;
    default:
      if (check.picked && !check.correct) lines.push(t("pinyinCourse.why.heard", { answer: check.answer, picked: check.picked, ...plain }));
  }
  return lines;
}

export default function PinyinWhy({ check }) {
  const { t } = useTranslation();
  const lines = pinyinWhyLines(t, check);
  if (!lines.length) return null;
  return (
    <div className="practice-why" aria-live="polite">
      {lines.map((line, i) => <p key={i}>{line}</p>)}
    </div>
  );
}
