"""Chinese Stories: a graded reading library from HSK 1 to HSK 9.

Books live in content files (services/books.py); this module is what a
learner does with them, all from their own records:

  library     every book with its real shape -- chapters, an honest reading
              time, how many of its words are new to THIS learner, a
              difficulty measured against the curriculum -- and the
              learner's state (new / in progress / completed / locked),
              the book to start with and the one to continue.
  reader      a chapter in Chinese: every sentence with curriculum pinyin
              (shown or hidden by level) and its words marked from the
              learner's records (new, learning, due, known). Translations
              are never laid over the text; help comes when the learner
              asks for it.
  help        a tapped word opens the curriculum's own entry (Word Helper,
              "add to review"); a selected sentence or passage is explained
              -- pinyin and word-by-word from the curriculum, the book's own
              translation when the selection is whole sentences, grammar
              the app recognises, and, only when asked, an AI explanation
              that is cached for everyone and falls back to the curriculum
              data when no AI answers.
  progress    StoryProgress: the bookmark (chapter + sentence), finished
              chapters, real counters (sentences explained, listening, words
              looked up). Created by the first reading action -- opening the
              library or a book writes nothing.
  round       POST /api/practice/sessions {"source": "story", "story": slug,
              "chapter": n}: the chapter's comprehension questions, one of
              its sentences picked by ear (then said aloud) and up to three
              of its words as real vocabulary cards. Grading, XP, Learning
              Compass, quests and the companion are the practice engine's.
              Finishing a round also finishes that chapter.
  locked      a book above the learner's HSK level (user_rank) is listed with
              the level that opens it, and refused by every endpoint (403).
"""

from __future__ import annotations

import hashlib
import math
import random
import time
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.services import books as lib
from app.services import sentence as sent
from app.services import story_slots as ss

LOCALES = ("en", "ru", "tg")
# Reading speed (Chinese characters per minute) a learner at each level can
# honestly be expected to manage on graded text, plus a minute per chapter
# for stopping on words. Shown as "≈ N min", never measured.
CHARS_PER_MIN = {1: 25, 2: 35, 3: 50, 4: 65, 5: 80, 6: 95, 7: 110, 8: 120, 9: 130}
# Typical sentence length (characters) at each level: the yardstick for
# a book's difficulty inside its level.
SENTENCE_NORM = {1: 9, 2: 12, 3: 16, 4: 20, 5: 25, 6: 29, 7: 33, 8: 37, 9: 41}
AI_PER_HOUR = 40  # uncached AI explanations one learner may ask for per hour
MAX_SELECTION = 200


class StoryError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def gate(book: dict) -> int:
    """The HSK level that opens a book (7-9 is one band: all open at 7)."""
    return min(book["level"], 7)


def support(level: int) -> dict:
    """Reading support by the book's level: pinyin starts on for beginners
    (a toggle at every level), audio slows down for them."""
    if level <= 2:
        return {"pinyin": "on", "rate": 0.75}
    if level == 3:
        return {"pinyin": "on", "rate": 0.85}
    if level == 4:
        return {"pinyin": "off", "rate": 0.9}
    if level <= 6:
        return {"pinyin": "off", "rate": 0.95}
    return {"pinyin": "off", "rate": 1.0}


def _text(d: dict, locale: str) -> str:
    return d.get("zh") if locale == "zh" else (d.get(locale) or d.get("en") or "")


# --------------------------------------------------------------------------- the curriculum view of a book
def segment(db: Session, book: dict, text: str) -> list[dict]:
    """sentence.segment, with the book's names (people, places) kept whole
    as "name" tokens carrying the book's pinyin -- a name is not
    vocabulary."""
    names = book.get("names") or {}
    if not names:
        return sent.segment(db, text)
    out: list[dict] = []
    i, start = 0, 0
    ordered = sorted(names, key=len, reverse=True)
    while i < len(text):
        hit = next((n for n in ordered if text.startswith(n, i)), None)
        if hit:
            if start < i:
                out.extend(sent.segment(db, text[start:i]))
            out.append({"text": hit, "kind": "name", "word": None, "pinyin": names[hit]})
            i += len(hit)
            start = i
        else:
            i += 1
    if start < len(text):
        out.extend(sent.segment(db, text[start:]))
    return out


