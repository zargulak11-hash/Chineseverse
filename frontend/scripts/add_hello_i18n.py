# -*- coding: utf-8 -*-
"""Adds the Dashboard greeting strings (pages/Dashboard.jsx GreetingHero)
into "dashboard" of all four locale files, as new lines. Idempotent.
Run from frontend/: python scripts/add_hello_i18n.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_recall_i18n import LANGS, LOCALES, put  # noqa: E402


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


S = {
    "dashboard.helloMorning": L("Good morning", "Доброе утро", "Субҳ ба хайр", "早上好"),
    "dashboard.helloAfternoon": L("Good afternoon", "Добрый день", "Рӯз ба хайр", "下午好"),
    "dashboard.helloEvening": L("Good evening", "Добрый вечер", "Шом ба хайр", "晚上好"),
    # The gloss of 今天也要加油！ (shown under it; none on a Chinese screen).
    "dashboard.helloCheer": L("Let's keep going today too!", "И сегодня — вперёд!", "Имрӯз ҳам пеш меравем!", ""),
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
