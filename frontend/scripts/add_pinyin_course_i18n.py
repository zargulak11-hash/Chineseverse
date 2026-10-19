# -*- coding: utf-8 -*-
"""Adds the strings of the pinyin foundation course (pages/Foundation.jsx,
services/pinyin_course.py) and of the pinyin answer explanations into all
four locale files. Idempotent: keys already present are skipped.
Run from frontend/: python scripts/add_pinyin_course_i18n.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_recall_i18n import LANGS, LOCALES, put  # noqa: E402


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


S = {
    # ---- the course page ----
    "pinyinCourse.title": L("The pinyin course", "Курс пиньиня", "Курси пинйин", "拼音课程"),
    "pinyinCourse.kpiUnits": L("Units passed", "Пройдено уроков", "Дарсҳои гузашта", "已通过单元"),
    "pinyinCourse.unitN": L("Unit {{n}}", "Урок {{n}}", "Дарси {{n}}", "第 {{n}} 单元"),
    "pinyinCourse.statusPassed": L("Passed · {{score}}%", "Пройден · {{score}}%", "Гузашт · {{score}}%", "已通过 · {{score}}%"),
    "pinyinCourse.statusBest": L("Best {{score}}%", "Лучший {{score}}%", "Беҳтарин {{score}}%", "最好 {{score}}%"),
    "pinyinCourse.statusNext": L("Start here", "Начните здесь", "Аз ин ҷо сар кунед", "从这里开始"),
    "pinyinCourse.statusNew": L("Not started", "Не начат", "Сар нашудааст", "未开始"),
    "pinyinCourse.unitsLabel": L("Units of the course", "Уроки курса", "Дарсҳои курс", "课程单元"),
    "pinyinCourse.stepLearn": L("Understand", "Разберитесь", "Фаҳмед", "理解"),
    "pinyinCourse.stepHear": L("Listen and repeat", "Слушайте и повторяйте", "Гӯш кунед ва такрор кунед", "听和跟读"),
    "pinyinCourse.stepHearBody": L(
        "Tap each syllable to hear it, then say it after the voice.",
        "Нажмите на слог, чтобы услышать его, и повторите вслед за голосом.",
        "Ба ҳар ҳиҷо пахш кунед, то онро бишнавед, ва пас аз овоз такрор кунед.",
        "点一下音节听读音，然后跟着说。"),
    "pinyinCourse.stepTry": L("Try it — with help", "Попробуйте — с подсказкой", "Санҷед — бо ёрӣ", "试一试（有讲解）"),
    "pinyinCourse.stepTryBody": L(
        "Three questions. Every answer is explained; nothing here is graded or saved.",
        "Три вопроса. Каждый ответ объясняется; здесь ничего не оценивается и не сохраняется.",
        "Се савол. Ҳар ҷавоб шарҳ дода мешавад; дар ин ҷо ҳеҷ чиз баҳо дода ва нигоҳ дошта намешавад.",
        "三道题。每个答案都有讲解；这里不打分，也不保存。"),
    "pinyinCourse.stepCheck": L("Mastery check", "Проверка", "Санҷиши азхудкунӣ", "掌握检测"),
    "pinyinCourse.stepCheckBody": L(
        "8 graded questions. Score {{score}}% or more to pass this unit — you can repeat it any time.",
        "8 оцениваемых вопросов. Наберите {{score}}% или больше, чтобы пройти урок; повторять можно сколько угодно.",
        "8 саволи баҳододашаванда. Барои гузаштан аз дарс {{score}}% ё бештар гиред — ҳар вақт такрор кардан мумкин аст.",
        "8 道计分题。得到 {{score}}% 或以上就通过本单元，随时可以再做。"),
    "pinyinCourse.startCheck": L("Start the check", "Начать проверку", "Санҷишро сар кунед", "开始检测"),
    "pinyinCourse.checkAgain": L("Check again", "Проверить ещё раз", "Боз санҷед", "再测一次"),
    "pinyinCourse.nextUnit": L("Next unit", "Следующий урок", "Дарси навбатӣ", "下一单元"),
    "pinyinCourse.prevUnit": L("Previous unit", "Предыдущий урок", "Дарси қаблӣ", "上一单元"),
    "pinyinCourse.play": L("Play the sound", "Прослушать", "Гӯш кардан", "播放读音"),
    "pinyinCourse.question": L("Question {{n}}", "Вопрос {{n}}", "Саволи {{n}}", "第 {{n}} 题"),
    "pinyinCourse.right": L("Right.", "Верно.", "Дуруст.", "对了。"),
    "pinyinCourse.wrong": L("Not quite.", "Не совсем.", "На он қадар.", "不太对。"),
    "pinyinCourse.tryAgain": L("Try another option", "Попробуйте другой вариант", "Варианти дигарро санҷед", "再选一个"),
    "pinyinCourse.finalTitle": L("Step check: real HSK 1 characters", "Итог шага: настоящие иероглифы HSK 1",
                                 "Санҷиши қадам: иероглифҳои воқеии HSK 1", "本步检测：真实的 HSK 1 汉字"),
    "pinyinCourse.finalBody": L(
        "Hear real HSK 1 characters and words and pick the right tone and meaning. Passing every unit above, or this "
        "round with 60% or more, completes step 1.",
        "Слушайте настоящие иероглифы и слова HSK 1 и выбирайте тон и значение. Шаг 1 засчитывается, когда пройдены "
        "все уроки выше или этот раунд на 60% и больше.",
        "Иероглифҳо ва калимаҳои воқеии HSK 1-ро бишнавед ва оҳанг ва маъноро интихоб кунед. Қадами 1 вақте анҷом "
        "меёбад, ки ҳамаи дарсҳои боло ё ин давр бо 60% ё бештар гузаронида шавад.",
        "听真实的 HSK 1 汉字和词语，选出声调和意思。上面所有单元都通过，或者这一轮得到 60% 以上，第一步就完成了。"),
    "pinyinCourse.sideBody": L(
        "Six short units, in order: the parts of a syllable, the tones, the initials, the finals and the spelling "
        "rules. Each one explains first, then lets you try, then checks.",
        "Шесть коротких уроков по порядку: части слога, тоны, инициали, финали и правила записи. Каждый сначала "
        "объясняет, потом даёт попробовать, потом проверяет.",
        "Шаш дарси кӯтоҳ бо тартиб: қисмҳои ҳиҷо, оҳангҳо, ибтидоҳо, охирҳо ва қоидаҳои навишт. Ҳар кадом аввал шарҳ "
        "медиҳад, баъд имкони санҷидан медиҳад, баъд месанҷад.",
        "六个短单元，按顺序学：音节的组成、声调、声母、韵母和拼写规则。每个单元先讲解，再练习，最后检测。"),
    "pinyinCourse.allPassed": L(
        "Every unit passed — you can read and hear pinyin. Step 1 is complete.",
        "Все уроки пройдены — вы читаете и слышите пиньинь. Шаг 1 выполнен.",
        "Ҳамаи дарсҳо гузаштанд — шумо пинйинро мехонед ва мешунавед. Қадами 1 анҷом ёфт.",
        "所有单元都通过了——你已经能读、能听拼音。第一步完成了。"),
    # ---- the part names ----
    "pinyinCourse.initial": L("initial", "инициаль", "ибтидо", "声母"),
    "pinyinCourse.final": L("final", "финаль", "охир", "韵母"),
    "pinyinCourse.tone": L("tone", "тон", "оҳанг", "声调"),
    "pinyinCourse.toneName.0": L("the light tone", "лёгкий тон", "оҳанги сабук", "轻声"),
    "pinyinCourse.toneName.1": L("tone 1 (high, level)", "1-й тон (высокий, ровный)", "оҳанги 1 (баланд, ҳамвор)", "第一声（高平）"),
    "pinyinCourse.toneName.2": L("tone 2 (rising)", "2-й тон (восходящий)", "оҳанги 2 (болоравӣ)", "第二声（上升）"),
    "pinyinCourse.toneName.3": L("tone 3 (low, dipping)", "3-й тон (низкий, с провалом)", "оҳанги 3 (паст, хамида)", "第三声（低，先降后升）"),
    "pinyinCourse.toneName.4": L("tone 4 (falling)", "4-й тон (нисходящий)", "оҳанги 4 (поёнравӣ)", "第四声（下降）"),
    # ---- why an answer was right or wrong ----
    "pinyinCourse.why.tone": L(
        "You chose {{picked}} — {{pickedTone}}. You heard {{answer}} — {{answerTone}}. Same sound, another tone: another word.",
        "Вы выбрали {{picked}} — {{pickedTone}}. Прозвучало {{answer}} — {{answerTone}}. Тот же звук, другой тон — другое слово.",
        "Шумо {{picked}}-ро интихоб кардед — {{pickedTone}}. Садо дод {{answer}} — {{answerTone}}. Ҳамон овоз, оҳанги дигар — калимаи дигар.",
        "你选了 {{picked}}——{{pickedTone}}。听到的是 {{answer}}——{{answerTone}}。音一样，声调不同，就是另一个词。"),
    "pinyinCourse.why.toneChar": L(
        "{{picked}} is {{pickedTone}}; this character is read {{answer}} — {{answerTone}}.",
        "{{picked}} — это {{pickedTone}}; этот иероглиф читается {{answer}} — {{answerTone}}.",
        "{{picked}} — {{pickedTone}} аст; ин иероглиф {{answer}} хонда мешавад — {{answerTone}}.",
        "{{picked}} 是{{pickedTone}}；这个字读 {{answer}}——{{answerTone}}。"),
    "pinyinCourse.why.mark": L("The mark on {{syllable}} shows {{answerTone}}.", "Знак над {{syllable}} — это {{answerTone}}.",
                               "Аломати болои {{syllable}} {{answerTone}}-ро нишон медиҳад.", "{{syllable}} 上的符号表示{{answerTone}}。"),
    "pinyinCourse.why.markPicked": L("You chose {{pickedTone}}.", "Вы выбрали: {{pickedTone}}.", "Шумо интихоб кардед: {{pickedTone}}.",
                                     "你选的是{{pickedTone}}。"),
    "pinyinCourse.why.part": L(
        "{{syllable}} = {{initial}} (initial) + {{final}} (final) + {{tone}}.",
        "{{syllable}} = {{initial}} (инициаль) + {{final}} (финаль) + {{tone}}.",
        "{{syllable}} = {{initial}} (ибтидо) + {{final}} (охир) + {{tone}}.",
        "{{syllable}} = {{initial}}（声母）+ {{final}}（韵母）+ {{tone}}。"),
    "pinyinCourse.why.partNoInitial": L(
        "{{syllable}} has no initial: it is only the final {{final}} + {{tone}}.",
        "У {{syllable}} нет инициали: это только финаль {{final}} + {{tone}}.",
        "{{syllable}} ибтидо надорад: он танҳо охири {{final}} + {{tone}} аст.",
        "{{syllable}} 没有声母，只有韵母 {{final}} + {{tone}}。"),
    "pinyinCourse.why.initial": L(
        "You chose {{picked}}, but you heard {{answer}}: the initial is {{answerPart}}, not {{pickedPart}}.",
        "Вы выбрали {{picked}}, а прозвучало {{answer}}: инициаль — {{answerPart}}, а не {{pickedPart}}.",
        "Шумо {{picked}}-ро интихоб кардед, аммо {{answer}} садо дод: ибтидо {{answerPart}} аст, на {{pickedPart}}.",
        "你选了 {{picked}}，听到的是 {{answer}}：声母是 {{answerPart}}，不是 {{pickedPart}}。"),
    "pinyinCourse.why.final": L(
        "You chose {{picked}}, but you heard {{answer}}: the final is {{answerPart}}, not {{pickedPart}}.",
        "Вы выбрали {{picked}}, а прозвучало {{answer}}: финаль — {{answerPart}}, а не {{pickedPart}}.",
        "Шумо {{picked}}-ро интихоб кардед, аммо {{answer}} садо дод: охир {{answerPart}} аст, на {{pickedPart}}.",
        "你选了 {{picked}}，听到的是 {{answer}}：韵母是 {{answerPart}}，不是 {{pickedPart}}。"),
    "pinyinCourse.why.heard": L(
        "You heard {{answer}}. Play it again and compare it with {{picked}}.",
        "Прозвучало {{answer}}. Прослушайте ещё раз и сравните с {{picked}}.",
        "{{answer}} садо дод. Боз гӯш кунед ва бо {{picked}} муқоиса кунед.",
        "听到的是 {{answer}}。再听一遍，和 {{picked}} 比一比。"),
    "pinyinCourse.why.rule": L("{{parts}} is written {{answer}}.", "{{parts}} пишется {{answer}}.", "{{parts}} {{answer}} навишта мешавад.",
                               "{{parts}} 写成 {{answer}}。"),
    "pinyinCourse.tip.air": L(
        "Listen for the puff of air: p, t, k, q, ch, c have it; b, d, g, j, zh, z do not.",
        "Слушайте выдох: у p, t, k, q, ch, c он есть, у b, d, g, j, zh, z — нет.",
        "Ба нафас гӯш диҳед: p, t, k, q, ch, c онро доранд; b, d, g, j, zh, z надоранд.",
        "听送气：p、t、k、q、ch、c 送气；b、d、g、j、zh、z 不送气。"),
    "pinyinCourse.tip.tongue": L(
        "Listen for where the tongue is: zh ch sh curled back, z c s behind the teeth, j q x flat with a smile.",
        "Слушайте положение языка: zh ch sh — загнут назад, z c s — у зубов, j q x — плоский, с улыбкой.",
        "Ба ҷойи забон гӯш диҳед: zh ch sh — ба қафо печида, z c s — назди дандонҳо, j q x — ҳамвор, бо табассум.",
        "听舌头的位置：zh ch sh 卷舌，z c s 舌尖抵齿，j q x 舌面平、嘴角像微笑。"),
    "pinyinCourse.tip.nl": L("n goes through the nose; l along the sides of the tongue.", "n — через нос; l — по бокам языка.",
                             "n — аз бинӣ; l — аз паҳлӯҳои забон.", "n 从鼻子出气，l 从舌头两边出气。"),
    "pinyinCourse.tip.r": L(
        "r is said like sh with the voice humming, the tongue curled back — it is not a rolled r.",
        "r произносится как sh, но со звоном голоса и загнутым языком — это не раскатистое р.",
        "r мисли sh гуфта мешавад, вале бо ларзиши овоз ва забони печида — ин r-и ғелонда нест.",
        "r 像 sh 一样卷舌，但声带振动，不是打舌的 r。"),
    "pinyinCourse.tip.initial": L("Only the first sound differs — listen to the very start.", "Различается только первый звук — слушайте самое начало.",
                                  "Танҳо овози аввал фарқ мекунад — ба оғоз гӯш диҳед.", "只有开头的音不同，注意听开头。"),
    "pinyinCourse.tip.nasal": L(
        "Listen to the end: -n stops at the front of the mouth, -ng rings at the back, like “song”.",
        "Слушайте конец: -n заканчивается спереди, -ng звучит в глубине, как в song.",
        "Ба охир гӯш диҳед: -n дар пеши даҳон қатъ мешавад, -ng дар қафо садо медиҳад.",
        "注意听结尾：-n 在前面收住，-ng 在后面，像 song 的结尾。"),
    "pinyinCourse.tip.umlaut": L("ü is i with rounded lips; u is said with the tongue back.", "ü — это i с округлёнными губами; u — с языком назад.",
                                 "ü — ин i бо лабони мудаввар; u бо забони ба қафо гуфта мешавад.", "ü 是圆唇的 i；u 舌头往后缩。"),
    "pinyinCourse.tip.final": L("Only the vowel part differs — listen after the first sound.", "Различается только гласная часть — слушайте после первого звука.",
                                "Танҳо қисми садонок фарқ мекунад — баъд аз овози аввал гӯш диҳед.", "只有韵母不同，注意听开头后面的部分。"),
    "pinyinCourse.rule.u_after_jqx": L(
        "After j, q, x and y, ü is written u without dots — these initials are never followed by a plain u.",
        "После j, q, x и y ü пишется как u без точек — с простым u эти инициали не сочетаются.",
        "Баъд аз j, q, x ва y ü бе нуқта ҳамчун u навишта мешавад — ин ибтидоҳо бо u-и оддӣ намеоянд.",
        "j、q、x、y 后面的 ü 去掉两点写成 u——这几个声母从来不跟 u 相拼。"),
    "pinyinCourse.rule.u_after_nl": L(
        "After n and l the dots stay: nǚ and lǜ are different from nù and lù.",
        "После n и l точки остаются: nǚ и lǜ — не то же, что nù и lù.",
        "Баъд аз n ва l нуқтаҳо мемонанд: nǚ ва lǜ аз nù ва lù фарқ мекунанд.",
        "n、l 后面保留两点：nǚ、lǜ 和 nù、lù 不一样。"),
    "pinyinCourse.rule.y_w": L(
        "With no initial, i becomes yi (or y-), u becomes wu (or w-), ü becomes yu.",
        "Без инициали i пишется yi (или y-), u — wu (или w-), ü — yu.",
        "Бе ибтидо i ҳамчун yi (ё y-), u ҳамчун wu (ё w-), ü ҳамчун yu навишта мешавад.",
        "没有声母时，i 写成 yi（或 y-），u 写成 wu（或 w-），ü 写成 yu。"),
    "pinyinCourse.rule.mark_a": L("The tone mark goes on a whenever there is one.", "Если есть a, знак тона ставится над ней.",
                                  "Агар a бошад, аломати оҳанг болои он гузошта мешавад.", "有 a 就标在 a 上。"),
    "pinyinCourse.rule.mark_oe": L("With no a, the mark goes on o or e.", "Если a нет, знак ставится над o или e.",
                                   "Агар a набошад, аломат болои o ё e гузошта мешавад.", "没有 a，就标在 o 或 e 上。"),
    "pinyinCourse.rule.mark_iu_ui": L("In iu and ui, the mark goes on the second letter: liù, guì.",
                                      "В iu и ui знак ставится над второй буквой: liù, guì.",
                                      "Дар iu ва ui аломат болои ҳарфи дуюм гузошта мешавад: liù, guì.",
                                      "iu、ui 标在后一个字母上：liù、guì。"),
    # A pronunciation / pinyin-course round's page title (it had no key, so
    # the raw "practice.title.pronunciation" was shown).
    "practice.title.pronunciation": L("Pronunciation · {{title}}", "Произношение · {{title}}", "Талаффуз · {{title}}",
                                      "发音 · {{title}}"),
    # ---- the questions (askText in components/CaseAndSound.jsx) ----
    "soundWorld.ask.pinyin_part_initial": L("Which is the initial of {{item}}?", "Какая инициаль у {{item}}?",
                                            "Ибтидои {{item}} кадом аст?", "{{item}} 的声母是哪个？"),
    "soundWorld.ask.pinyin_part_final": L("Which is the final of {{item}}?", "Какая финаль у {{item}}?",
                                          "Охири {{item}} кадом аст?", "{{item}} 的韵母是哪个？"),
    "soundWorld.ask.pinyin_tone_mark": L("Which tone is marked on {{item}}?", "Какой тон обозначен в {{item}}?",
                                         "Дар {{item}} кадом оҳанг нишон дода шудааст?", "{{item}} 标的是第几声？"),
    "soundWorld.ask.pinyin_spell": L("How is {{item}} written? (the number is the tone)",
                                     "Как записать {{item}}? (число — это тон)",
                                     "{{item}} чӣ тавр навишта мешавад? (рақам — оҳанг аст)",
                                     "{{item}} 怎么写？（数字是声调）"),
}
KEYS = list(S)

def section(lang):
    """The new top-level "pinyinCourse" object, nested from the dotted keys."""
    out = {}
    for dotted, value in S.items():
        if not dotted.startswith("pinyinCourse."):
            continue
        node = out
        *parents, leaf = dotted.split(".")[1:]
        for part in parents:
            node = node.setdefault(part, {})
        node[leaf] = value[lang]
    return out


if __name__ == "__main__":
    for lang in LANGS:
        path = os.path.join(LOCALES, f"{lang}.json")
        with open(path, encoding="utf-8", newline="") as f:
            raw = f.read()
        nl = "\r\n" if "\r\n" in raw else "\n"  # keep the file's own line endings
        lines = raw.split(nl)
        if '  "pinyinCourse": {' not in lines:
            # A new section, appended as the file's last object (2-space indent).
            end = max(i for i, line in enumerate(lines) if line == "}")
            body = json.dumps({"pinyinCourse": section(lang)}, ensure_ascii=False, indent=2).split("\n")[1:-1]
            lines[end - 1] = lines[end - 1].rstrip(",") + ","
            lines[end:end] = body
        for dotted, value in S.items():
            if not dotted.startswith("pinyinCourse."):
                put(lines, dotted, value[lang])
        text = nl.join(lines)
        json.loads(text)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print(f"updated {lang}.json")
