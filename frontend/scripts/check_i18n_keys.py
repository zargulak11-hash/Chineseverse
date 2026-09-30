# -*- coding: utf-8 -*-
"""Fails if any translation key used in src/ is missing from any locale.

Checks every literal t("a.b.c") call, plus the dynamic key families built
from template strings that this script knows how to expand (lesson status,
practice question types/titles, companion moods/voices).
Run from frontend/: python scripts/check_i18n_keys.py
"""
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
LOCALES = ("en", "ru", "tg", "zh")

DYNAMIC = (
    [f"lessonStatus.{s}" for s in ("not_started", "in_progress", "completed")]
    + [f"practice.title.{s}" for s in ("vocab", "hanzi", "grammar", "lesson", "review")]
    + [f"practice.q.{q}" for q in ("meaning_to_word", "word_to_meaning", "listen_to_word",
                                   "char_to_meaning", "char_to_pinyin", "example_to_point")]
    + [f"companionReact.{m}" for m in ("happy", "excited", "proud", "celebrating", "encouraging",
                                       "worried", "lessonComplete", "reviewClear")]
    + [f"companionReact.context.{c}" for c in ("vocab", "hanzi", "grammar")]
    + [f"companionReact.voice.{s}" for s in ("fox", "wolf", "snake", "cat", "dog", "tiger", "rabbit", "bird",
                                             "capybara", "panther", "sheep", "panda", "red-panda", "phoenix",
                                             "monkey", "koala", "elephant", "cow", "penguin", "owl")]
)

CALL = re.compile(r"""\bt\(\s*["']([A-Za-z0-9_.-]+)["']""")


def lookup(d, key):
    *parents, leaf = key.split(".")
    for part in parents:
        if not isinstance(d, dict) or part not in d:
            return None
        d = d[part]
    if not isinstance(d, dict):
        return None
    if leaf in d:
        return d[leaf]
    # i18next plural forms: key_one / key_few / key_many / key_other
    return d.get(f"{leaf}_other")


def main() -> int:
    data = {l: json.load(open(os.path.join(ROOT, "locales", f"{l}.json"), encoding="utf-8")) for l in LOCALES}
    used = set(DYNAMIC)
    for dirpath, _dirs, files in os.walk(ROOT):
        for name in files:
            if name.endswith((".js", ".jsx")):
                src = open(os.path.join(dirpath, name), encoding="utf-8").read()
                used.update(k for k in CALL.findall(src) if "." in k)
    missing = [(l, k) for k in sorted(used) for l in LOCALES if not isinstance(lookup(data[l], k), str)]
    for l, k in missing:
        print(f"MISSING [{l}] {k}")
    print(f"{len(used)} keys checked across {len(LOCALES)} locales: {len(missing)} missing")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
