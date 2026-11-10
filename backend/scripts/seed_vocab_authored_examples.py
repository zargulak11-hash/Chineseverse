# -*- coding: utf-8 -*-
"""Hand-written example sentences for vocabulary (app/seed_content/
vocab_examples/hsk*.json), checked before they reach the database.

The stories and case files gave 495 words a real example
(seed_vocab_story_examples.py) and are used up; the rest of HSK 1 needs
sentences written for them. Each entry is {"level", "word", "zh", "pinyin",
"en", "ru", "tg"} and is refused unless:

- the word is a curriculum word at that level with one row, still without
  an example, and appears in the sentence as a whole word (forward and
  backward longest-match splits agree);
- every curriculum word of the sentence is at the word's level or below;
- the pinyin, written by hand, is exactly the sentence's curriculum words
  read one after another: each word's own reading, or a character's from
  the Hanzi table (tones as the curriculum writes them; 一 and 不 in their
  dictionary tone). A wrong tone, a wrong reading of 还/得/长 or a missing
  syllable fails;
- one tone mark per syllable, ASCII punctuation, the apostrophe before a
  syllable that starts with a/o/e inside a word (bǎo'ān);
- the sentence is not used twice, and all translations are there.

English goes in example_translation; Russian and Tajik are content
translations marked "draft" -- written for the curriculum, awaiting a
native speaker's review (scripts/export_translation_review.py). Never
overwrites an example. Re-export the snapshot afterwards:
    python scripts/seed_vocab_authored_examples.py [--check]
    python scripts/export_curriculum_snapshot.py
"""
import glob
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402

SOURCE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "app", "seed_content", "vocab_examples")
CJK = re.compile(r"[㐀-鿿]")
SENTENCE = re.compile(r"^[㐀-鿿，、：；！？。]+[。！？]$")
TONED = set("āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ")
CYR = re.compile(r"[А-Яа-яЁёӢӣҚқҒғҲҳҶҷӮӯ]")
MAX_WORD = 8


def norm(p: str) -> str:
    """A reading compared as letters only: no spaces, apostrophes, case."""
    return unicodedata.normalize("NFC", re.sub(r"[\s'’·\-.,!?:;]", "", p or "").lower())


def entries() -> list[dict]:
    out = []
    for path in sorted(glob.glob(os.path.join(SOURCE_DIR, "*.json"))):
        with open(path, encoding="utf-8") as f:
            for e in json.load(f):
                out.append({**e, "_file": os.path.basename(path)})
    return out


