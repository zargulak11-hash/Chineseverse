"""Chinese Stories: graded reading from HSK 1 to HSK 9 (content: stories_content.py).

A story is read, heard and understood here; the learning itself goes
through the systems that already exist:

  reader      every sentence with curriculum pinyin, a translation in the
              learner's language and its words marked from the learner's
              own records: known, learning, due for review, or new. A word
              opens in the Word Helper (meaning, characters, "add to review").
  support     fades with the level: HSK 1-2 show pinyin and the translation
              inline; HSK 3-4 keep pinyin a toggle and translations a tap
              away; HSK 5-6 start without pinyin; HSK 7-9 read like real
              text, translation only on request. Audio slows down for
              beginners.
  round       POST /api/practice/sessions {"source": "story", "story": slug}:
              comprehension questions, one sentence picked by ear (then said
              aloud: the practice engine's speak step, a real voice attempt),
              and up to three of the story's words the learner hasn't
              mastered yet as real vocabulary cards (SRS, mistakes, Review).
              Completing the round is what "read" means -- grading, XP, DNA,
              quests and the companion reaction are the engine's own.
  locked      a story above the learner's HSK level (user_rank) is not
              served, by the reader or the round (403).
"""

from __future__ import annotations

import random
from datetime import datetime

from sqlalchemy.orm import Session

from app import models
from app.services import sentence as sent
from app.services import story_slots as ss
from app.services.stories_content import STORIES, STORY_BY_SLUG

LOCALES = ("en", "ru", "tg")


class StoryError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def gate(story: dict) -> int:
    """The HSK level that opens a story (7-9 is one band: all open at 7)."""
    return min(story["level"], 7)


def support(level: int) -> dict:
    if level <= 2:
        return {"pinyin": "on", "translation": "inline", "rate": 0.75}
    if level == 3:
        return {"pinyin": "on", "translation": "tap", "rate": 0.85}
    if level == 4:
        return {"pinyin": "off", "translation": "tap", "rate": 0.9}
    if level <= 6:
        return {"pinyin": "off", "translation": "tap", "rate": 0.95}
    return {"pinyin": "off", "translation": "hidden", "rate": 1.0}


def _text(d: dict, locale: str) -> str:
    return d.get(locale) or d.get("en") or ""


def _tr(d: dict, locale: str) -> str | None:
    """A sentence's translation; the Chinese UI reads the Chinese itself."""
    return None if locale == "zh" else _text(d, locale)


def _sessions(db: Session, user: models.User) -> list[models.PracticeSession]:
    return db.query(models.PracticeSession).filter_by(user_id=user.id, source="story").all()


def _slug(s: models.PracticeSession) -> str | None:
    return ((s.questions or [{}])[0].get("ctx") or {}).get("slug")


def records(db: Session, user: models.User) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for s in _sessions(db, user):
        slug = _slug(s)
        if not slug:
            continue
        r = out.setdefault(slug, {"rounds": 0, "best": 0.0, "started": True})
        if s.completed_at is not None:
            r["rounds"] += 1
            r["best"] = max(r["best"], s.score or 0.0)
    return out


def read_slugs(db: Session, user: models.User) -> set[str]:
    return {slug for slug, r in records(db, user).items() if r["rounds"]}


def _levels(db: Session) -> dict[int, int]:
    return {lvl.id: lvl.level for lvl in db.query(models.HSKLevel).all()}


def _statuses(db: Session, user: models.User, word_ids: set[int]) -> dict[int, tuple[str, bool]]:
    now = datetime.utcnow()
    rows = (db.query(models.UserVocabulary)
            .filter(models.UserVocabulary.user_id == user.id, models.UserVocabulary.word_id.in_(word_ids or [0])).all())
    return {r.word_id: (r.status or "new", bool(r.next_review_at and r.next_review_at <= now)) for r in rows}


def _word_state(st: tuple[str, bool] | None) -> str:
    if st is None or st[0] == "new":
        return "new"
    if st[1]:
        return "review"
    return "known" if st[0] in ("reviewing", "mastered") else "learning"


def _story_words(db: Session, story: dict) -> list[tuple[int, list[dict]]]:
    return [(i, sent.segment(db, s["zh"])) for i, s in enumerate(story["sentences"])]


def library(db: Session, user: models.User, locale: str) -> dict:
    from app.services.gamification import user_rank

    level, _ = user_rank(db, user)
    recs = records(db, user)
    out = []
    for st in STORIES:
        r = recs.get(st["slug"])
        locked = gate(st) > level
        status = "locked" if locked else "read" if r and r["rounds"] else "started" if r else "new"
        out.append({
            "slug": st["slug"], "level": st["level"], "gate": gate(st), "icon": st["icon"],
            "title": _text(st["title"], locale) if locale != "zh" else st["title"]["zh"], "title_zh": st["title"]["zh"],
            "summary": _text(st["summary"], locale) if locale != "zh" else st["summary"]["zh"],
            "sentences": len(st["sentences"]),
            "characters": sum(1 for s in st["sentences"] for ch in s["zh"] if "一" <= ch <= "鿿"),
            "status": status, "best": round(r["best"], 1) if r else 0.0, "rounds": r["rounds"] if r else 0,
        })
    # The one to read now: an unread story at the learner's own level,
    # else the easiest unread story they can open.
    open_unread = [s for s in out if s["status"] in ("new", "started")]
    at_level = [s for s in open_unread if s["gate"] == min(level, 7)]
    recommended = (at_level or open_unread or [{}])[0].get("slug")
    return {"level": level, "stories": out, "recommended": recommended}


