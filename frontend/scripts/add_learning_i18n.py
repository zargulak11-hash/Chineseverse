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
}
KEYS = list(S)

if __name__ == "__main__":
    for lang in LANGS:
        path = os.path.join(LOCALES, f"{lang}.json")
        with open(path, encoding="utf-8", newline="") as f:
            raw = f.read()
        nl = "\r\n" if "\r\n" in raw else "\n"  # keep the file's own line endings
        lines = raw.split(nl)
        for dotted, value in S.items():
            put(lines, dotted, value[lang])
        text = nl.join(lines)
        json.loads(text)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print(f"updated {lang}.json")
