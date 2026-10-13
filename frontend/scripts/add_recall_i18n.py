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

WHY = L(
    "You pick these out of options, but have never produced them yourself. A word you can recall is a word you can use.",
    "Вы узнаёте их среди вариантов, но ещё ни разу не воспроизвели сами. Слово, которое вы можете вспомнить, — слово, которым вы можете пользоваться.",
    "Шумо онҳоро дар байни вариантҳо мешиносед, вале ҳанӯз худатон нанавиштаед. Калимае, ки ба ёд оварда метавонед, калимаест, ки истифода бурда метавонед.",
    "你能在选项里认出它们，但还没有自己写出来过。能回忆起来的词，才是能用的词。")

# The recall round ("/practice?source=recall") and the plan/next step that
# send the learner there: added into objects that already exist.
INTO = {
    "practice.title.recall": L("Recall from memory", "Вспомнить по памяти", "Ба ёд овардан", "凭记忆回想"),
    "practice.recallNothing": L(
        "Nothing to recall right now — every word you recognise has been recalled from memory at least once.",
        "Сейчас вспоминать нечего — каждое слово, которое вы узнаёте, вы уже хотя бы раз вспомнили по памяти.",
        "Ҳоло чизе барои ба ёд овардан нест — ҳар калимаеро, ки мешиносед, шумо ақаллан як бор аз ёд навиштаед.",
        "现在没有要回想的——你认识的每个词都至少凭记忆写出过一次。"),
    "practice.recallWhat": L(
        "Words and characters you recognise but have never produced yourself gather here. Recalling one from memory is what makes it mastered.",
        "Здесь собираются слова и иероглифы, которые вы узнаёте, но ещё ни разу не воспроизвели сами. Выученным слово становится, когда вы вспоминаете его по памяти.",
        "Дар ин ҷо калимаҳо ва иероглифҳое ҷамъ мешаванд, ки шумо мешиносед, вале ҳанӯз худатон нанавиштаед. Калима вақте азхуд мешавад, ки онро аз ёд нависед.",
        "这里是你认识、但还没有自己写出来过的词和汉字。凭记忆写出来，才算真正掌握。"),
    "journey.next.recall": {
        "en": {"one": "Recall a word you only recognise", "other": "Recall {{count}} words you only recognise"},
        "ru": {"one": "Вспомнить {{count}} слово, которое вы пока только узнаёте",
               "few": "Вспомнить {{count}} слова, которые вы пока только узнаёте",
               "many": "Вспомнить {{count}} слов, которые вы пока только узнаёте",
               "other": "Вспомнить {{count}} слова, которые вы пока только узнаёте"},
        "tg": {"one": "Калимаеро, ки ҳоло фақат мешиносед, аз ёд нависед",
               "other": "{{count}} калимаеро, ки ҳоло фақат мешиносед, аз ёд нависед"},
        "zh": {"other": "凭记忆写出{{count}}个你只认得的词"},
    },
    "journey.nextWhy.recall": WHY,
    # Progress -> "What you know" (GET /api/analytics/knowledge)
    "pages.progress.knowTitle": L("What you know", "Что вы знаете", "Он чи шумо медонед", "你掌握了什么"),
    "pages.progress.knowSub": L(
        "Counted from your graded answers. Choosing a word among options shows you recognise it; writing it from memory shows you can recall it — only that makes it mastered.",
        "Подсчитано по вашим проверенным ответам. Выбрать слово среди вариантов — значит узнать его; написать по памяти — значит вспомнить. Только это делает слово выученным.",
        "Аз рӯи ҷавобҳои санҷидашудаи шумо ҳисоб шудааст. Интихоби калима аз байни вариантҳо нишон медиҳад, ки шумо онро мешиносед; навиштани он аз ёд нишон медиҳад, ки онро ба ёд оварда метавонед — танҳо ҳамин онро азхудшуда мекунад.",
        "根据你被批改过的答案统计。在选项中选出一个词，说明你认得它；凭记忆写出来，说明你能回想起来——只有这样才算掌握。"),
    "pages.progress.knowWords": L("Words", "Слова", "Калимаҳо", "词语"),
    "pages.progress.knowChars": L("Characters", "Иероглифы", "Иероглифҳо", "汉字"),
    "pages.progress.knowMet": L("Met: {{count}}", "Встречено: {{count}}", "Дидаед: {{count}}", "学过：{{count}}"),
    "pages.progress.knowLearning": L("Learning", "Изучаете", "Меомӯзед", "在学"),
    "pages.progress.knowLearningWhat": L(
        "Met in practice, not yet answered reliably.", "Встречались в практике, но пока без уверенных ответов.",
        "Дар машқ дида шудааст, вале ҳанӯз бо боварӣ ҷавоб дода нашудааст.", "练习中见过，还没有稳定答对。"),
    "pages.progress.knowRecognised": L("Recognised", "Узнаёте", "Мешиносед", "认得"),
    "pages.progress.knowRecognisedWhat": L(
        "You pick it out of options, but haven't written it from memory yet.",
        "Вы выбираете их среди вариантов, но ещё не писали по памяти.",
        "Шумо онро аз байни вариантҳо интихоб мекунед, вале ҳанӯз аз ёд нанавиштаед.",
        "能在选项中选出来，但还没有凭记忆写过。"),
    "pages.progress.knowRecalled": L("Recalled", "Вспоминаете", "Ба ёд меоред", "能回想"),
    "pages.progress.knowRecalledWhat": L(
        "Written from memory at least once; still being reinforced.", "Хотя бы раз написаны по памяти; ещё закрепляются.",
        "Ақаллан як бор аз ёд навишта шудааст; ҳоло мустаҳкам мешавад.", "至少凭记忆写出过一次，还在巩固。"),
    "pages.progress.knowMastered": L("Mastered", "Выучены", "Азхуд шудааст", "已掌握"),
    "pages.progress.knowMasteredWhat": L(
        "Answered reliably and recalled from memory.", "Уверенные ответы и воспроизведение по памяти.",
        "Ҷавобҳои боэътимод ва аз ёд навиштан.", "稳定答对，并能凭记忆写出。"),
    "pages.progress.knowDue": L("Due for review: {{count}}", "Пора повторить: {{count}}", "Барои такрор: {{count}}",
                                "该复习：{{count}}"),
    "pages.progress.knowSlipping": L("Fading: {{count}}", "Забываются: {{count}}", "Фаромӯш мешаванд: {{count}}",
                                     "快忘了：{{count}}"),
    "pages.progress.knowRecallAcc": L(
        "From memory in the last {{days}} days: {{correct}} of {{total}} correct.",
        "По памяти за последние {{days}} дней: верно {{correct}} из {{total}}.",
        "Аз ёд дар {{days}} рӯзи охир: {{correct}} аз {{total}} дуруст.",
        "最近{{days}}天凭记忆作答：{{total}}题中答对{{correct}}题。"),
    "pages.progress.knowRecallNone": L(
        "No answers from memory in the last {{days}} days yet.", "За последние {{days}} дней ответов по памяти пока нет.",
        "Дар {{days}} рӯзи охир ҳанӯз ҷавоби аз ёд нест.", "最近{{days}}天还没有凭记忆作答。"),
    "pages.progress.knowEmpty": L(
        "Nothing here yet — practise a level, and your words appear here as you answer.",
        "Пока пусто — потренируйте уровень, и слова появятся здесь по мере ваших ответов.",
        "Ҳоло холист — як сатҳро машқ кунед, ва калимаҳо ҳангоми ҷавоб додан дар ин ҷо пайдо мешаванд.",
        "这里还是空的——练习一个级别，答题后你的词就会出现在这里。"),
    "pages.progress.knowGoRecall": L("Recall them now", "Вспомнить сейчас", "Ҳозир ба ёд оред", "现在去回想"),
    "pages.progress.knowGoReview": L("Review now", "Повторить сейчас", "Ҳозир такрор кунед", "现在去复习"),
}