def view(db: Session, user: models.User, slug: str, locale: str) -> dict:
    from app.services import internet
    from app.services.gamification import user_rank

    story = STORY_BY_SLUG.get(slug or "")
    if story is None:
        raise StoryError(404, "Story not found")
    level, _ = user_rank(db, user)
    if gate(story) > level:
        raise StoryError(403, f"This story opens at HSK {gate(story)}")
    lv = _levels(db)
    segmented = _story_words(db, story)
    ids = {t["word"].id for _, toks in segmented for t in toks if t["word"] is not None}
    states = _statuses(db, user, ids)
    meanings = ss.meanings(db, list(ids), locale)
    words: dict[int, dict] = {}
    sentences = []
    for i, toks in segmented:
        s = story["sentences"][i]
        out_toks = []
        for t in toks:
            w = t["word"]
            if w is None:
                out_toks.append({"text": t["text"]})
                continue
            state = _word_state(states.get(w.id))
            wl = lv.get(w.hsk_level_id, 9)
            out_toks.append({"text": t["text"], "word_id": w.id, "state": state, "level": wl,
                             "meaning": meanings.get(w.id, "")})
            words.setdefault(w.id, {"id": w.id, "text": w.simplified, "pinyin": w.pinyin, "level": wl,
                                    "meaning": meanings.get(w.id, ""), "state": state})
        sentences.append({"zh": s["zh"], "pinyin": internet._pinyin(db, s["zh"]), "tr": _tr(s, locale),
                          "tokens": out_toks})
    rec = records(db, user).get(slug)
    title = story["title"]["zh"] if locale == "zh" else _text(story["title"], locale)
    # The words worth stopping for: new and due ones first, then learning.
    order = {"new": 0, "review": 1, "learning": 2, "known": 3}
    glossary = sorted(words.values(), key=lambda w: (order[w["state"]], -w["level"]))
    return {
        "slug": slug, "level": story["level"], "icon": story["icon"], "title": title, "title_zh": story["title"]["zh"],
        "summary": story["summary"]["zh"] if locale == "zh" else _text(story["summary"], locale),
        "support": support(story["level"]), "sentences": sentences, "say": story["say"],
        "words": glossary, "questions": len(story["questions"]),
        "record": {"rounds": rec["rounds"], "best": round(rec["best"], 1)} if rec else None,
        "counts": {k: sum(1 for w in words.values() if w["state"] == k) for k in ("new", "review", "learning", "known")},
    }


def build_questions(db: Session, user: models.User, slug: str, level: int, rng: random.Random,
                    translated: dict | None) -> list[dict]:
    from app.services import internet, practice

    story = STORY_BY_SLUG.get(slug or "")
    if story is None:
        raise StoryError(404, "Story not found")
    if gate(story) > level:
        raise StoryError(403, f"This story opens at HSK {gate(story)}")
    show_py = story["level"] <= 3
    questions: list[dict] = []
    for cq in story["questions"]:
        order = list(range(len(cq["options"])))
        rng.shuffle(order)
        opts = [cq["options"][k] for k in order]
        questions.append({
            "type": "story_q", "item_type": "reading", "q": cq["q"],
            "q_py": internet._pinyin(db, cq["q"]) if show_py else None,
            "q_tr": {k: v for k, v in (cq.get("tr") or {}).items() if k in LOCALES and v},
            "options": [{"zh": o, "py": internet._pinyin(db, o) if show_py else ""} for o in opts],
            "item_id": order.index(cq["answer"]), "option_ids": list(range(len(opts))),
            "focus_id": internet._focus_of(db, cq["options"][cq["answer"]]), "show_py": show_py,
        })
    # Listening: the story's key sentence heard among two others -- and then
    # said aloud (the engine's speak step grades it against this sentence).
    lines = [s["zh"] for s in story["sentences"]]
    heard = lines[story["say"]]
    others = [x for x in lines if x != heard]
    rng.shuffle(others)
    opts = [heard] + others[:2]
    rng.shuffle(opts)
    questions.insert(1, {
        "type": "story_listen", "item_type": "reading", "speak": heard, "rate": support(story["level"])["rate"],
        "options": [{"zh": o, "py": ""} for o in opts], "item_id": opts.index(heard),
        "option_ids": list(range(len(opts))), "focus_id": internet._focus_of(db, heard), "show_py": False,
        "say": {"zh": heard},
    })
    # Up to three of the story's words the learner hasn't mastered yet, as
    # real vocabulary cards (the same items Review brings back).
    ids = [t["word"].id for _, toks in _story_words(db, story) for t in toks if t["word"] is not None]
    states = _statuses(db, user, set(ids))
    seen, rows = set(), []
    for wid in ids:
        if wid in seen:
            continue
        seen.add(wid)
        if _word_state(states.get(wid)) in ("new", "review", "learning"):
            r = db.get(models.VocabularyWord, wid)
            if r is not None and practice._usable("vocab", r) and len(r.simplified) >= 2:
                rows.append(r)
    for k, r in enumerate(rows[:3]):
        q = practice._question(db, "vocab", r, k, rng, translated)
        if q:
            questions.append(q)
    questions[0]["ctx"] = {"kind": "story", "slug": slug, "level": story["level"], "icon": story["icon"],
                           "title": story["title"]["zh"]}
    return questions
