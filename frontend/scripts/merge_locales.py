"""Merge new i18n keys into all 4 locale JSON files at once.

Usage: define ENTRIES as {"dot.path.to.key": {"en": ..., "ru": ..., "tg": ..., "zh": ...}}
in a sibling file or inline, then run this module's merge(entries) function.
Never overwrites an existing key with an empty value; always overwrites with
a provided non-empty value (used to fix/extend existing pages too).
"""
import json
import os

LOCALES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "locales")
LANGS = ["en", "ru", "tg", "zh"]


def _set_path(d, dotted_path, value):
    parts = dotted_path.split(".")
    cur = d
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value


def merge(entries: dict):
    docs = {}
    for lang in LANGS:
        path = os.path.join(LOCALES_DIR, f"{lang}.json")
        with open(path, encoding="utf-8") as f:
            docs[lang] = json.load(f)

    count = 0
    for dotted_path, by_lang in entries.items():
        for lang in LANGS:
            value = by_lang.get(lang)
            if value is None:
                continue
            _set_path(docs[lang], dotted_path, value)
        count += 1

    for lang in LANGS:
        path = os.path.join(LOCALES_DIR, f"{lang}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(docs[lang], f, ensure_ascii=False, indent=2)
            f.write("\n")

    print(f"Merged {count} keys into {', '.join(LANGS)}.json")
