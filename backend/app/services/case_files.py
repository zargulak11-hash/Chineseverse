"""Detective Mode case files: hand-written mysteries on disk, one JSON file each.

app/seed_content/cases/hsk<N>/<slug>.json -- like the story books
(services/books.py), adding a case is adding a file: no code change, no
migration. Every file is loaded and validated at startup, so a broken case
never reaches a learner. The generated cases (services/detective.py) are
built per learner from curriculum words; a case file is a fixed story with
real suspects, evidence and a timeline, written for its level.

A case (Chinese first; en/ru/tg are support translations):

    {
      "slug": "the-missing-cake", "level": 1, "order": 1, "icon": "🎂",
      "title":   ["蛋糕去哪儿了？", "Where did the cake go?", "…", "…"],
      "summary": ["…", "…", "…", "…"],
      "names": {"小明": "Xiǎomíng"},                 # every suspect's name, with pinyin
      "brief": [["…", "…", "…", "…"], …],             # what happened
      "suspects": [
        {"name": "小明", "role": ["弟弟", "little brother", "…", "…"],
         "statement": ["我在看电视。", "I was watching TV.", "…", "…"]}, …
      ],
      "evidence": [["…", "…", "…", "…"], …],          # what the detective finds
      "timeline": [{"time": "15:00", "event": ["…", "…", "…", "…"]}, …],
      "questions": [{"q": "…？", "options": ["…"], "answer": 0, "tr": ["…", "…", "…"]}, …],
      "ask": ["谁吃了蛋糕？", "Who ate the cake?", "…", "…"],   # the deduction
      "culprit": 1,                                   # index into suspects
      "verdict": [["…", "…", "…", "…"], …]             # why: the explanation
    }

The questions are clue comprehension, graded by the practice engine like a
story's (type story_q); the deduction is the last question of the round.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache

from app.services.books import CJK_RE, LANGS, SLUG_RE, BookError, _question, _sentence, _texts

CASES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seed_content", "cases")
TIME_RE = re.compile(r"^([01]?\d|2[0-3]):[0-5]\d$")


class CaseFileError(BookError):
    pass


def _lines(value, where: str, minimum: int = 1) -> list[dict]:
    if not isinstance(value, list) or len(value) < minimum:
        raise CaseFileError(f"{where}: at least {minimum} sentence(s)")
    return [_sentence(s, f"{where} {i + 1}") for i, s in enumerate(value)]


def parse(raw: dict, where: str = "case") -> dict:
    """A validated, normalised case file (raises CaseFileError naming the problem)."""
    if not isinstance(raw, dict):
        raise CaseFileError(f"{where}: a case is an object")
    slug = raw.get("slug")
    if not isinstance(slug, str) or not SLUG_RE.match(slug) or len(slug) > 40:
        raise CaseFileError(f"{where}: bad slug {slug!r}")
    where = f"{where} ({slug})"
    level = raw.get("level")
    if not isinstance(level, int) or not 1 <= level <= 9:
        raise CaseFileError(f"{where}: level must be 1-9")
    names = raw.get("names") or {}
    if not isinstance(names, dict) or not all(
            isinstance(k, str) and CJK_RE.search(k) and isinstance(v, str) and v.strip() for k, v in names.items()):
        raise CaseFileError(f"{where}: 'names' maps each Chinese name to its pinyin")
    suspects = raw.get("suspects")
    if not isinstance(suspects, list) or not 2 <= len(suspects) <= 5:
        raise CaseFileError(f"{where}: 2-5 suspects")
    out_s = []
    for i, s in enumerate(suspects):
        sw = f"{where} suspect {i + 1}"
        if not isinstance(s, dict) or s.get("name") not in names:
            raise CaseFileError(f"{sw}: 'name' must be one of the case's names (for its pinyin)")
        out_s.append({"name": s["name"], "pinyin": names[s["name"]],
                      "role": _sentence(s.get("role"), f"{sw} role"),
                      "statement": _sentence(s.get("statement"), f"{sw} statement")})
    if len({s["name"] for s in out_s}) != len(out_s):
        raise CaseFileError(f"{where}: two suspects share a name")
    culprit = raw.get("culprit")
    if not isinstance(culprit, int) or not 0 <= culprit < len(out_s):
        raise CaseFileError(f"{where}: 'culprit' must index a suspect")
    timeline = raw.get("timeline")
    if not isinstance(timeline, list) or len(timeline) < 2:
        raise CaseFileError(f"{where}: a timeline of at least two moments")
    out_t = []
    for i, t in enumerate(timeline):
        tw = f"{where} timeline {i + 1}"
        if not isinstance(t, dict) or not isinstance(t.get("time"), str) or not TIME_RE.match(t["time"]):
            raise CaseFileError(f"{tw}: 'time' is HH:MM")
        out_t.append({"time": t["time"], "event": _sentence(t.get("event"), f"{tw} event")})
    minutes = [int(h) * 60 + int(m) for h, m in (t["time"].split(":") for t in out_t)]
    if minutes != sorted(minutes):
        raise CaseFileError(f"{where}: the timeline must be in time order")
    questions = raw.get("questions")
    if not isinstance(questions, list) or len(questions) < 2:
        raise CaseFileError(f"{where}: at least two clue questions")
    brief = _lines(raw.get("brief"), f"{where} brief")
    evidence = _lines(raw.get("evidence"), f"{where} evidence", 2)
    verdict = _lines(raw.get("verdict"), f"{where} verdict")
    sentences = brief + [s["statement"] for s in out_s] + evidence + [t["event"] for t in out_t] + verdict
    return {
        "slug": slug, "level": level, "order": int(raw.get("order") or 99),
        "icon": str(raw.get("icon") or "🕵️")[:8],
        "names": {k: v.strip() for k, v in names.items()},
        "title": _texts(raw.get("title"), f"{where} title"),
        "summary": _texts(raw.get("summary"), f"{where} summary"),
        "brief": brief, "suspects": out_s, "evidence": evidence, "timeline": out_t,
        "questions": [_question(q, f"{where} q{i + 1}") for i, q in enumerate(questions)],
        "ask": _sentence(raw.get("ask"), f"{where} ask"),
        "culprit": culprit, "verdict": verdict,
        "characters": sum(len(CJK_RE.findall(s["zh"])) for s in sentences),
        "sentences": sentences,
    }


def load_dir(path: str = CASES_DIR) -> list[dict]:
    cases: list[dict] = []
    seen: set[str] = set()
    if not os.path.isdir(path):
        return cases
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
                    raise CaseFileError(f"{rel}: invalid JSON ({exc})") from exc
            case = parse(raw, rel)
            if name[:-5] != case["slug"]:
                raise CaseFileError(f"{rel}: file name must be <slug>.json")
            if os.path.basename(root) != f"hsk{case['level']}":
                raise CaseFileError(f"{rel}: a level {case['level']} case belongs in hsk{case['level']}/")
            if case["slug"] in seen:
                raise CaseFileError(f"{rel}: duplicate slug {case['slug']}")
            seen.add(case["slug"])
            cases.append(case)
    cases.sort(key=lambda c: (c["level"], c["order"], c["slug"]))
    return cases


@lru_cache(maxsize=1)
def _all() -> tuple[list[dict], dict[str, dict]]:
    cases = load_dir()
    return cases, {c["slug"]: c for c in cases}


def all_cases() -> list[dict]:
    return _all()[0]


def get(slug: str) -> dict | None:
    return _all()[1].get(slug or "")


def as_book(case: dict) -> dict:
    """The case seen as a one-chapter book, so the stories segmenter gives
    it curriculum pinyin and a vocabulary check (names kept whole)."""
    return {"slug": f"case:{case['slug']}", "level": case["level"], "names": case["names"],
            "chapters": [{"sentences": case["sentences"] + [{"zh": q["q"]} for q in case["questions"]]}],
            "characters": case["characters"], "sentence_count": len(case["sentences"])}


def vocabulary_report(db, case: dict) -> dict:
    """The curriculum check of a case: like a book's, with the cap of a
    three-chapter book of its level (a case reads like a short story)."""
    from app.services import sentence as sent
    from app.services import stories

    book = as_book(case)
    prof = stories.profile(db, book)
    loose = {t for ch in prof["chapters"] for row in ch for t, _wid, kind in row if kind == "char"}
    unknown = sorted(loose - set(sent.hanzi_rows(db, loose)))
    cap = None if case["level"] >= 7 else (5 if case["level"] <= 4 else 10)
    suspicious = sorted({s for x in book["chapters"][0]["sentences"] for s in stories.ambiguous(db, book, x["zh"])})
    return {"above": prof["above"], "cap": cap, "unknown_chars": unknown, "suspicious": suspicious,
            "ok": (len(unknown) <= 5 if case["level"] >= 7 else not unknown)
            and (cap is None or len(prof["above"]) <= cap)}
