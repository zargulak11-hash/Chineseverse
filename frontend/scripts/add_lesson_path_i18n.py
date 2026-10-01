# -*- coding: utf-8 -*-
"""Adds the lesson-path strings (Lessons page, locked lesson, "next lesson")
to all four locale files (en/ru/tg/zh). Idempotent: re-running overwrites the
same keys with the same text. Run from frontend/: python scripts/add_lesson_path_i18n.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LOCALES = os.path.join(HERE, "..", "src", "locales")

T = {
    "en": {
        "pages.lessons": {
            "subtitle": "One lesson at a time: pass a lesson's practice round to open the next one.",
            "eyebrow": "Your learning path",
            "upNext": "Up next",
            "start": "Start lesson",
            "review": "Review",
            "open": "Open",
            "lockedReason": "Complete the previous lesson first.",
            "levelLocked": "Finish HSK {{level}} to unlock this level.",
            "readingHint": "Reading lesson · no practice round",
            "pathDone": "You've completed every lesson on the path. Keep your skills fresh in Review.",
            "completedKpi": "Lessons completed",
            "currentLevel": "Current level",
            "levelKpi": "This level",
            "hskProgress": "HSK progress",
            "keepSharp": "Keep it fresh",
            "reviewMistakes": "Review mistakes",
            "chooseLevel": "Choose an HSK level",
            "best": "Best: {{score}}%",
            "lessonsInLevel": "{{done}} of {{total}} lessons",
            "status": {"completed": "Completed", "current": "Up next", "available": "Open", "locked": "Locked"},
        },
        "pages.lessonDetail": {
            "lockedTitle": "This lesson is locked",
            "lockedText": "Complete the previous lesson first — your lesson path shows what to study next.",
            "backToPath": "Back to your lesson path",
        },
        "practice.nextLesson": "Next lesson",
    },
    "ru": {
        "pages.lessons": {
            "subtitle": "Урок за уроком: пройдите практику урока, чтобы открыть следующий.",
            "eyebrow": "Ваш учебный путь",
            "upNext": "Следующий шаг",
            "start": "Начать урок",
            "review": "Повторить",
            "open": "Открыть",
            "lockedReason": "Сначала пройдите предыдущий урок.",
            "levelLocked": "Завершите HSK {{level}}, чтобы открыть этот уровень.",
            "readingHint": "Урок для чтения · без практики",
            "pathDone": "Вы прошли все уроки пути. Поддерживайте навыки в разделе «Повторение».",
            "completedKpi": "Уроков пройдено",
            "currentLevel": "Текущий уровень",
            "levelKpi": "Этот уровень",
            "hskProgress": "Прогресс HSK",
            "keepSharp": "Закрепление",
            "reviewMistakes": "Разобрать ошибки",
            "chooseLevel": "Выберите уровень HSK",
            "best": "Лучший результат: {{score}}%",
            "lessonsInLevel": "{{done}} из {{total}} уроков",
            "status": {"completed": "Пройден", "current": "Следующий", "available": "Открыт", "locked": "Закрыт"},
        },
        "pages.lessonDetail": {
            "lockedTitle": "Этот урок пока закрыт",
            "lockedText": "Сначала пройдите предыдущий урок — на пути уроков видно, что изучать дальше.",
            "backToPath": "К пути уроков",
        },
        "practice.nextLesson": "Следующий урок",
    },
    "tg": {
        "pages.lessons": {
            "subtitle": "Дарс ба дарс: машқи дарсро супоред, то дарси навбатӣ кушода шавад.",
            "eyebrow": "Роҳи омӯзиши шумо",
            "upNext": "Қадами навбатӣ",
            "start": "Оғози дарс",
            "review": "Такрор",
            "open": "Кушодан",
            "lockedReason": "Аввал дарси қаблиро анҷом диҳед.",
            "levelLocked": "Барои кушодани ин сатҳ HSK {{level}}-ро анҷом диҳед.",
            "readingHint": "Дарси хониш · бе машқ",
            "pathDone": "Шумо ҳамаи дарсҳои роҳро анҷом додед. Малакаҳоро дар бахши «Такрор» нигоҳ доред.",
            "completedKpi": "Дарсҳои анҷомёфта",
            "currentLevel": "Сатҳи ҷорӣ",
            "levelKpi": "Ин сатҳ",
            "hskProgress": "Пешравии HSK",
            "keepSharp": "Мустаҳкамкунӣ",
            "reviewMistakes": "Таҳлили хатоҳо",
            "chooseLevel": "Сатҳи HSK-ро интихоб кунед",
            "best": "Беҳтарин: {{score}}%",
            "lessonsInLevel": "{{done}} аз {{total}} дарс",
            "status": {"completed": "Анҷомёфта", "current": "Навбатӣ", "available": "Кушода", "locked": "Баста"},
        },
        "pages.lessonDetail": {
            "lockedTitle": "Ин дарс ҳоло баста аст",
            "lockedText": "Аввал дарси қаблиро анҷом диҳед — роҳи дарсҳо нишон медиҳад, ки баъд чиро омӯзед.",
            "backToPath": "Бозгашт ба роҳи дарсҳо",
        },
        "practice.nextLesson": "Дарси навбатӣ",
    },
    "zh": {
        "pages.lessons": {
            "subtitle": "一课一课地学：通过本课的练习，即可解锁下一课。",
            "eyebrow": "你的学习路径",
            "upNext": "下一步",
            "start": "开始学习",
            "review": "复习",
            "open": "打开",
            "lockedReason": "请先完成上一课。",
            "levelLocked": "完成 HSK {{level}} 后即可解锁本级。",
            "readingHint": "阅读课 · 无练习",
            "pathDone": "你已完成路径上的所有课程。去复习巩固吧。",
            "completedKpi": "已完成课程",
            "currentLevel": "当前级别",
            "levelKpi": "本级进度",
            "hskProgress": "HSK 进度",
            "keepSharp": "巩固练习",
            "reviewMistakes": "复习错题",
            "chooseLevel": "选择 HSK 级别",
            "best": "最佳：{{score}}%",
            "lessonsInLevel": "{{done}} / {{total}} 课",
            "status": {"completed": "已完成", "current": "下一课", "available": "可学习", "locked": "未解锁"},
        },
        "pages.lessonDetail": {
            "lockedTitle": "本课尚未解锁",
            "lockedText": "请先完成上一课——学习路径会告诉你接下来学什么。",
            "backToPath": "返回学习路径",
        },
        "practice.nextLesson": "下一课",
    },
}


def set_path(d, dotted, value):
    parts = dotted.split(".")
    for p in parts[:-1]:
        d = d.setdefault(p, {})
    if isinstance(value, dict) and isinstance(d.get(parts[-1]), dict):
        merge(d[parts[-1]], value)
    else:
        d[parts[-1]] = value


def merge(dst, src):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            merge(dst[k], v)
        else:
            dst[k] = v


for loc, entries in T.items():
    path = os.path.join(LOCALES, f"{loc}.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for key, value in entries.items():
        set_path(data, key, value)
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"updated {loc}.json")
