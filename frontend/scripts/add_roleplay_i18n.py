# -*- coding: utf-8 -*-
"""Adds the AI roleplay strings (pages/Roleplay.jsx) to all four locale
files, as new lines only: a top-level "roleplay" block, plus one key each in
"nav" and "pages.progress.section". Idempotent. Run from frontend/:
python scripts/add_roleplay_i18n.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_recall_i18n import LANGS, LOCALES, put  # noqa: E402


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


def P(en, ru, tg, zh):
    """Plural forms: en one/other, ru one/few/many/other, tg one/other, zh other."""
    return {"en": en, "ru": ru, "tg": tg, "zh": zh, "_plural": True}


S = {
    "title": L("AI Roleplay", "Ролевые диалоги с ИИ", "Муколамаҳои нақшӣ бо ИИ", "AI 情景对话"),
    "subtitle": L(
        "Talk your way through real situations in your own words. Your partner answers what you actually said, corrects your Chinese and explains why.",
        "Проходите реальные ситуации своими словами. Собеседник отвечает на то, что вы сказали, исправляет ваш китайский и объясняет почему.",
        "Ҳолатҳои воқеиро бо суханони худ гузаред. Ҳамсуҳбат ба он чизе, ки гуфтед, ҷавоб медиҳад, чинии шуморо ислоҳ мекунад ва сабабашро мефаҳмонад.",
        "用你自己的话完成真实的生活场景。对方会回应你说的话，纠正你的中文，并告诉你为什么。"),
    "unavailableTitle": L("AI conversations aren't available right now", "Диалоги с ИИ сейчас недоступны",
                          "Муколамаҳо бо ИИ ҳоло дастрас нестанд", "AI 对话现在不能用"),
    "unavailableText": L(
        "This needs the AI service, which this server can't reach at the moment. The scripted scenes in Real Chinese work without it.",
        "Для этого нужен сервис ИИ, а сервер сейчас не может к нему подключиться. Готовые сцены в разделе «Живой китайский» работают без него.",
        "Барои ин хидмати ИИ лозим аст, ки сервер ҳоло ба он пайваст шуда наметавонад. Саҳнаҳои тайёр дар «Чинии зинда» бе он кор мекунанд.",
        "这个功能需要 AI 服务，服务器现在连不上。“真实中文”里的固定场景不需要 AI，可以继续练习。"),
    "toScenes": L("Open Real Chinese scenes", "Открыть сцены «Живого китайского»", "Саҳнаҳои «Чинии зинда»-ро кушоед",
                  "打开真实中文场景"),
    "start": L("Start", "Начать", "Оғоз", "开始"),
    "starting": L("Starting…", "Начинаем…", "Оғоз мешавад…", "正在开始…"),
    "locked": L("Opens at HSK {{level}}", "Откроется на HSK {{level}}", "Дар HSK {{level}} кушода мешавад", "HSK {{level}} 开放"),
    "played": P({"one": "Played once", "other": "Played {{count}} times"},
                {"one": "Пройдено {{count}} раз", "few": "Пройдено {{count}} раза", "many": "Пройдено {{count}} раз",
                 "other": "Пройдено {{count}} раза"},
                {"one": "{{count}} бор гузашт", "other": "{{count}} бор гузашт"},
                {"other": "已练习 {{count}} 次"}),
    "goals": L("Your goals", "Ваши цели", "Мақсадҳои шумо", "你的目标"),
    "recent": L("Your recent conversations", "Ваши недавние диалоги", "Муколамаҳои охирини шумо", "最近的对话"),
    "continue": L("Continue", "Продолжить", "Идома додан", "继续"),
    "seeSummary": L("See summary", "Итоги", "Натиҷаҳо", "查看总结"),
    "messages": P({"one": "{{count}} message", "other": "{{count}} messages"},
                  {"one": "{{count}} сообщение", "few": "{{count}} сообщения", "many": "{{count}} сообщений",
                   "other": "{{count}} сообщения"},
                  {"one": "{{count}} паём", "other": "{{count}} паём"},
                  {"other": "{{count}} 条消息"}),
    "showPinyin": L("Pinyin", "Пиньинь", "Пинйин", "拼音"),
    "showTranslation": L("Translation", "Перевод", "Тарҷума", "翻译"),
    "listen": L("Listen", "Прослушать", "Гӯш кардан", "听一听"),
    "inputLabel": L("Your reply in Chinese", "Ваш ответ на китайском", "Ҷавоби шумо ба забони чинӣ", "用中文回答"),
    "placeholder": L("Write in Chinese — characters or pinyin…", "Пишите по-китайски — иероглифами или пиньинем…",
                     "Ба чинӣ нависед — бо иероглифҳо ё пинйин…", "用汉字或拼音写…"),
    "send": L("Send", "Отправить", "Фиристодан", "发送"),
    "hint": L("Hint", "Подсказка", "Маслиҳат", "提示"),
    "hintLine": L("You could say:", "Можно сказать:", "Метавонед гӯед:", "你可以说："),
    "hintGoal": L("Next goal: {{goal}}", "Следующая цель: {{goal}}", "Мақсади навбатӣ: {{goal}}", "下一个目标：{{goal}}"),
    "thinking": L("Your partner is answering…", "Собеседник отвечает…", "Ҳамсуҳбат ҷавоб медиҳад…", "对方正在回答…"),
    "slow": L("The AI service is busy — this can take up to a minute.", "Сервис ИИ сейчас загружен — это может занять до минуты.",
              "Хидмати ИИ банд аст — ин метавонад то як дақиқа тӯл кашад.", "AI 服务现在比较忙，可能需要一分钟左右。"),
    "corrected": L("Better:", "Лучше так:", "Беҳтараш:", "更好的说法："),
    "wellSaid": L("Well said", "Отлично сказано", "Хуб гуфтед", "说得好"),
    "keyWords": L("Key words", "Ключевые слова", "Калимаҳои асосӣ", "关键词"),
    "save": L("Save to review", "В повторение", "Ба такрор илова кунед", "加入复习"),
    "saved": L("In your review", "Уже в повторении", "Дар такрори шумо", "已在复习中"),
    "turnsLeft": L("Messages left", "Осталось сообщений", "Паёмҳои боқимонда", "剩余消息"),
    "finish": L("Finish conversation", "Завершить диалог", "Анҷоми муколама", "结束对话"),
    "finishing": L("Finishing…", "Завершаем…", "Анҷом дода мешавад…", "正在结束…"),
    "summaryTitle": L("How it went", "Как всё прошло", "Чӣ тавр гузашт", "对话总结"),
    "statMessages": L("Messages", "Сообщения", "Паёмҳо", "消息"),
    "statAccepted": L("Correct", "Верно", "Дуруст", "正确"),
    "statGoals": L("Goals", "Цели", "Мақсадҳо", "目标"),
    "strengths": L("What went well", "Что получилось", "Чӣ хуб шуд", "做得好的地方"),
    "nextTime": L("Next time", "В следующий раз", "Дафъаи оянда", "下次可以"),
    "corrections": L("Your corrections", "Ваши исправления", "Ислоҳҳои шумо", "你的纠正"),
    "noCorrections": L("No corrections — every message was correct.", "Исправлений нет — все сообщения были верными.",
                       "Ислоҳ нест — ҳамаи паёмҳо дуруст буданд.", "没有需要纠正的——每条消息都是对的。"),
    "again": L("Play again", "Сыграть ещё раз", "Боз бозӣ кунед", "再练一次"),
    "all": L("All scenarios", "Все сценарии", "Ҳамаи сенарияҳо", "全部场景"),
    "aiNote": L("Replies, corrections and summaries are written by AI and can occasionally be wrong.",
                "Ответы, исправления и итоги пишет ИИ, и иногда он может ошибаться.",
                "Ҷавобҳо, ислоҳҳо ва хулосаҳоро ИИ менависад ва баъзан метавонад хато кунад.",
                "回答、纠正和总结由 AI 生成，偶尔可能有错误。"),
    "speakOrType": L("Speak or type", "Говорите или пишите", "Гӯед ё нависед", "说或者写"),
}
EXTRA = {
    "nav.roleplay": L("AI Roleplay", "Диалоги с ИИ", "Муколама бо ИИ", "AI 情景对话"),
    "pages.progress.section.roleplay": L("AI Roleplay", "Диалоги с ИИ", "Муколама бо ИИ", "AI 情景对话"),
}


def _tree(lang):
    out = {}
    for k, v in S.items():
        if v.get("_plural"):
            for form, text in v[lang].items():
                out[f"{k}_{form}"] = text
        else:
            out[k] = v[lang]
    return out


def keys():
    return [f"roleplay.{k}" for k in S] + list(EXTRA)


KEYS = keys()


if __name__ == "__main__":
    for lang in LANGS:
        path = os.path.join(LOCALES, f"{lang}.json")
        with open(path, encoding="utf-8", newline="") as f:
            lines = f.read().split("\r\n")
        if '  "roleplay": {' not in lines:
            # A new top-level object, inserted before the file's closing brace.
            end = max(i for i, l in enumerate(lines) if l == "}")
            block = json.dumps({"roleplay": _tree(lang)}, ensure_ascii=False, indent=2).split("\n")[1:-1]
            lines[end - 1] = lines[end - 1].rstrip(",") + ","
            lines[end:end] = block
        for dotted, value in EXTRA.items():
            put(lines, dotted, value[lang])
        text = "\r\n".join(lines)
        json.loads(text)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print(f"updated {lang}.json")