def pinyin_of(db: Session, book: dict, text: str, toks: list[dict] | None = None) -> str:
    """Pinyin from the curriculum (words, then single characters) and the
    book's names -- never typed by hand, never guessed."""
    toks = toks if toks is not None else segment(db, book, text)
    chars = {t["text"] for t in toks if t["kind"] == "char"}
    hz = sent.hanzi_rows(db, chars)
    parts: list[str] = []
    for t in toks:
        if t["kind"] == "name":
            parts.append(t["pinyin"])
        elif t["word"] is not None:
            parts.append(t["word"].pinyin)
        elif t["kind"] == "char" and t["text"] in hz:
            parts.append(hz[t["text"]].pinyin or "")
        elif t["kind"] == "other" and parts:
            parts[-1] += t["text"]
    return " ".join(p for p in parts if p)


# Content is static for the life of the process and word ids are this
# database's, so each book is segmented once.
_PROFILE: dict[str, dict] = {}


def profile(db: Session, book: dict) -> dict:
    """The book measured against the curriculum: its word ids (per sentence
    and overall), words above its level, and from that its difficulty and
    reading time."""
    cached = _PROFILE.get(book["slug"])
    if cached is not None:
        return cached
    levels = sent._level_map(db)
    chapters, all_ids, above, own, total = [], set(), set(), 0, 0
    for ch in book["chapters"]:
        rows = []
        for s in ch["sentences"]:
            toks = segment(db, book, s["zh"])
            rows.append([(t["text"], t["word"].id if t["word"] is not None else None, t["kind"]) for t in toks])
            for t in toks:
                w = t["word"]
                if w is None:
                    continue
                lvl = levels.get(w.hsk_level_id, 9)
                all_ids.add(w.id)
                total += 1
                own += lvl >= min(book["level"], 7)
                if lvl > book["level"] and book["level"] < 7:
                    above.add(t["text"])
        chapters.append(rows)
    n_sent = max(1, book["sentence_count"])
    avg_len = book["characters"] / n_sent
    minutes = max(1, math.ceil(book["characters"] / CHARS_PER_MIN[book["level"]] + 0.5 * len(book["chapters"])))
    # How hard the book is for its level: sentences longer than the level's
    # norm, and (above HSK 1, where every word is at the level) more words
    # AT the level rather than below it. Ranked against the level's other
    # books in difficulty().
    at_share = (own / total if total else 0.0) if book["level"] > 1 else 0.0
    out = {"chapters": chapters, "word_ids": all_ids, "above": sorted(above), "avg_len": round(avg_len, 1),
           "score": avg_len / SENTENCE_NORM[book["level"]] + at_share, "minutes": minutes}
    _PROFILE[book["slug"]] = out
    return out


def difficulty(db: Session, book: dict) -> str:
    """easy / medium / challenging among the books of the same level (by
    thirds once a level has three books; by sentence length against the
    level's norm before that)."""
    same = [b for b in lib.all_books() if b["level"] == book["level"]]
    mine = profile(db, book)
    if len(same) < 3:
        ratio = mine["avg_len"] / SENTENCE_NORM[book["level"]]
        return "easy" if ratio < 0.85 else "challenging" if ratio > 1.15 else "medium"
    ranked = sorted(same, key=lambda b: (profile(db, b)["score"], b["slug"]))
    k = ranked.index(book)
    third = len(ranked) / 3
    return "easy" if k < third else "challenging" if k >= 2 * third else "medium"


def above_level_cap(book: dict) -> int | None:
    """How many distinct words above its level a book may use (they are
    marked "new" in the reader). HSK 7-9 is one band: no cap."""
    n = len(book["chapters"])
    if book["level"] <= 4:
        return 2 + n
    if book["level"] <= 6:
        return 4 + 2 * n
    return None


def vocabulary_report(db: Session, book: dict) -> dict:
    """The curriculum check of one book (scripts/check_books.py and the tests)."""
    prof = profile(db, book)
    loose = {t for ch in prof["chapters"] for row in ch for t, wid, kind in row if kind == "char"}
    unknown = sorted(loose - set(sent.hanzi_rows(db, loose)))
    cap = above_level_cap(book)
    return {"above": prof["above"], "cap": cap, "unknown_chars": unknown, "avg_len": prof["avg_len"],
            "difficulty": difficulty(db, book), "minutes": prof["minutes"],
            # Advanced (7-9) literature may use a few characters beyond the
            # 3,000 of the curriculum; they are read without curriculum pinyin.
            "ok": (len(unknown) <= 3 + 2 * len(book["chapters"]) if book["level"] >= 7 else not unknown)
            and (cap is None or len(prof["above"]) <= cap)}


