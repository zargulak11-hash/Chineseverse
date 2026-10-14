# -*- coding: utf-8 -*-
"""Adds the strings of the product-wide page redesign (Roleplay, Tone Coach,
Mistakes, ...) into all four locale files, as new lines inside their existing
sections. Idempotent: keys already present are skipped.
Run from frontend/: python scripts/add_redesign_i18n.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_recall_i18n import LANGS, LOCALES, put  # noqa: E402


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


S = {
    # ---- Roleplay (pages/Roleplay.jsx) ----
    "roleplay.statOpen": L("Scenes open", "Открыто сцен", "Саҳнаҳои кушода", "已开放场景"),
    "roleplay.statPlayed": L("Conversations finished", "Завершено разговоров", "Суҳбатҳои анҷомёфта", "已完成对话"),
    "roleplay.pickScene": L("Choose where to talk", "Выберите, где поговорить", "Интихоб кунед, ки дар куҷо гап мезанед", "选择对话场景"),
    "roleplay.youMeet": L("You'll talk to", "Ваш собеседник:", "Ҳамсуҳбати шумо:", "对话对象："),
    "roleplay.noRecent": L(
        "No conversations yet — pick a scene to start your first.",
        "Разговоров пока нет — выберите сцену, чтобы начать первый.",
        "Ҳоло суҳбате нест — барои оғози аввалин саҳнаеро интихоб кунед.",
        "还没有对话——选一个场景开始吧。"),
    "roleplay.goalsMet": L("{{met}}/{{total}} goals", "Целей: {{met}}/{{total}}", "Ҳадафҳо: {{met}}/{{total}}", "目标 {{met}}/{{total}}"),
    "roleplay.useSuggestion": L(
        "Put this reply in the box — you can change it before sending",
        "Вставить ответ в поле — его можно изменить перед отправкой",
        "Ин ҷавобро ба майдон гузоштан — пеш аз фиристодан тағйир додан мумкин аст",
        "把这句话放进输入框——发送前还可以修改"),
    "roleplay.hinting": L("Thinking…", "Подбираю…", "Фикр мекунам…", "正在想…"),
    # ---- Tone Coach (pages/ToneCoach.jsx) ----
    "toneCoach.stepsLabel": L("Steps", "Шаги", "Қадамҳо", "步骤"),
    "toneCoach.stepListen": L("Listen", "Послушайте", "Гӯш кунед", "听"),
    "toneCoach.stepSay": L("Say it", "Произнесите", "Талаффуз кунед", "说"),
    "toneCoach.stepCompare": L("Compare", "Сравните", "Муқоиса кунед", "对比"),
    "toneCoach.legendTarget": L("The tone's shape", "Форма тона", "Шакли оҳанг", "声调的形状"),
    "toneCoach.legendVoice": L("Your voice", "Ваш голос", "Овози шумо", "你的声音"),
    # ---- Practice / Review (pages/Practice.jsx) ----
    "practice.keysHint": L(
        "Tip: press 1–{{n}} to answer, Enter for the next question.",
        "Совет: нажмите 1–{{n}}, чтобы ответить, и Enter — к следующему вопросу.",
        "Маслиҳат: барои ҷавоб 1–{{n}}-ро пахш кунед, барои саволи навбатӣ Enter.",
        "小提示：按 1–{{n}} 作答，按 Enter 进入下一题。"),
    # ---- Vocabulary as a dictionary (pages/Vocabulary.jsx) ----
    "pages.vocabulary.kpiWords": L("Words in this level", "Слов на уровне", "Калимаҳои сатҳ", "本级词数"),
    "pages.vocabulary.kpiKnown": L("You know", "Вы знаете", "Шумо медонед", "已掌握"),
    "pages.vocabulary.searchPlaceholder": L(
        "Search: 你好, nihao or a meaning", "Поиск: 你好, nihao или значение",
        "Ҷустуҷӯ: 你好, nihao ё маъно", "搜索：汉字、拼音或释义"),
    "pages.vocabulary.searchLabel": L("Search the words of HSK {{level}}", "Поиск по словам HSK {{level}}",
                                      "Ҷустуҷӯ дар калимаҳои HSK {{level}}", "搜索 HSK {{level}} 的词语"),
    "pages.vocabulary.levelLabel": L("HSK level", "Уровень HSK", "Сатҳи HSK", "HSK 等级"),
    "pages.vocabulary.listLabel": L("Words", "Слова", "Калимаҳо", "词语"),
    "pages.vocabulary.found": L(
        {"one": "{{count}} word found", "other": "{{count}} words found"},
        {"one": "Найдено {{count}} слово", "few": "Найдено {{count}} слова", "many": "Найдено {{count}} слов", "other": "Найдено {{count}} слова"},
        {"one": "{{count}} калима ёфт шуд", "other": "{{count}} калима ёфт шуд"},
        {"other": "找到 {{count}} 个词"}),
    "pages.vocabulary.noMatch": L(
        "Nothing at this level matches. Try another spelling or another HSK level.",
        "На этом уровне ничего не найдено. Попробуйте другое написание или другой уровень HSK.",
        "Дар ин сатҳ чизе ёфт нашуд. Навишти дигар ё сатҳи дигари HSK-ро санҷед.",
        "本级没有匹配的词。换个写法或换个 HSK 等级试试。"),
    "pages.vocabulary.traditional": L("Traditional", "Традиционное", "Анъанавӣ", "繁体"),
    "pages.vocabulary.example": L("In a sentence", "В предложении", "Дар ҷумла", "例句"),
    "pages.vocabulary.characters": L("Written with", "Пишется иероглифами", "Бо иероглифҳо навишта мешавад", "组成的汉字"),
    "pages.vocabulary.openChar": L("Open the character {{char}}", "Открыть иероглиф {{char}}", "Кушодани иероглифи {{char}}", "查看汉字 {{char}}"),
    "pages.vocabulary.related": L("Words that share a character", "Слова с тем же иероглифом", "Калимаҳо бо ҳамон иероглиф", "含相同汉字的词"),
    "pages.vocabulary.yourMastery": L("Your mastery", "Ваше освоение", "Азхудкунии шумо", "你的掌握度"),
    "pages.vocabulary.st_new": L("new", "новое", "нав", "未学"),
    "pages.vocabulary.st_learning": L("learning", "изучается", "дар омӯзиш", "学习中"),
    "pages.vocabulary.st_reviewing": L("reviewing", "на повторении", "дар такрор", "复习中"),
    "pages.vocabulary.st_mastered": L("mastered", "освоено", "азхудшуда", "已掌握"),
    "pages.vocabulary.st_due": L("due", "пора повторить", "вақти такрор", "待复习"),
    "pages.vocabulary.st_slipping": L("slipping", "забывается", "фаромӯш мешавад", "快忘了"),
    # ---- One Sentence (pages/SentenceLesson.jsx) ----
    "sentenceLesson.readTitle": L(
        "Read it — tap a word", "Прочитайте — нажмите на слово", "Хонед — ба калима пахш кунед", "读一读——点击词语"),
    "sentenceLesson.legend": L(
        "What the underline under a word means", "Что значит подчёркивание под словом",
        "Хати зери калима чӣ маъно дорад", "词语下划线的含义"),
    # ---- Mistake notebook (pages/Mistakes.jsx) ----
    "pages.mistakes.listen": L("Listen", "Прослушать", "Гӯш кардан", "听"),
    "pages.mistakes.missedTimes": L(
        {"one": "Missed {{count}} time", "other": "Missed {{count}} times"},
        {"one": "Ошибка {{count}} раз", "few": "Ошибка {{count}} раза", "many": "Ошибка {{count}} раз", "other": "Ошибка {{count}} раза"},
        {"one": "{{count}} бор хато", "other": "{{count}} бор хато"},
        {"other": "错了 {{count}} 次"}),
    "pages.mistakes.tabAll": L("All", "Все", "Ҳама", "全部"),
    "pages.mistakes.filterLabel": L("Show mistakes of one kind", "Показать ошибки одного вида", "Нишон додани хатоҳои як навъ", "按类型查看"),
    "pages.mistakes.focusStart": L("Test yourself", "Проверить себя", "Худро санҷед", "自我检测"),
    "pages.mistakes.focusTitle": L("Test yourself", "Проверьте себя", "Худро санҷед", "自我检测"),
    "pages.mistakes.focusCount": L("{{n}} of {{total}}", "{{n}} из {{total}}", "{{n}} аз {{total}}", "第 {{n}} / {{total}} 个"),
    "pages.mistakes.focusPrompt": L(
        "Say or write the answer to yourself, then check.",
        "Ответьте про себя или запишите, затем проверьте.",
        "Ҷавобро дар дил гӯед ё нависед, баъд санҷед.",
        "先自己说出或写出答案，再看答案。"),
    "pages.mistakes.reveal": L("Show the answer", "Показать ответ", "Ҷавобро нишон диҳед", "显示答案"),
    "pages.mistakes.lastTime": L("Last time you answered", "В прошлый раз вы ответили", "Дафъаи гузашта шумо ҷавоб додед", "上次你的回答"),
    "pages.mistakes.focusNext": L("Next", "Дальше", "Минбаъда", "下一个"),
    "pages.mistakes.focusClose": L("Back to the notebook", "Вернуться к тетради", "Бозгашт ба дафтар", "返回错题本"),
    "pages.mistakes.focusDone": L(
        "That's all of them. Now earn them back where it counts — in Review.",
        "Это все. Теперь закрепите их там, где это засчитывается, — в повторении.",
        "Ҳамааш ҳамин. Акнун онҳоро дар ҷое баргардонед, ки ҳисоб мешавад — дар такрор.",
        "全部看完了。现在去复习里真正把它们赢回来吧。"),
    "pages.mistakes.focusNote": L(
        "A self-check: nothing here is saved. A mistake is cleared only by answering it correctly in practice.",
        "Это самопроверка: здесь ничего не сохраняется. Ошибка исчезает, только когда вы правильно ответите в практике.",
        "Ин худсанҷӣ аст: дар ин ҷо чизе сабт намешавад. Хато танҳо вақте пок мешавад, ки шумо дар машқ дуруст ҷавоб диҳед.",
        "这是自我检测：这里不保存任何结果。只有在练习中答对，错题才会被清除。"),
    "pages.mistakes.progressTitle": L("Earned back", "Исправлено", "Ислоҳшуда", "已攻克"),
    "pages.mistakes.progressLine": L(
        "Mistakes and mix-ups you have since answered right in practice.",
        "Ошибки и путаницы, на которые вы с тех пор правильно ответили в практике.",
        "Хатоҳо ва омехтагиҳое, ки шумо баъдан дар машқ дуруст ҷавоб додед.",
        "之后在练习中答对了的错题和易混词。"),
}
KEYS = list(S)

if __name__ == "__main__":
    for lang in LANGS:
        path = os.path.join(LOCALES, f"{lang}.json")
        with open(path, encoding="utf-8", newline="") as f:
            lines = f.read().split("\r\n")
        for dotted, value in S.items():
            put(lines, dotted, value[lang])
        text = "\r\n".join(lines)
        json.loads(text)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print(f"updated {lang}.json")
