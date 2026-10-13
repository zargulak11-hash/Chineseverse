# -*- coding: utf-8 -*-
"""Adds the active-recall strings (typed answers, and why an answer was
wrong) to all four locale files. Idempotent. Run from frontend/:
python scripts/add_recall_i18n.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LOCALES = os.path.join(HERE, "..", "src", "locales")
LANGS = ("en", "ru", "tg", "zh")


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


S = {
    "practice.q.type_word": L(
        "Write the Chinese word for this meaning — in characters, or in pinyin with tones.",
        "Напишите китайское слово с этим значением — иероглифами или пиньинем с тонами.",
        "Калимаи чиниро бо ҳамин маъно нависед — бо иероглифҳо ё бо пинйин бо оҳангҳо.",
        "请写出表示这个意思的词——写汉字或带声调的拼音都可以。"),
    "practice.q.type_pinyin": L(
        "Write how this character is read, with its tone.",
        "Напишите, как читается этот иероглиф, с тоном.",
        "Нависед, ки ин иероглиф чӣ тавр хонда мешавад, бо оҳангаш.",
        "请写出这个汉字的拼音，要带声调。"),
    "practice.recall.badge": L("From memory", "По памяти", "Аз ёд", "凭记忆"),
    "practice.recall.why": L(
        "You already recognise this — now recall it yourself. A word counts as mastered only once you have produced it from memory.",
        "Вы уже узнаёте это — теперь вспомните сами. Слово считается выученным, только когда вы воспроизвели его по памяти.",
        "Шумо инро аллакай мешиносед — акнун худатон ба ёд оред. Калима танҳо вақте азхудшуда ҳисоб мешавад, ки шумо онро аз ёд навишта тавонед.",
        "你已经认识它了——现在试着自己回忆出来。只有凭记忆写出来，这个词才算真正掌握。"),
    "practice.recall.label": L("Your answer", "Ваш ответ", "Ҷавоби шумо", "你的答案"),
    "practice.recall.check": L("Check", "Проверить", "Санҷидан", "检查"),
    "practice.recall.dontKnow": L("I don't know", "Не знаю", "Намедонам", "我不知道"),
    "practice.recall.toneHint": L(
        "Tones: tone marks (nǐ hǎo) or a number after each syllable (ni3 hao3). Spaces don't matter.",
        "Тоны: знаками (nǐ hǎo) или цифрой после каждого слога (ni3 hao3). Пробелы не важны.",
        "Оҳангҳо: бо аломатҳо (nǐ hǎo) ё бо рақам пас аз ҳар ҳиҷо (ni3 hao3). Фосилаҳо аҳамият надоранд.",
        "声调：可以用声调符号（nǐ hǎo），也可以在每个音节后写数字（ni3 hao3）。空格没有关系。"),
    "practice.recall.addTones": L(
        "The sounds are right — now add the tones. Which tone does each syllable have?",
        "Звуки верные — теперь добавьте тоны. Какой тон у каждого слога?",
        "Садоҳо дурустанд — акнун оҳангҳоро илова кунед. Ҳар ҳиҷо кадом оҳанг дорад?",
        "音节对了——现在加上声调吧。每个音节是第几声？"),
    "practice.recall.youTyped": L("You wrote: {{text}}", "Вы написали: {{text}}", "Шумо навиштед: {{text}}",
                                  "你写的是：{{text}}"),
    "practice.why.alternative": L(
        "Also right: {{word}} has this meaning too. The word this question had in mind is shown below.",
        "Тоже верно: у {{word}} тоже есть это значение. Слово, которое имелось в виду, — ниже.",
        "Ин ҳам дуруст аст: {{word}} низ ҳамин маъноро дорад. Калимае, ки дар назар буд, дар поён аст.",
        "这样也对：{{word}}也有这个意思。题目想要的词在下面。"),
    "practice.why.tone": L(
        "The syllables are right, the tones are not: you wrote tones {{typed}}, the word has {{expected}}. In Chinese a different tone makes a different word.",
        "Слоги верные, а тоны — нет: вы написали тоны {{typed}}, а у слова {{expected}}. В китайском другой тон — это другое слово.",
        "Ҳиҷоҳо дурустанд, вале оҳангҳо не: шумо оҳангҳои {{typed}} навиштед, калима {{expected}} дорад. Дар забони чинӣ оҳанги дигар — калимаи дигар аст.",
        "音节对了，声调不对：你写的是{{typed}}声，这个词是{{expected}}声。在中文里，声调不同就是不同的词。"),
    "practice.why.missing_tones": L(
        "The syllables are right, but the tones are missing — and tones are part of the word.",
        "Слоги верные, но тонов нет — а тоны являются частью слова.",
        "Ҳиҷоҳо дурустанд, вале оҳангҳо нестанд — оҳанг қисми калима аст.",
        "音节对了，但是没有写声调——声调也是词的一部分。"),
    "practice.why.other_word": L(
        "{{word}} ({{pinyin}}) is another word: it means “{{meaning}}”. Compare it with the answer below — the two will meet again in your practice.",
        "{{word}} ({{pinyin}}) — другое слово: оно значит «{{meaning}}». Сравните с ответом ниже — эти два слова ещё встретятся вам в практике.",
        "{{word}} ({{pinyin}}) калимаи дигар аст: маънояш «{{meaning}}». Онро бо ҷавоби поён муқоиса кунед — ин ду калима боз дар машқ вомехӯранд.",
        "{{word}}（{{pinyin}}）是另一个词，意思是“{{meaning}}”。和下面的答案比较一下——这两个词以后还会在练习里一起出现。"),
    "practice.why.picked": L(
        "The option you chose belongs to {{word}} ({{pinyin}}): “{{meaning}}”. Compare it with the answer below — the two will meet again in your practice.",
        "Выбранный вариант относится к {{word}} ({{pinyin}}): «{{meaning}}». Сравните с ответом ниже — они ещё встретятся вам в практике.",
        "Варианти интихобкардаи шумо ба {{word}} ({{pinyin}}) тааллуқ дорад: «{{meaning}}». Онро бо ҷавоби поён муқоиса кунед — ин ду боз дар машқ вомехӯранд.",
        "你选的选项属于{{word}}（{{pinyin}}）：“{{meaning}}”。和下面的答案比较一下——它们以后还会在练习里一起出现。"),
    "practice.why.wrong": L(
        "Not this time. Look at the answer below — it comes back soon in your review, so you can recall it again.",
        "В этот раз нет. Посмотрите на ответ ниже — он скоро вернётся в повторении, и вы попробуете вспомнить его снова.",
        "Ин дафъа не. Ба ҷавоби поён нигаред — он ба наздикӣ дар такрор бармегардад, то онро боз ба ёд оред.",
        "这次不对。看看下面的答案——它很快会回到复习里，你可以再回忆一次。"),
    "practice.why.unknown": L(
        "That's fine — now you've seen it. It comes back in a few hours so you can try to recall it.",
        "Ничего страшного — теперь вы это видели. Это вернётся через несколько часов, чтобы вы попробовали вспомнить.",
        "Ҳеҷ гап не — акнун шумо онро дидед. Он пас аз чанд соат бармегардад, то онро ба ёд оваред.",
        "没关系——现在你看到了。几个小时后它会再出现，到时候试着回忆它。"),
}

KEYS = list(S)


def _line(indent, key, value, comma):
    return f'{" " * indent}{json.dumps(key, ensure_ascii=False)}: {json.dumps(value, ensure_ascii=False)}{"," if comma else ""}'


def insert(lines, lang):
    """Inserts the strings as new lines inside "practice", leaving every
    existing line as it is (the files keep hand-formatted one-line objects
    that a json.dump would reflow). Keys already present are skipped, so
    re-running changes nothing."""
    start = lines.index('  "practice": {')
    q_open = lines.index('    "q": {', start)
    q_close = next(i for i in range(q_open, len(lines)) if lines[i].startswith("    }"))
    present = "\n".join(lines[start:])
    q_new = [(k.split(".")[-1], v[lang]) for k, v in S.items() if k.startswith("practice.q.")]
    q_new = [(k, v) for k, v in q_new if f'      "{k}":' not in "\n".join(lines[q_open:q_close])]
    groups = {}
    for k, v in S.items():
        _, group, leaf = k.split(".")
        if group != "q":
            groups.setdefault(group, []).append((leaf, v[lang]))
    after = []
    for group, items in groups.items():
        if f'    "{group}": {{' in present:
            continue
        after.append(f'    "{group}": {{')
        after += [_line(6, k, v, i < len(items) - 1) for i, (k, v) in enumerate(items)]
        after.append("    },")
    if after:
        # The q block closes with "}," (more keys follow it in "practice").
        lines[q_close + 1:q_close + 1] = after
    if q_new:
        lines[q_close - 1] = lines[q_close - 1].rstrip(",") + ","
        lines[q_close:q_close] = [_line(6, k, v, i < len(q_new) - 1) for i, (k, v) in enumerate(q_new)]
    return lines


if __name__ == "__main__":
    for lang in LANGS:
        path = os.path.join(LOCALES, f"{lang}.json")
        with open(path, encoding="utf-8", newline="") as f:
            lines = f.read().split("\r\n")
        lines = insert(lines, lang)
        text = "\r\n".join(lines)
        json.loads(text)  # still valid JSON
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print(f"updated {lang}.json")