def _word_states(db: Session, user: models.User, ids: set[int]) -> dict[int, str]:
    now = datetime.utcnow()
    rows = (db.query(models.UserVocabulary)
            .filter(models.UserVocabulary.user_id == user.id, models.UserVocabulary.word_id.in_(ids or [0])).all())
    out = {}
    for r in rows:
        status = r.status or "new"
        if status == "new":
            continue
        if r.next_review_at and r.next_review_at <= now:
            out[r.word_id] = "review"
        else:
            out[r.word_id] = "known" if status in ("reviewing", "mastered") else "learning"
    return out


# --------------------------------------------------------------------------- the learner's records
def _rounds(db: Session, user: models.User) -> dict[str, dict]:
    """Completed story rounds by book: count, best score, chapters covered."""
    out: dict[str, dict] = {}
    for s in db.query(models.PracticeSession).filter_by(user_id=user.id, source="story"):
        ctx = (s.questions or [{}])[0].get("ctx") or {}
        slug = ctx.get("slug")
        if not slug:
            continue
        r = out.setdefault(slug, {"rounds": 0, "best": 0.0, "chapters": set(), "started": True, "last": None})
        if s.completed_at is not None:
            r["last"] = max(r["last"] or s.completed_at, s.completed_at)
            r["rounds"] += 1
            r["best"] = max(r["best"], s.score or 0.0)
            r["chapters"].add(int(ctx.get("chapter") or 0))
    return out


def records(db: Session, user: models.User) -> dict[str, dict]:
    return _rounds(db, user)


def _progress_rows(db: Session, user: models.User) -> dict[str, models.StoryProgress]:
    return {p.slug: p for p in db.query(models.StoryProgress).filter_by(user_id=user.id)}


def _done_chapters(book: dict, p: models.StoryProgress | None, r: dict | None) -> set[int]:
    done = set(p.chapters_done or []) if p else set()
    if r:
        done |= r["chapters"]  # a finished round finished its chapter (incl. rounds from before books)
    return {c for c in done if 0 <= c < len(book["chapters"])}


def _completed(book: dict, p: models.StoryProgress | None, r: dict | None) -> bool:
    return (p is not None and p.completed_at is not None) or len(_done_chapters(book, p, r)) == len(book["chapters"])


def read_slugs(db: Session, user: models.User) -> set[str]:
    """Books the learner has finished: every chapter read (by reading it to
    the end or by its round)."""
    rounds, prog = _rounds(db, user), _progress_rows(db, user)
    return {b["slug"] for b in lib.all_books() if _completed(b, prog.get(b["slug"]), rounds.get(b["slug"]))}


def completed_books(db: Session, user: models.User) -> list[tuple[dict, datetime]]:
    """Finished books with when they were finished, oldest first (Passport,
    Companion, achievements)."""
    rounds, prog = _rounds(db, user), _progress_rows(db, user)
    out = []
    for b in lib.all_books():
        p, r = prog.get(b["slug"]), rounds.get(b["slug"])
        if not _completed(b, p, r):
            continue
        when = p.completed_at if p and p.completed_at else None
        if when is None:  # finished by rounds alone (e.g. before books had chapters)
            when = (r["last"] if r else None) or (p.updated_at if p else None)
        if when is not None:
            out.append((b, when))
    out.sort(key=lambda x: x[1])
    return out


def _percent(book: dict, p: models.StoryProgress | None, done: set[int]) -> int:
    n = len(book["chapters"])
    if len(done) == n:
        return 100
    partial = 0.0
    if p is not None and p.chapter not in done and 0 <= p.chapter < n:
        size = len(book["chapters"][p.chapter]["sentences"])
        partial = min(1.0, p.position / size) if size else 0.0
    return min(99, round(100 * (len(done) + partial) / n))


