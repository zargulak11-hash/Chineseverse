# -*- coding: utf-8 -*-
"""Adds the strings of the learning-path pass (writing feedback, the skill
check for learners who already know some Chinese, ...) into all four locale
files, as new lines inside their existing sections. Idempotent: keys already
present are skipped. Run from frontend/: python scripts/add_learning_i18n.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_recall_i18n import LANGS, LOCALES, put  # noqa: E402


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


S = {
    # ---- writing a character (components/HanziTrace.jsx) ----
    "pages.hanzi.missStroke": L(
        "Stroke {{n}} of {{total}} didn't match. Check where it starts and which stroke comes next in the order you watched.",
        "Черта {{n}} из {{total}} не совпала. Проверьте, где она начинается и какая черта идёт следующей по порядку.",
        "Хати {{n}} аз {{total}} мувофиқ наомад. Санҷед, ки он аз куҷо сар мешавад ва кадом хат бо тартиб баъд меояд.",
        "第 {{n}} 笔（共 {{total}} 笔）不对。看看这一笔从哪里起笔，按笔顺下一笔是哪一笔。"),
    "pages.hanzi.missBackwards": L(
        "Stroke {{n}} of {{total}} has the right shape but the wrong direction: strokes go left to right and top to bottom.",
        "У черты {{n}} из {{total}} верная форма, но неверное направление: черты пишутся слева направо и сверху вниз.",
        "Хати {{n}} аз {{total}} шакли дуруст дорад, вале самти нодуруст: хатҳо аз чап ба рост ва аз боло ба поён навишта мешаванд.",
        "第 {{n}} 笔（共 {{total}} 笔）形状对，方向反了：笔画从左到右、从上到下写。"),
    "pages.hanzi.missHint": L(
        "The hint now shows where this stroke goes.",
        "Теперь подсказка показывает, где проходит эта черта.",
        "Акнун ишора нишон медиҳад, ки ин хат аз куҷо мегузарад.",
        "现在提示会显示这一笔的位置。"),
    # ---- testing out of a level (services/hsk_exam.test_out_levels) ----
    "journey.next.testout": L("Test out of HSK {{level}}", "Экзамен экстерном: HSK {{level}}",
                              "Имтиҳони берун аз навбат: HSK {{level}}", "跳级测试：HSK {{level}}"),
    "journey.nextWhy.testout": L(
        "Your results show you already know more than HSK {{from}} lessons. Pass the HSK {{level}} exam and your "
        "lessons continue after it — no need to repeat what you know.",
        "Ваши результаты показывают, что вы знаете больше уроков HSK {{from}}. Сдайте экзамен HSK {{level}} — и "
        "уроки продолжатся после него, без повторения того, что вы уже знаете.",
        "Натиҷаҳои шумо нишон медиҳанд, ки шумо аз дарсҳои HSK {{from}} бештар медонед. Имтиҳони HSK {{level}}-ро "
        "супоред — дарсҳо баъд аз он идома меёбанд, бе такрори он чи ки медонед.",
        "你的成绩说明你已经超过了 HSK {{from}} 的课程。通过 HSK {{level}} 考试，课程就从它后面继续，不用重学已经会的内容。"),
    "exam.testOutTitle": L("Test out of HSK {{level}}", "Экзамен экстерном: HSK {{level}}",
                           "Имтиҳони берун аз навбат: HSK {{level}}", "跳级测试：HSK {{level}}"),
    "exam.testOutBody": L(
        "You haven't finished this level's lessons. If you already know HSK {{level}}, pass this exam and your path "
        "moves on to HSK {{next}}; the skipped lessons stay open to read and practise. If you don't pass, nothing "
        "changes — your lessons stay exactly as they are.",
        "Уроки этого уровня ещё не пройдены. Если вы уже знаете HSK {{level}}, сдайте этот экзамен — и ваш путь "
        "продолжится с HSK {{next}}; пропущенные уроки останутся открытыми. Если не сдадите, ничего не изменится — "
        "уроки останутся как есть.",
        "Дарсҳои ин сатҳ ҳанӯз тамом нашудаанд. Агар шумо HSK {{level}}-ро аллакай донед, ин имтиҳонро супоред — роҳи "
        "шумо аз HSK {{next}} идома меёбад; дарсҳои гузошташуда кушода мемонанд. Агар нагузаред, ҳеҷ чиз тағйир "
        "намеёбад — дарсҳо ҳамон тавр мемонанд.",
        "这一级的课还没学完。如果你已经掌握了 HSK {{level}}，通过这个考试，你的学习路线就从 HSK {{next}} 继续；跳过的课仍然可以学习和练习。"
        "没通过也没关系，课程保持原样。"),
    "exam.testOutOffer": L(
        "Already know this? Take a level's exam to skip ahead:",
        "Уже знаете это? Сдайте экзамен уровня, чтобы перейти дальше:",
        "Инро аллакай медонед? Барои пеш рафтан имтиҳони сатҳро супоред:",
        "已经会了？参加这一级的考试，直接往后学："),
    "exam.testOutLevel": L("Test out of HSK {{level}}", "Экстерном: HSK {{level}}", "Берун аз навбат: HSK {{level}}",
                           "跳级测试 HSK {{level}}"),
    # ---- the skill check (components/SkillCheck.jsx, services/diagnostic.py) ----
    "practice.title.diagnostic": L("Skill check · HSK {{level}}", "Проверка навыков · HSK {{level}}",
                                   "Санҷиши малакаҳо · HSK {{level}}", "技能检测 · HSK {{level}}"),
    "journey.next.checkskill": L("Practise {{skill}}", "Потренируйте: {{skill}}", "Машқ кунед: {{skill}}", "练习：{{skill}}"),
    "journey.nextWhy.checkskill": L(
        "In your skill check you got {{correct}} of {{total}} right here — the weakest of your skills. A short round now.",
        "В проверке навыков здесь было {{correct}} из {{total}} верных ответов — это ваш самый слабый навык. Короткий раунд сейчас.",
        "Дар санҷиши малакаҳо дар ин ҷо {{correct}} аз {{total}} ҷавоби дуруст доштед — ин заифтарин малакаи шумост. Ҳозир як даври кӯтоҳ.",
        "技能检测里这一项你答对了 {{total}} 题中的 {{correct}} 题，是你最弱的一项。现在练一小轮吧。"),
    "skillCheck.title": L("Skill check", "Проверка навыков", "Санҷиши малакаҳо", "技能检测"),
    "skillCheck.body": L(
        "12 questions at one HSK level, two for each skill: words, listening, characters, tones, grammar and recalling "
        "words from memory. You'll see which skills you have and which need practice — and the next step follows it.",
        "12 вопросов одного уровня HSK, по два на каждый навык: слова, аудирование, иероглифы, тоны, грамматика и "
        "вспоминание слов по памяти. Вы увидите, какие навыки уже есть, а какие нужно тренировать, — и следующий шаг "
        "будет подобран по результату.",
        "12 савол дар як сатҳи HSK, барои ҳар малака ду савол: калимаҳо, шунидан, иероглифҳо, оҳангҳо, грамматика ва "
        "аз хотир ёд овардани калимаҳо. Шумо мебинед, ки кадом малакаҳо доред ва кадомашро машқ кардан лозим аст — ва "
        "қадами навбатӣ аз рӯи натиҷа интихоб мешавад.",
        "同一个 HSK 等级的 12 道题，每项技能两道：词语、听力、汉字、声调、语法和凭记忆写词。你会看到哪些已经会了、哪些需要练习，下一步也会据此安排。"),
    "skillCheck.start": L("Start the skill check", "Начать проверку", "Санҷишро оғоз кунед", "开始检测"),
    "skillCheck.again": L("Check again", "Проверить снова", "Боз санҷед", "再测一次"),
    "skillCheck.levelLabel": L("Level of the check", "Уровень проверки", "Сатҳи санҷиш", "检测等级"),
    "skillCheck.last": L("Last check: HSK {{level}}", "Последняя проверка: HSK {{level}}", "Санҷиши охирин: HSK {{level}}",
                         "上次检测：HSK {{level}}"),
    "skillCheck.score": L("{{correct}}/{{total}} right", "{{correct}}/{{total}} верно", "{{correct}}/{{total}} дуруст",
                          "答对 {{correct}}/{{total}}"),
    "skillCheck.practise": L("Practise this", "Потренировать", "Машқ кардан", "去练习"),
    "skillCheck.weakLeft": L(
        {"one": "{{count}} skill still needs practice since the check.", "other": "{{count}} skills still need practice since the check."},
        {"one": "После проверки {{count}} навык ещё нужно потренировать.", "few": "После проверки {{count}} навыка ещё нужно потренировать.",
         "many": "После проверки {{count}} навыков ещё нужно потренировать.", "other": "После проверки {{count}} навыка ещё нужно потренировать."},
        {"one": "Пас аз санҷиш {{count}} малака ҳанӯз машқ талаб мекунад.", "other": "Пас аз санҷиш {{count}} малака ҳанӯз машқ талаб мекунад."},
        {"other": "检测后还有 {{count}} 项技能需要练习。"}),
    "skillCheck.noneWeak": L(
        "No weak skill left from the last check. Check again whenever you want to see where you stand.",
        "После последней проверки слабых навыков не осталось. Проверьте снова, когда захотите узнать свой уровень.",
        "Аз санҷиши охирин малакаи заиф намонд. Ҳар вақт хоҳед, боз санҷед.",
        "上次检测的弱项都已经练过了。想知道自己的水平，随时可以再测。"),
    "skillCheck.resultTitle": L("Your skills at this level", "Ваши навыки на этом уровне", "Малакаҳои шумо дар ин сатҳ",
                                "你在这个等级的各项技能"),
    "skillCheck.resultBody": L(
        "Fewer than half right is marked as needing practice. Your next step now starts with the weakest one.",
        "Меньше половины верных ответов — навык нужно тренировать. Следующий шаг теперь начнётся с самого слабого.",
        "Камтар аз нисфи ҷавобҳо дуруст бошад — малака машқ талаб мекунад. Қадами навбатӣ аз заифтарин сар мешавад.",
        "答对不到一半的技能需要练习。下一步会从最弱的一项开始。"),
}
KEYS = list(S)
NEW_SECTIONS = ("skillCheck",)  # top-level objects this script creates


def section(name, lang):
    """A new top-level object built from the dotted keys under `name`."""
    out = {}
    for dotted, value in S.items():
        head, leaf = dotted.split(".", 1)
        if head != name:
            continue
        v = value[lang]
        if isinstance(v, str):
            out[leaf] = v
        else:
            out.update({f"{leaf}_{form}": x for form, x in v.items()})
    return out

if __name__ == "__main__":
    for lang in LANGS:
        path = os.path.join(LOCALES, f"{lang}.json")
        with open(path, encoding="utf-8", newline="") as f:
            raw = f.read()
        nl = "\r\n" if "\r\n" in raw else "\n"  # keep the file's own line endings
        lines = raw.split(nl)
        for name in NEW_SECTIONS:
            if f'  "{name}": {{' not in lines:
                end = max(i for i, line in enumerate(lines) if line == "}")
                body = json.dumps({name: section(name, lang)}, ensure_ascii=False, indent=2).split("\n")[1:-1]
                lines[end - 1] = lines[end - 1].rstrip(",") + ","
                lines[end:end] = body
        for dotted, value in S.items():
            if dotted.split(".")[0] not in NEW_SECTIONS:
                put(lines, dotted, value[lang])
        text = nl.join(lines)
        json.loads(text)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print(f"updated {lang}.json")
