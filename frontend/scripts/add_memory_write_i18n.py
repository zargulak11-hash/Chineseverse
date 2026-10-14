# -*- coding: utf-8 -*-
"""Adds the write-from-memory strings (components/HanziTrace.jsx,
HanziDetail.jsx) into "pages.hanzi" of all four locale files, as new lines.
Idempotent. Run from frontend/: python scripts/add_memory_write_i18n.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_recall_i18n import LANGS, LOCALES, put  # noqa: E402


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


S = {
    "pages.hanzi.writeFromMemory": L("Write from memory", "Написать по памяти", "Аз ёд навиштан", "凭记忆写"),
    "pages.hanzi.memoryPrompt": L("Write the character for:", "Напишите иероглиф:", "Иероглифро нависед:", "写出这个字："),
    "pages.hanzi.memoryStart": L("Start writing", "Начать писать", "Навиштанро оғоз кунед", "开始写"),
    "pages.hanzi.memoryHint": L("No outline to follow. A stroke's hint appears after 3 misses — and counts as mistakes.",
                                "Контура нет. Подсказка черты появится после 3 ошибок — и они засчитаются.",
                                "Контур нест. Маслиҳати хат пас аз 3 хато пайдо мешавад — ва ҳамчун хато ҳисоб мешавад.",
                                "没有描红。一笔错三次后会出现提示，错误也会被记录。"),
    "pages.hanzi.memoryCount": L("Written from memory: {{count}}", "Написано по памяти: {{count}}", "Аз ёд навишта шуд: {{count}}",
                                 "凭记忆写过：{{count}}次"),
    "pages.hanzi.memoryWhy": L("Writing counts as mastered once you have written it from memory.",
                               "Письмо считается выученным, когда вы написали иероглиф по памяти.",
                               "Навиштан вақте азхудшуда ҳисоб мешавад, ки иероглифро аз ёд навиштед.",
                               "凭记忆写出来以后，书写才算掌握。"),
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