# --------------------------------------------------------------------------- library
def _card(db: Session, book: dict, level: int, known: dict[int, str], p, r, locale: str) -> dict:
    prof = profile(db, book)
    done = _done_chapters(book, p, r)
    locked = gate(book) > level
    completed = _completed(book, p, r)
    status = ("locked" if locked else "completed" if completed
              else "in_progress" if (p is not None or done or (r and r["started"])) else "new")
    return {
        "slug": book["slug"], "level": book["level"], "gate": gate(book), "order": book["order"],
        "topic": book["topic"], "icon": book["icon"],
        "title": _text(book["title"], locale), "title_zh": book["title"]["zh"],
        "summary": _text(book["summary"], locale),
        "chapters": len(book["chapters"]), "minutes": prof["minutes"], "difficulty": difficulty(db, book),
        "characters": book["characters"],
        "new_words": sum(1 for i in prof["word_ids"] if i not in known),
        "status": status, "percent": _percent(book, p, done) if not locked else 0,
        "chapter": (p.chapter + 1) if p is not None and not completed else None,
        "best": round(r["best"], 1) if r else 0.0,
    }


def library(db: Session, user: models.User, locale: str) -> dict:
    from app.services.gamification import user_rank

    level, _ = user_rank(db, user)
    all_books = lib.all_books()
    ids = set().union(*(profile(db, b)["word_ids"] for b in all_books)) if all_books else set()
    known = _word_states(db, user, ids)
    rounds, prog = _rounds(db, user), _progress_rows(db, user)
    cards = [_card(db, b, level, known, prog.get(b["slug"]), rounds.get(b["slug"]), locale) for b in all_books]
    # Continue: the book the learner touched last and hasn't finished.
    reading = [prog[c["slug"]] for c in cards if c["status"] == "in_progress" and c["slug"] in prog]
    cont = max(reading, key=lambda p: p.updated_at).slug if reading else None
    # Recommended: the next unread book in reading order at the learner's
    # own level, else the nearest open level below.
    open_new = [c for c in cards if c["status"] == "new"]
    at_level = [c for c in open_new if c["gate"] == min(level, 7)]
    below = sorted((c for c in open_new if c["gate"] < min(level, 7)), key=lambda c: (-c["level"], c["order"]))
    recommended = (at_level or below or [{}])[0].get("slug")
    per_level = {}
    for c in cards:
        s = per_level.setdefault(c["level"], {"level": c["level"], "books": 0, "completed": 0, "locked": c["status"] == "locked"})
        s["books"] += 1
        s["completed"] += c["status"] == "completed"
    return {
        "level": level, "books": cards, "recommended": recommended, "continue": cont,
        "levels": [per_level.get(lvl, {"level": lvl, "books": 0, "completed": 0, "locked": min(lvl, 7) > level})
                   for lvl in range(1, 10)],
        "topics": sorted({c["topic"] for c in cards}),
        "counts": {k: sum(1 for c in cards if c["status"] == k) for k in ("completed", "in_progress")},
    }


def _open(db: Session, user: models.User, slug: str) -> tuple[dict, int]:
    from app.services.gamification import user_rank

    book = lib.get(slug)
    if book is None:
        raise StoryError(404, "Story not found")
    level, _ = user_rank(db, user)
    if gate(book) > level:
        raise StoryError(403, f"This story opens at HSK {gate(book)}")
    return book, level


def _chapter(book: dict, n: int) -> dict:
    if not isinstance(n, int) or not 1 <= n <= len(book["chapters"]):
        raise StoryError(404, "Chapter not found")
    return book["chapters"][n - 1]


def stats(db: Session, user: models.User, book: dict, p: models.StoryProgress | None, r: dict | None) -> dict:
    """What the learner really did with this book -- every number counted
    from their own records."""
    prof = profile(db, book)
    known = _word_states(db, user, prof["word_ids"])
    return {
        "chapters": len(_done_chapters(book, p, r)), "chapters_total": len(book["chapters"]),
        "words_known": sum(1 for s in known.values() if s in ("known", "learning", "review")),
        "words_total": len(prof["word_ids"]),
        "looked_up": len((p.looked_up or {}) if p else {}),
        "explained": p.explained if p else 0, "listened": p.listened if p else 0,
        "rounds": r["rounds"] if r else 0, "best": round(r["best"], 1) if r else 0.0,
    }