KEYS = list(S) + list(INTO)  # a plural key is checked through its _other form


def _object(lines, path):
    """(first line inside, closing line) of the multi-line object at
    `path` ("journey.next"), found by its two-space indentation."""
    lo, hi = 0, len(lines)
    for depth, part in enumerate(path.split("."), start=1):
        pad = " " * (2 * depth)
        lo = next(i for i in range(lo, hi) if lines[i] == f'{pad}"{part}": {{')
        hi = next(i for i in range(lo + 1, hi) if lines[i] in (f"{pad}}}", f"{pad}}},"))
        lo += 1
    return lo, hi


def put(lines, dotted, value):
    parent, leaf = dotted.rsplit(".", 1)
    lo, hi = _object(lines, parent)
    pad = " " * (2 * (parent.count(".") + 2))
    entries = [(leaf, value)] if isinstance(value, str) else [(f"{leaf}_{form}", v) for form, v in value.items()]
    entries = [(k, v) for k, v in entries if not any(lines[i].startswith(f'{pad}"{k}":') for i in range(lo, hi))]
    if not entries:
        return
    lines[hi - 1] = lines[hi - 1].rstrip(",") + ","
    lines[hi:hi] = [_line(len(pad), k, v, i < len(entries) - 1) for i, (k, v) in enumerate(entries)]


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
        for dotted, value in INTO.items():
            put(lines, dotted, value[lang])
        text = "\r\n".join(lines)
        json.loads(text)  # still valid JSON
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print(f"updated {lang}.json")
