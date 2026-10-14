# -*- coding: utf-8 -*-
"""Adds "stories.line" (the reader's line-by-line mode and saved sentences)
to all four locale files as new lines inside "stories", leaving every
existing line untouched. The strings themselves live in
add_library_i18n.py (S["line"]). Idempotent. Run from frontend/:
python scripts/add_line_i18n.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_library_i18n import S  # noqa: E402
from add_recall_i18n import LANGS, LOCALES, _object  # noqa: E402

if __name__ == "__main__":
    for lang in LANGS:
        path = os.path.join(LOCALES, f"{lang}.json")
        with open(path, encoding="utf-8", newline="") as f:
            lines = f.read().split("\r\n")
        if '    "line": {' not in lines[_object(lines, "stories")[0]:_object(lines, "stories")[1]]:
            _lo, hi = _object(lines, "stories")
            block = json.dumps({"line": {k: v[lang] for k, v in S["line"].items()}}, ensure_ascii=False,
                               indent=2).split("\n")[1:-1]
            block = ["  " + b for b in block]
            lines[hi - 1] = lines[hi - 1].rstrip(",") + ","
            lines[hi:hi] = block
        text = "\r\n".join(lines)
        json.loads(text)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print(f"updated {lang}.json")