def view(db: Session, user: models.User, slug: str, locale: str) -> dict:
    """A book's page: its chapters, the learner's place in it and its words."""
    book, level = _open(db, user, slug)
    prof = profile(db, book)
    rounds, prog = _rounds(db, user), _progress_rows(db, user)
    p, r = prog.get(slug), rounds.get(slug)
    done = _done_chapters(book, p, r)
    known = _word_states(db, user, prof["word_ids"])
    lv = sent._level_map(db)
    rows = {w.id: w for w in db.query(models.VocabularyWord).filter(models.VocabularyWord.id.in_(prof["word_ids"] or [0]))}
    meanings = ss.meanings(db, list(prof["word_ids"]), locale)
    order = {"new": 0, "review": 1, "learning": 2, "known": 3}
    words = sorted(
        ({"id": w.id, "text": w.simplified, "pinyin": w.pinyin, "level": lv.get(w.hsk_level_id, 9),
          "meaning": meanings.get(w.id, ""), "state": known.get(w.id, "new")} for w in rows.values()),
        key=lambda w: (order[w["state"]], -w["level"], w["text"]))
    completed = _completed(book, p, r)
    nxt = None
    if completed:
        nxt = next_book(db, user, book, level, locale)
    return {
        "slug": slug, "level": book["level"], "gate": gate(book), "topic": book["topic"], "icon": book["icon"],
        "title": _text(book["title"], locale), "title_zh": book["title"]["zh"],
        "summary": _text(book["summary"], locale),
        "minutes": prof["minutes"], "difficulty": difficulty(db, book), "characters": book["characters"],
        "support": support(book["level"]),
        "chapters": [{"n": i + 1, "title": _text(c["title"], locale), "title_zh": c["title"]["zh"],
                      "sentences": len(c["sentences"]), "questions": len(c["questions"]), "done": i in done}
                     for i, c in enumerate(book["chapters"])],
        "progress": {
            "started": p is not None or bool(done), "chapter": (p.chapter + 1) if p else 1,
            "position": p.position if p else 0, "percent": _percent(book, p, done), "completed": completed,
        },
        "words": words[:40], "word_count": len(words),
        "counts": {k: sum(1 for w in words if w["state"] == k) for k in ("new", "review", "learning", "known")},
        "stats": stats(db, user, book, p, r) if (p is not None or r) else None,
        "next": nxt,
    }


def next_book(db: Session, user: models.User, book: dict, level: int, locale: str) -> dict | None:
    """The next book to read after this one: the next unfinished open book
    in reading order, at this book's level first."""
    done = read_slugs(db, user)
    cands = [b for b in lib.all_books() if b["slug"] != book["slug"] and b["slug"] not in done and gate(b) <= level]
    cands.sort(key=lambda b: (b["level"] != book["level"], abs(b["level"] - book["level"]), b["level"], b["order"]))
    if not cands:
        return None
    b = cands[0]
    return {"slug": b["slug"], "title": _text(b["title"], locale), "title_zh": b["title"]["zh"],
            "level": b["level"], "icon": b["icon"]}


def chapter_view(db: Session, user: models.User, slug: str, n: int, locale: str) -> dict:
    """One chapter to read: Chinese only (with pinyin to toggle), words
    marked from the learner's records. No translations -- those come on
    request (explain)."""
    book, level = _open(db, user, slug)
    ch = _chapter(book, n)
    prof = profile(db, book)
    toks_by_sentence = prof["chapters"][n - 1]
    ids = {wid for row in toks_by_sentence for _t, wid, _k in row if wid}
    known = _word_states(db, user, ids)
    lv = sent._level_map(db)
    words = {w.id: w for w in db.query(models.VocabularyWord).filter(models.VocabularyWord.id.in_(ids or [0]))}
    paragraphs, k = [], 0
    for para in ch["paragraphs"]:
        out = []
        for s in para:
            tokens = []
            for text, wid, kind in toks_by_sentence[k]:
                if wid and wid in words:
                    tokens.append({"text": text, "word_id": wid, "state": known.get(wid, "new"),
                                   "level": lv.get(words[wid].hsk_level_id, 9)})
                elif kind == "name":
                    tokens.append({"text": text, "name": book["names"][text]})
                else:
                    tokens.append({"text": text})
            out.append({"i": k, "zh": s["zh"], "pinyin": pinyin_of(db, book, s["zh"]), "tokens": tokens})
            k += 1
        paragraphs.append(out)
    p = _progress_rows(db, user).get(slug)
    r = _rounds(db, user).get(slug)
    done = _done_chapters(book, p, r)
    return {
        "slug": slug, "n": n, "total": len(book["chapters"]), "level": book["level"], "icon": book["icon"],
        "book_title": _text(book["title"], locale), "book_title_zh": book["title"]["zh"],
        "title": _text(ch["title"], locale), "title_zh": ch["title"]["zh"],
        "paragraphs": paragraphs, "support": support(book["level"]),
        "position": p.position if p is not None and p.chapter == n - 1 else 0,
        "done": (n - 1) in done, "questions": len(ch["questions"]),
        "percent": _percent(book, p, done),
    }


