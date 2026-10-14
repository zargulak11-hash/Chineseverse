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
