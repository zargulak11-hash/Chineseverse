"""Strings of the app shell (logo, layout). Idempotent; keeps 2-space indent
and CRLF. Run from frontend/: python scripts/add_shell_i18n.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LOCALES = os.path.join(HERE, "..", "src", "locales")


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


S = {
    "nav.toLanding": L("ChineseVerse — main page", "ChineseVerse — главная страница",
                       "ChineseVerse — саҳифаи асосӣ", "ChineseVerse——首页"),
}


def set_path(d, dotted, value):
    parts = dotted.split(".")
    for p in parts[:-1]:
        d = d.setdefault(p, {})
    d[parts[-1]] = value


if __name__ == "__main__":
    for loc in ("en", "ru", "tg", "zh"):
        path = os.path.join(LOCALES, f"{loc}.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for key, per in S.items():
            set_path(data, key, per[loc])
        with open(path, "w", encoding="utf-8", newline="\r\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"updated {loc}.json")