# --------------------------------------------------------------------------- progress
def _row(db: Session, user: models.User, slug: str) -> models.StoryProgress:
    p = db.query(models.StoryProgress).filter_by(user_id=user.id, slug=slug).first()
    if p is None:
        p = models.StoryProgress(user_id=user.id, slug=slug, chapter=0, position=0, chapters_done=[],
                                 explained=0, listened=0, looked_up={})
        db.add(p)
        try:
            db.flush()
        except IntegrityError:  # a parallel first action created it
            db.rollback()
            p = db.query(models.StoryProgress).filter_by(user_id=user.id, slug=slug).one()
    return p


def save_position(db: Session, user: models.User, slug: str, n: int, position: int) -> dict:
    """The bookmark: the chapter and sentence the learner is reading."""
    book, _ = _open(db, user, slug)
    ch = _chapter(book, n)
    if not isinstance(position, int) or not 0 <= position < max(1, len(ch["sentences"])):
        raise StoryError(422, "position is outside the chapter")
    p = _row(db, user, slug)
    p.chapter, p.position, p.updated_at = n - 1, position, datetime.utcnow()
    db.commit()
    return {"chapter": n, "position": position}


def finish_chapter(db: Session, user: models.User, slug: str, n: int, locale: str) -> dict:
    """The learner read a chapter to its end. Finishing the last unread one
    finishes the book (once); the next chapter becomes the bookmark."""
    from app.services.activity import log_activity
    from app.services.gamification import check_achievements

    book, level = _open(db, user, slug)
    _chapter(book, n)
    p = _row(db, user, slug)
    r = _rounds(db, user).get(slug)
    was_completed = _completed(book, p, r)
    done = set(p.chapters_done or [])
    newly = (n - 1) not in done
    if newly:
        done.add(n - 1)
        p.chapters_done = sorted(done)  # a new list, so the JSON column is marked dirty
        log_activity(db, user, "story_chapter")
    total = len(book["chapters"])
    if n < total:
        p.chapter, p.position = n, 0
    p.updated_at = datetime.utcnow()
    book_done = not was_completed and _completed(book, p, r)
    if book_done:
        p.completed_at = datetime.utcnow()
        log_activity(db, user, "story_book")
    db.commit()
    check_achievements(db, user)
    db.refresh(p)
    return {
        "chapter": n, "chapters_done": len(_done_chapters(book, p, r)), "total": total,
        "book_completed": _completed(book, p, r), "just_completed": book_done,
        "next_chapter": n + 1 if n < total else None,
        "stats": stats(db, user, book, p, r) if book_done else None,
        "next": next_book(db, user, book, level, locale) if book_done else None,
    }


def listened(db: Session, user: models.User, slug: str, n: int) -> dict:
    from app.services.activity import log_activity

    book, _ = _open(db, user, slug)
    _chapter(book, n)
    p = _row(db, user, slug)
    p.listened = (p.listened or 0) + 1
    p.updated_at = datetime.utcnow()
    log_activity(db, user, "story_listen")
    db.commit()
    return {"listened": p.listened}


def looked_up(db: Session, user: models.User, slug: str, word_id: int) -> dict:
    """A word the learner tapped while reading (only words of this book)."""
    book, _ = _open(db, user, slug)
    if word_id not in profile(db, book)["word_ids"]:
        raise StoryError(404, "This word is not in the story")
    p = _row(db, user, slug)
    counts = dict(p.looked_up or {})
    counts[str(word_id)] = counts.get(str(word_id), 0) + 1
    p.looked_up = counts
    p.updated_at = datetime.utcnow()
    db.commit()
    return {"times": counts[str(word_id)]}


def round_finished(db: Session, user: models.User, session: models.PracticeSession) -> None:
    """A completed story round also finishes its chapter (practice.complete_session)."""
    ctx = (session.questions or [{}])[0].get("ctx") or {}
    book = lib.get(ctx.get("slug") or "")
    if book is None:
        return
    ci = int(ctx.get("chapter") or 0)
    p = _row(db, user, book["slug"])
    done = set(p.chapters_done or [])
    if ci not in done:
        p.chapters_done = sorted(done | {ci})
    if p.completed_at is None and len(_done_chapters(book, p, None)) == len(book["chapters"]):
        p.completed_at = datetime.utcnow()
    p.updated_at = datetime.utcnow()