class Checker:
    def __init__(self, db):
        self.level_of = {l.id: l.level for l in db.query(models.HSKLevel)}
        self.rows: dict[str, list] = {}
        for w in db.query(models.VocabularyWord):
            self.rows.setdefault(w.simplified, []).append(w)
        self.readings = {s: {norm(w.pinyin) for w in ws} for s, ws in self.rows.items()}
        self.lowest = {s: min(self.level_of[w.hsk_level_id] for w in ws) for s, ws in self.rows.items()}
        self.char_readings: dict[str, set] = {}
        for h in db.query(models.Hanzi):
            self.char_readings.setdefault(h.character, set()).update(
                norm(r) for r in re.split(r"[,，/;；]", h.pinyin or "") if r.strip())
        self.existing = {w.example for ws in self.rows.values() for w in ws if w.example}

    def split(self, text: str, backward: bool) -> list[tuple[int, str]]:
        lex, n, out = self.rows, len(text), []
        if not backward:
            i = 0
            while i < n:
                size = next((s for s in range(min(MAX_WORD, n - i), 1, -1) if text[i:i + s] in lex), 1)
                out.append((i, text[i:i + size]))
                i += size
            return out
        j = n
        while j > 0:
            size = next((s for s in range(min(MAX_WORD, j), 1, -1) if text[j - s:j] in lex), 1)
            out.append((j - size, text[j - size:j]))
            j -= size
        return out[::-1]

    def reads_as(self, tokens: list[str], pinyin: str) -> bool:
        """Can the pinyin be these tokens' readings one after another?"""
        target = norm(pinyin)
        options = []
        for t in tokens:
            opts = set(self.readings.get(t, set()))
            if len(t) == 1:
                opts |= self.char_readings.get(t, set())
            if not opts:
                return False
            options.append(opts)
        reach = {0}
        for opts in options:
            reach = {p + len(o) for p in reach for o in opts if target.startswith(o, p)}
            if not reach:
                return False
        return len(target) in reach

    def problems(self, e: dict, seen: set) -> list[str]:
        out = []
        word, zh, py, level = e.get("word"), e.get("zh", ""), e.get("pinyin", ""), e.get("level")
        rows = [w for w in self.rows.get(word, []) if self.level_of[w.hsk_level_id] == level]
        if len(rows) != 1:
            out.append(f"{word}: not exactly one HSK {level} row")
        elif rows[0].example and rows[0].example != zh:
            out.append(f"{word}: already has an example")
        if not SENTENCE.match(zh):
            out.append(f"{word}: not a plain sentence ending in 。！？")
        if zh in seen or (zh in self.existing and not (rows and rows[0].example == zh)):
            out.append(f"{word}: sentence used twice")
        seen.add(zh)
        fwd = self.split(zh, False)
        if (zh.find(word) < 0 or not any(p == word for _, p in fwd)
                or not set(x for x in fwd if x[1] == word) & set(self.split(zh, True))):
            out.append(f"{word}: not a whole word of {zh}")
        tokens = [p for _, p in fwd if CJK.search(p)]
        too_hard = [t for t in tokens if t in self.lowest and self.lowest[t] > level]
        unknown = [t for t in tokens if t not in self.lowest and t not in self.char_readings]
        if too_hard or unknown:
            out.append(f"{word}: above HSK {level} or unknown: {too_hard + unknown}")
        if not self.reads_as(tokens, py):
            out.append(f"{word}: pinyin '{py}' is not the curriculum reading of {tokens}")
        # (Each syllable's tone is checked by reads_as: the pinyin must be the
        # curriculum's own readings, which carry one mark per syllable.)
        if re.search(r"[，。！？：；、]", py) or "  " in py or py != py.strip():
            out.append(f"{word}: pinyin punctuation")
        for t, w in ((t, self.rows.get(t)) for t in tokens):
            # A word stored as "bǎo ān" is written bǎo'ān.
            for row in w or []:
                parts = row.pinyin.split()
                for k in range(1, len(parts)):
                    if unicodedata.normalize("NFD", parts[k])[0].lower() in "aoe" and parts[k - 1] + parts[k] in py:
                        out.append(f"{word}: apostrophe missing in {parts[k - 1]}'{parts[k]}")
        for loc in ("en", "ru", "tg"):
            if not (e.get(loc) or "").strip():
                out.append(f"{word}: no {loc}")
        if e.get("ru") and not CYR.search(e["ru"]) or e.get("tg") and not CYR.search(e["tg"]):
            out.append(f"{word}: ru/tg not in Cyrillic")
        if any(CJK.search(e.get(loc) or "") for loc in ("en", "ru", "tg")):
            out.append(f"{word}: Chinese left inside a translation")
        if CYR.search(e.get("en") or ""):
            out.append(f"{word}: Cyrillic in the English")
        return out


def main(check_only: bool) -> int:
    db = SessionLocal()
    checker, seen, bad, added = Checker(db), set(), [], 0
    for e in entries():
        problems = checker.problems(e, seen)
        if problems:
            bad.extend(f"{e['_file']}: {p}" for p in problems)
            continue
        row = next(w for w in checker.rows[e["word"]] if checker.level_of[w.hsk_level_id] == e["level"])
        if check_only or row.example:
            continue
        row.example, row.example_pinyin, row.example_translation = e["zh"], e["pinyin"], e["en"]
        for loc in ("ru", "tg"):
            db.add(models.ContentTranslation(content_type="vocab_word", content_key=str(row.id),
                                             field="example_translation", locale=loc, text=e[loc], source="draft"))
        added += 1
    for b in bad:
        print("REFUSED", b)
    if check_only or bad:
        db.rollback()
    else:
        db.commit()
    print(f"{len(entries())} entries, {len(bad)} problems, {added} examples added")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(check_only="--check" in sys.argv))
