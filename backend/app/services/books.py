"""The Chinese Stories library: books on disk, one JSON file per book.

app/seed_content/books/hsk<N>/<slug>.json -- adding a book is adding a
file (no code change, no migration); the app loads and validates every
file at startup and refuses to start on a malformed one, so a broken book
never reaches a learner. scripts/check_books.py validates the same way and
also checks each book's vocabulary against the curriculum.

A book (sentences are written in Chinese first; en/ru/tg are the support
translations, shown only when the learner asks for help):

    {
      "slug": "my-day", "level": 1, "order": 3, "topic": "daily", "icon": "☀️",
      "title":   ["我的一天", "My day", "Мой день", "Рӯзи ман"],
      "summary": ["…", "…", "…", "…"],
      "names": {"王小雨": "Wáng Xiǎoyǔ"},          # optional: people and places with their pinyin
      "chapters": [
        {
          "title": ["早上", "Morning", "Утро", "Субҳ"],
          "text": [                                  # paragraphs
            [["我七点起床。", "I get up at seven.", "Я встаю в семь.", "Ман соати ҳафт бедор мешавам."], …],
            …
          ],
          "say": 2,                                   # optional: sentence (flat index) to say aloud
          "questions": [                              # optional: comprehension, in Chinese
            {"q": "他几点起床？", "options": ["六点", "七点", "八点"], "answer": 1,
             "tr": ["What time does he get up?", "Во сколько он встаёт?", "Ӯ соати чанд бедор мешавад?"]}
          ]
        }
      ]
    }

`names` are read as names, not vocabulary: they never count as words above
the level and the reader shows the book's pinyin for them.

`level` is the HSK level the book is written for (7, 8, 9 are steps inside
the shared advanced band and all open at 7 -- see stories.gate). `order`
is the suggested reading order inside a level.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache

BOOKS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seed_content", "books")
LANGS = ("zh", "en", "ru", "tg")
TOPICS = ("daily", "family", "friends", "school", "food", "shopping", "travel", "city", "work", "culture",
          "nature", "history", "relationships", "adventure", "mystery", "humor", "society", "science")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CJK_RE = re.compile(r"[㐀-鿿]")


class BookError(ValueError):
    pass


def _texts(value, where: str, langs=LANGS) -> dict:
    if not isinstance(value, list) or len(value) != len(langs) or not all(isinstance(v, str) and v.strip() for v in value):
        raise BookError(f"{where}: expected {len(langs)} non-empty strings ({'/'.join(langs)})")
    return dict(zip(langs, (v.strip() for v in value)))


def _sentence(value, where: str) -> dict:
    s = _texts(value, where)
    if not CJK_RE.search(s["zh"]):
        raise BookError(f"{where}: the first text must be Chinese")
    return s


def _question(value, n_where: str) -> dict:
    if not isinstance(value, dict):
        raise BookError(f"{n_where}: a question is an object")
    q, options, answer = value.get("q"), value.get("options"), value.get("answer")
    if not isinstance(q, str) or not CJK_RE.search(q):
        raise BookError(f"{n_where}: 'q' must be a Chinese question")
    if not isinstance(options, list) or not 2 <= len(options) <= 4 or not all(isinstance(o, str) and o for o in options):
        raise BookError(f"{n_where}: 2-4 Chinese options")
    if len(set(options)) != len(options):
        raise BookError(f"{n_where}: options must differ")
    if not isinstance(answer, int) or not 0 <= answer < len(options):
        raise BookError(f"{n_where}: 'answer' must index an option")
    tr = value.get("tr")
    return {"q": q, "options": options, "answer": answer,
            "tr": _texts(tr, f"{n_where}.tr", LANGS[1:]) if tr is not None else None}


def parse(raw: dict, where: str = "book") -> dict:
    """A validated, normalised book (raises BookError with the place of the problem)."""
    if not isinstance(raw, dict):
        raise BookError(f"{where}: a book is an object")
    slug = raw.get("slug")
    if not isinstance(slug, str) or not SLUG_RE.match(slug) or len(slug) > 40:
        raise BookError(f"{where}: bad slug {slug!r}")
    where = f"{where} ({slug})"
    level = raw.get("level")
    if not isinstance(level, int) or not 1 <= level <= 9:
        raise BookError(f"{where}: level must be 1-9")
    topic = raw.get("topic")
    if topic not in TOPICS:
        raise BookError(f"{where}: topic must be one of {', '.join(TOPICS)}")
    chapters = raw.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        raise BookError(f"{where}: at least one chapter")
    out_ch = []
    for ci, ch in enumerate(chapters):
        cw = f"{where} chapter {ci + 1}"
        paras = ch.get("text") if isinstance(ch, dict) else None
        if not isinstance(paras, list) or not paras or not all(isinstance(p, list) and p for p in paras):
            raise BookError(f"{cw}: 'text' is a list of non-empty paragraphs")
        paragraphs = [[_sentence(s, f"{cw} p{pi + 1}s{si + 1}") for si, s in enumerate(p)] for pi, p in enumerate(paras)]
        flat = [s for p in paragraphs for s in p]
        seen_zh: set[str] = set()
        for s in flat:
            # A repeated sentence is almost always a copy-paste or export
            # slip (one once duplicated a whole paragraph), not writing.
            if s["zh"] in seen_zh:
                raise BookError(f"{cw}: the sentence {s['zh']!r} appears twice")
            seen_zh.add(s["zh"])
        say = ch.get("say")
        if say is not None and (not isinstance(say, int) or not 0 <= say < len(flat)):
            raise BookError(f"{cw}: 'say' must index a sentence of the chapter")
        out_ch.append({
            "title": _texts(ch.get("title"), f"{cw} title"),
            "paragraphs": paragraphs,
            "sentences": flat,
            "say": say,
            "questions": [_question(q, f"{cw} q{qi + 1}") for qi, q in enumerate(ch.get("questions") or [])],
        })
    names = raw.get("names") or {}
    if not isinstance(names, dict) or not all(
            isinstance(k, str) and CJK_RE.search(k) and isinstance(v, str) and v.strip() for k, v in names.items()):
        raise BookError(f"{where}: 'names' maps each Chinese name to its pinyin")
    chars = sum(len(CJK_RE.findall(s["zh"])) for c in out_ch for s in c["sentences"])
    return {
        "slug": slug, "level": level, "order": int(raw.get("order") or 99), "topic": topic,
        "icon": str(raw.get("icon") or "📖")[:8],
        "names": {k: v.strip() for k, v in names.items()},
        "title": _texts(raw.get("title"), f"{where} title"),
        "summary": _texts(raw.get("summary"), f"{where} summary"),
        "chapters": out_ch,
        "characters": chars,
        "sentence_count": sum(len(c["sentences"]) for c in out_ch),
    }


def load_dir(path: str = BOOKS_DIR) -> list[dict]:
    books: list[dict] = []
    seen: set[str] = set()
    for root, _dirs, files in os.walk(path):
        for name in sorted(files):
            if not name.endswith(".json"):
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, path)
            with open(full, encoding="utf-8") as f:
                try:
                    raw = json.load(f)
                except json.JSONDecodeError as exc:
                    raise BookError(f"{rel}: invalid JSON ({exc})") from exc
            book = parse(raw, rel)
            if name[:-5] != book["slug"]:
                raise BookError(f"{rel}: file name must be <slug>.json")
            if os.path.basename(root) != f"hsk{book['level']}":
                raise BookError(f"{rel}: a level {book['level']} book belongs in hsk{book['level']}/")
            if book["slug"] in seen:
                raise BookError(f"{rel}: duplicate slug {book['slug']}")
            seen.add(book["slug"])
            books.append(book)
    books.sort(key=lambda b: (b["level"], b["order"], b["slug"]))
    return books


@lru_cache(maxsize=1)
def _library() -> tuple[list[dict], dict[str, dict]]:
    books = load_dir()
    return books, {b["slug"]: b for b in books}


def all_books() -> list[dict]:
    return _library()[0]


def get(slug: str) -> dict | None:
    return _library()[1].get(slug or "")


def dump(book_raw: dict) -> str:
    """A book file in the house layout: one sentence per line, so a diff
    shows exactly which sentence changed."""
    def line(v):
        return json.dumps(v, ensure_ascii=False)

    out = ["{"]
    head = [(k, book_raw[k]) for k in ("slug", "level", "order", "topic", "icon", "title", "summary", "names")
            if k in book_raw]
    for k, v in head:
        out.append(f'  "{k}": {line(v)},')
    out.append('  "chapters": [')
    for ci, ch in enumerate(book_raw["chapters"]):
        out.append("    {")
        out.append(f'      "title": {line(ch["title"])},')
        out.append('      "text": [')
        for pi, p in enumerate(ch["text"]):
            out.append("        [")
            for si, s in enumerate(p):
                out.append(f"          {line(s)}{',' if si < len(p) - 1 else ''}")
            out.append(f"        ]{',' if pi < len(ch['text']) - 1 else ''}")
        tail = []
        if ch.get("say") is not None:
            tail.append(f'      "say": {ch["say"]}')
        if ch.get("questions"):
            qs = ",\n".join(f"        {line(q)}" for q in ch["questions"])
            tail.append(f'      "questions": [\n{qs}\n      ]')
        out.append("      ]" + ("," if tail else ""))
        out.append(",\n".join(tail)) if tail else None
        out.append(f"    }}{',' if ci < len(book_raw['chapters']) - 1 else ''}")
    out.append("  ]")
    out.append("}")
    return "\n".join(x for x in out if x is not None) + "\n"