# --------------------------------------------------------------------------- help while reading
_ai_calls: dict[int, list[float]] = {}


def _ai_allowed(user_id: int) -> bool:
    now = time.monotonic()
    calls = [t for t in _ai_calls.get(user_id, []) if now - t < 3600]
    _ai_calls[user_id] = calls
    return len(calls) < AI_PER_HOUR


def _band(level: int) -> int:
    return 1 if level <= 2 else 3 if level <= 4 else 5 if level <= 6 else 7


def _book_translation(ch: dict, text: str, locale: str) -> str | None:
    """The book's own translation when the selection is one or more whole,
    consecutive sentences (no AI needed)."""
    if locale == "zh":
        return None
    flat = ch["sentences"]
    for i in range(len(flat)):
        acc = ""
        for j in range(i, len(flat)):
            acc += flat[j]["zh"]
            if acc == text:
                return " ".join(_text(s, locale) for s in flat[i:j + 1])
            if len(acc) >= len(text) or not text.startswith(acc):
                break
    return None


def explain(db: Session, user: models.User, slug: str, n: int, text: str, focus: str, locale: str) -> dict:
    """Help with a selected piece of a chapter. Curriculum data always; the
    AI explanation only when the learner asks for it (focus explain/grammar)."""
    from app.services import ai_client
    from app.services.activity import log_activity
    from app.services.localization import load_translations, tr

    book, level = _open(db, user, slug)
    ch = _chapter(book, n)
    text = "".join((text or "").split())
    chapter_text = "".join(s["zh"] for s in ch["sentences"])
    if not text or not sent._CJK.search(text):
        raise StoryError(422, "Select some Chinese text")
    if len(text) > MAX_SELECTION:
        raise StoryError(422, f"Select at most {MAX_SELECTION} characters")
    if text not in chapter_text:
        raise StoryError(422, "The selection is not part of this chapter")
    if focus not in ("explain", "pinyin", "translate", "words", "grammar"):
        raise StoryError(422, "Unknown kind of help")

    levels = sent._level_map(db)
    toks = segment(db, book, text)
    words = [t["word"] for t in toks if t["word"] is not None]
    states = _word_states(db, user, {w.id for w in words})
    meanings = ss.meanings(db, [w.id for w in words], locale)
    loose = {t["text"] for t in toks if t["kind"] == "char"}
    hanzi = sent.hanzi_rows(db, loose)
    hanzi_tr = load_translations(db, "hanzi", [str(h.id) for h in hanzi.values()], locale)
    breakdown = []
    for t in toks:
        if t["word"] is not None:
            w = t["word"]
            breakdown.append({"text": t["text"], "word_id": w.id, "pinyin": w.pinyin, "meaning": meanings.get(w.id, ""),
                              "level": levels.get(w.hsk_level_id), "state": states.get(w.id, "new")})
        elif t["kind"] == "name":
            breakdown.append({"text": t["text"], "pinyin": t["pinyin"], "meaning": "", "level": None, "name": True})
        elif t["kind"] == "char":
            h = hanzi.get(t["text"])
            breakdown.append({"text": t["text"], "pinyin": h.pinyin if h else "",
                              "meaning": tr(hanzi_tr, h.id, "meaning", h.meaning) if h else "", "level": None})
    grammar_rows = sent.match_grammar(db, text)
    grammar_tr = load_translations(db, "grammar_topic", [str(g.id) for g in grammar_rows], locale)
    grammar = [{"title": tr(grammar_tr, g.id, "title", g.title), "pattern": g.pattern,
                "explanation": tr(grammar_tr, g.id, "explanation", g.explanation),
                "level": levels.get(g.hsk_level_id)} for g in grammar_rows]

    translation, source = _book_translation(ch, text, locale), "book"
    if translation is None and focus in ("translate", "explain") and locale != "zh":
        translation, source = ai_client.translate_sentence(text, locale), "ai"
    ai, ai_status = None, "skipped"
    if focus in ("explain", "grammar"):
        ai, ai_status = _ai_explanation(db, user, text, locale, level, breakdown, [g["title"] for g in grammar])
        if ai and not translation and ai.get("translation"):
            translation, source = ai["translation"], "ai"

    p = _row(db, user, slug)
    p.explained = (p.explained or 0) + 1
    p.updated_at = datetime.utcnow()
    log_activity(db, user, "story_explain")
    db.commit()
    return {
        "text": text, "pinyin": pinyin_of(db, book, text, toks), "focus": focus,
        "translation": {"text": translation, "source": source if translation else None},
        "words": breakdown, "grammar": grammar, "ai": ai, "ai_status": ai_status,
    }


def _ai_explanation(db: Session, user: models.User, text: str, locale: str, level: int,
                    breakdown: list[dict], grammar: list[str]) -> tuple[dict | None, str]:
    from app.services import ai_client

    band = _band(level)
    key = hashlib.sha256(f"reading|v1|{locale}|{band}|{text}".encode("utf-8")).hexdigest()
    hit = db.query(models.AIExplanation).filter_by(key=key).first()
    if hit is not None:
        return hit.payload, "cached"
    if not _ai_allowed(user.id):
        return None, "limit"
    _ai_calls.setdefault(user.id, []).append(time.monotonic())
    out = ai_client.explain_reading(text, locale, band, [b for b in breakdown if b.get("meaning")], grammar)
    if out is None:
        return None, "offline"
    db.add(models.AIExplanation(key=key, kind="reading", locale=locale, text=text, payload=out))
    try:
        db.flush()
    except IntegrityError:  # another request cached the same answer first
        db.rollback()
    return out, "ok"


# --------------------------------------------------------------------------- the graded round
def build_questions(db: Session, user: models.User, slug: str, level: int, rng: random.Random,
                    translated: dict | None, chapter: int | None = None) -> list[dict]:
    from app.services import internet, practice

    book = lib.get(slug or "")
    if book is None:
        raise StoryError(404, "Story not found")
    if gate(book) > level:
        raise StoryError(403, f"This story opens at HSK {gate(book)}")
    n = chapter or 1
    ch = _chapter(book, n)
    show_py = book["level"] <= 3
    questions: list[dict] = []
    for cq in ch["questions"]:
        order = list(range(len(cq["options"])))
        rng.shuffle(order)
        opts = [cq["options"][k] for k in order]
        questions.append({
            "type": "story_q", "item_type": "reading", "q": cq["q"],
            "q_py": pinyin_of(db, book, cq["q"]) if show_py else None,
            "q_tr": {k: v for k, v in (cq.get("tr") or {}).items() if k in LOCALES and v},
            "options": [{"zh": o, "py": pinyin_of(db, book, o) if show_py else ""} for o in opts],
            "item_id": order.index(cq["answer"]), "option_ids": list(range(len(opts))),
            "focus_id": internet._focus_of(db, cq["options"][cq["answer"]]), "show_py": show_py,
        })
    # Listening: one of the chapter's sentences heard among two others --
    # and then said aloud (the engine's speak step grades it).
    lines = [s["zh"] for s in ch["sentences"]]
    if len(lines) >= 3:
        heard = lines[ch["say"]] if ch["say"] is not None else rng.choice(lines)
        others = [x for x in lines if x != heard]
        rng.shuffle(others)
        opts = [heard] + others[:2]
        rng.shuffle(opts)
        questions.insert(min(1, len(questions)), {
            "type": "story_listen", "item_type": "reading", "speak": heard, "rate": support(book["level"])["rate"],
            "options": [{"zh": o, "py": ""} for o in opts], "item_id": opts.index(heard),
            "option_ids": list(range(len(opts))), "focus_id": internet._focus_of(db, heard), "show_py": False,
            "say": {"zh": heard},
        })
    # Up to three of the chapter's words the learner hasn't mastered yet, as
    # real vocabulary cards (the same items Review brings back).
    ids = [wid for row in profile(db, book)["chapters"][n - 1] for _t, wid, _k in row if wid]
    states = _word_states(db, user, set(ids))
    seen, rows = set(), []
    for wid in ids:
        if wid in seen:
            continue
        seen.add(wid)
        if states.get(wid) != "known":
            r = db.get(models.VocabularyWord, wid)
            if r is not None and practice._usable("vocab", r) and len(r.simplified) >= 2:
                rows.append(r)
    for k, r in enumerate(rows[:3]):
        q = practice._question(db, "vocab", r, k, rng, translated)
        if q:
            questions.append(q)
    if not questions:
        raise StoryError(422, "This chapter has nothing to practise yet")
    questions[0]["ctx"] = {"kind": "story", "slug": slug, "chapter": n - 1, "level": book["level"],
                           "icon": book["icon"], "title": book["title"]["zh"]}
    return questions
