"""Character DNA and the Vocabulary Ecosystem.

Both are READ-ONLY views over data the project already holds -- nothing
here invents a dictionary relationship or a learning event:

  structure     Hanzi.radical / Hanzi.decomposition (the bundled
                makemeahanzi-derived dataset; "？" marks an unknown part and
                is left out)
  words         VocabularyWord rows that actually contain the character
  characters    same radical / shared component (Hanzi rows), and the
                characters it really combines with in those words
  examples      the curriculum's own example sentences
  the learner   UserHanzi / UserVocabulary (status, mastery, schedule),
                PracticeSession answers (first met, recent practice,
                confusions), HanziTraceAttempt, LearningMistake

The ecosystem is the same data as a small graph around one character:
character -> compounds -> the other characters in them, filtered by HSK
level and capped so a request never loads more than a screenful.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.services import story_slots as ss
from app.services.localization import load_translations, tr

_CJK = re.compile(r"^[㐀-鿿]$")
_IDS = re.compile(r"[⿰-⿻？?]")
MAX_WORDS = 40
ECO_WORDS = 18
ECO_CHARS = 18


class CharacterError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def _levels(db: Session) -> dict[int, int]:
    return {lvl.id: lvl.level for lvl in db.query(models.HSKLevel).all()}


def _hanzi(db: Session, chars: list[str], levels: dict[int, int]) -> dict[str, models.Hanzi]:
    rows = db.query(models.Hanzi).filter(models.Hanzi.character.in_(chars or [""])).all()
    best: dict[str, models.Hanzi] = {}
    for r in sorted(rows, key=lambda r: (levels.get(r.hsk_level_id, 99), r.id)):
        best.setdefault(r.character, r)
    return best


def _hanzi_meanings(db: Session, rows: list[models.Hanzi], locale: str) -> dict[int, str]:
    trs = load_translations(db, "hanzi", [str(r.id) for r in rows], locale)
    out = {}
    for r in rows:
        label = tr(trs, r.id, "meaning", r.meaning) or ""
        if label.strip() == r.character:
            label = r.meaning or ""
        out[r.id] = label
    return out


def components(decomposition: str | None) -> list[str]:
    return [c for c in _IDS.sub("", decomposition or "") if c.strip()]


def _word_status(db: Session, user: models.User, ids: list[int]) -> dict[int, models.UserVocabulary]:
    return {r.word_id: r for r in db.query(models.UserVocabulary).filter(
        models.UserVocabulary.user_id == user.id, models.UserVocabulary.word_id.in_(ids or [0]))}


def _word_card(w: models.VocabularyWord, rec, meaning: str, level: int | None, now: datetime) -> dict:
    return {
        "id": w.id, "text": w.simplified, "pinyin": w.pinyin, "meaning": meaning, "level": level,
        "status": rec.status if rec else "new", "mastery": round(rec.mastery or 0, 1) if rec else 0.0,
        "due": bool(rec and rec.next_review_at and rec.next_review_at <= now),
        "example": w.example, "example_pinyin": w.example_pinyin,
    }


def _check_char(char: str) -> str:
    char = (char or "").strip()
    if not _CJK.match(char):
        raise CharacterError(422, "Give one Chinese character")
    return char


def character_dna(db: Session, user: models.User, char: str, locale: str) -> dict:
    from app.services.companion_memory import confusion_pairs

    char = _check_char(char)
    levels = _levels(db)
    now = datetime.utcnow()
    h = _hanzi(db, [char], levels).get(char)
    words = (
        db.query(models.VocabularyWord)
        .filter(models.VocabularyWord.simplified.contains(char))
        .join(models.HSKLevel, models.VocabularyWord.hsk_level_id == models.HSKLevel.id)
        .order_by(models.HSKLevel.level, func.length(models.VocabularyWord.simplified), models.VocabularyWord.id)
        .limit(MAX_WORDS)
        .all()
    )
    if h is None and not words:
        raise CharacterError(404, "This character isn't in the ChineseVerse curriculum yet")

    # ---- structure
    comps = components(h.decomposition if h else None)
    comp_rows = _hanzi(db, comps + ([h.radical] if h and h.radical else []), levels)
    same_radical = []
    if h and h.radical:
        same_radical = (
            db.query(models.Hanzi).filter(models.Hanzi.radical == h.radical, models.Hanzi.character != char)
            .order_by(models.Hanzi.hsk_level_id, models.Hanzi.id).limit(12).all()
        )
    shared = []
    parts = [c for c in comps if c != (h.radical if h else None)]
    if parts:
        q = db.query(models.Hanzi).filter(models.Hanzi.character != char)
        from sqlalchemy import or_

        q = q.filter(or_(*[models.Hanzi.decomposition.contains(p) for p in parts[:3]]))
        shared = [r for r in q.order_by(models.Hanzi.hsk_level_id, models.Hanzi.id).limit(12).all()
                  if r.id not in {x.id for x in same_radical}][:8]

    # ---- words, partners, examples
    recs = _word_status(db, user, [w.id for w in words])
    wm = ss.meanings(db, [w.id for w in words], locale)
    cards = [_word_card(w, recs.get(w.id), wm.get(w.id, ""), levels.get(w.hsk_level_id), now) for w in words]
    multi = [c for c in cards if len(c["text"]) > 1]
    tree = {
        "starts": [c for c in multi if c["text"].startswith(char)],
        "ends": [c for c in multi if c["text"].endswith(char) and not c["text"].startswith(char)],
        "inside": [c for c in multi if not c["text"].startswith(char) and not c["text"].endswith(char)],
    }
    partner_counts = Counter(c for w in words if len(w.simplified) > 1 for c in w.simplified if c != char and _CJK.match(c))
    partner_rows = _hanzi(db, [c for c, _n in partner_counts.most_common(12)], levels)
    all_hanzi = list(comp_rows.values()) + same_radical + shared + list(partner_rows.values()) + ([h] if h else [])
    hm = _hanzi_meanings(db, all_hanzi, locale)

    def hcard(r: models.Hanzi, **extra) -> dict:
        return {"char": r.character, "pinyin": r.pinyin, "meaning": hm.get(r.id, ""), "level": levels.get(r.hsk_level_id), **extra}

    examples = []
    seen = set()
    for w in (db.query(models.VocabularyWord)
              .filter(models.VocabularyWord.example.isnot(None), models.VocabularyWord.example.contains(char))
              .join(models.HSKLevel, models.VocabularyWord.hsk_level_id == models.HSKLevel.id)
              .order_by(models.HSKLevel.level, models.VocabularyWord.id).limit(12)):
        if w.example in seen:
            continue
        seen.add(w.example)
        examples.append({"text": w.example, "pinyin": w.example_pinyin, "word": w.simplified})
        if len(examples) >= 6:
            break

    # ---- the learner's own history with it
    uh = db.query(models.UserHanzi).filter_by(user_id=user.id, hanzi_id=h.id).first() if h else None
    word_ids = {w.id for w in words}
    sessions = (db.query(models.PracticeSession).filter(models.PracticeSession.user_id == user.id)
                .order_by(models.PracticeSession.created_at.desc()).limit(500).all())
    events = []
    for s in sessions:
        for qq, a in zip(s.questions or [], s.answers or []):
            if not a:
                continue
            it, iid = qq.get("item_type"), qq.get("item_id")
            hit = (it == "hanzi" and h is not None and iid == h.id) or (it == "vocab" and iid in word_ids) or (
                qq.get("focus_id") in word_ids)
            if hit:
                at = a.get("answered_at") or (s.created_at.isoformat() if s.created_at else None)
                label = char if it == "hanzi" else next((w.simplified for w in words if w.id in (iid, qq.get("focus_id"))), char)
                events.append({"at": at, "correct": bool(a.get("correct")), "item": label, "type": qq.get("type"),
                               "source": s.source})
    events.sort(key=lambda e: e["at"] or "")
    traces = db.query(models.HanziTraceAttempt).filter_by(user_id=user.id, hanzi_id=h.id).order_by(
        models.HanziTraceAttempt.started_at).all() if h else []
    firsts = [e["at"] for e in events if e["at"]] + [t.started_at.isoformat() for t in traces[:1]]
    first_seen = min(firsts) if firsts else None

    texts = [char] + [w.simplified for w in words]
    mistakes = [
        {"reference": m.reference, "type": m.mistake_type, "times": m.occurrences, "mastered": m.mastered,
         "last_seen_at": m.last_seen_at.isoformat() if m.last_seen_at else None}
        for m in db.query(models.LearningMistake).filter(
            models.LearningMistake.user_id == user.id, models.LearningMistake.reference.in_(texts))
        .order_by(models.LearningMistake.occurrences.desc()).limit(10)
    ]
    confusions = []
    for (item_type, lo, hi), n in confusion_pairs(sessions).most_common():
        mine = (item_type == "hanzi" and h is not None and h.id in (lo, hi)) or (item_type == "vocab" and (lo in word_ids or hi in word_ids))
        if not mine:
            continue
        a_id, b_id = (lo, hi) if (item_type == "vocab" and lo in word_ids) or (h and lo == h.id) else (hi, lo)
        model = models.Hanzi if item_type == "hanzi" else models.VocabularyWord
        a, b = db.get(model, a_id), db.get(model, b_id)
        if a and b:
            txt = lambda r: getattr(r, "character", None) or r.simplified  # noqa: E731
            confusions.append({"item": txt(a), "with": txt(b), "with_pinyin": b.pinyin, "times": n})
        if len(confusions) >= 5:
            break

    mastered = sum(1 for c in cards if c["status"] == "mastered")
    due_words = [c for c in cards if c["due"]]
    return {
        "char": char,
        "hanzi_id": h.id if h else None,
        "pinyin": h.pinyin if h else (words[0].pinyin if len(words[0].simplified) == 1 else ""),
        "meaning": hm.get(h.id, "") if h else "",
        "level": levels.get(h.hsk_level_id) if h else None,
        "stroke_count": h.stroke_count if h else None,
        "radical": hcard(comp_rows[h.radical]) if h and h.radical in comp_rows else (
            {"char": h.radical, "pinyin": "", "meaning": "", "level": None} if h and h.radical else None),
        "decomposition": h.decomposition if h else None,
        "components": [hcard(comp_rows[c]) if c in comp_rows else {"char": c, "pinyin": "", "meaning": "", "level": None}
                       for c in comps],
        "handwriting_tier": h.handwriting_tier if h else None,
        "words": cards,
        "tree": tree,
        "related": {
            "same_radical": [hcard(r) for r in same_radical],
            "shared_component": [hcard(r) for r in shared],
            "partners": [hcard(partner_rows[c], count=n) for c, n in partner_counts.most_common(12) if c in partner_rows],
        },
        "examples": examples,
        "mine": {
            "status": uh.status if uh else "new",
            "mastery": round(uh.mastery or 0, 1) if uh else 0.0,
            "times_seen": uh.times_seen if uh else 0,
            "times_missed": uh.times_missed if uh else 0,
            "writing_status": uh.writing_status if uh else "not_practiced",
            "writing_mastery": round(uh.writing_mastery or 0, 1) if uh else 0.0,
            "times_written": uh.times_written if uh else 0,
            "last_reviewed_at": uh.last_reviewed_at.isoformat() if uh and uh.last_reviewed_at else None,
            "next_review_at": uh.next_review_at.isoformat() if uh and uh.next_review_at else None,
            "due": bool(uh and uh.next_review_at and uh.next_review_at <= now),
            "first_seen_at": first_seen,
            "traces": len(traces),
            "recent": list(reversed(events[-8:])),
            "practice_count": len(events),
            "mistakes": mistakes,
            "confusions": confusions,
            "words_mastered": mastered,
            "words_total": len(cards),
            "words_due": len(due_words),
        },
    }


# --------------------------------------------------------------------------- ecosystem

def default_center(db: Session, user: models.User) -> str:
    """The character the learner meets most across their own words, else a
    basic one from the curriculum."""
    texts = [w.simplified for w in db.query(models.VocabularyWord)
             .join(models.UserVocabulary, models.UserVocabulary.word_id == models.VocabularyWord.id)
             .filter(models.UserVocabulary.user_id == user.id).limit(400)]
    counts = Counter(c for t in texts for c in t if _CJK.match(c))
    for c, _n in counts.most_common(20):
        if db.query(models.Hanzi.id).filter_by(character=c).first():
            return c
    return "学"


def ecosystem(db: Session, user: models.User, center: str | None, hsk_max: int | None, locale: str) -> dict:
    from app.services.gamification import user_rank

    level, _ = user_rank(db, user)
    hsk_max = max(1, min(7, hsk_max or max(level, 1)))
    center = _check_char(center) if center else default_center(db, user)
    levels = _levels(db)
    now = datetime.utcnow()
    allowed = {lid for lid, lvl in levels.items() if lvl <= hsk_max}
    words = (
        db.query(models.VocabularyWord)
        .filter(models.VocabularyWord.simplified.contains(center),
                models.VocabularyWord.hsk_level_id.in_(allowed or {0}),
                func.length(models.VocabularyWord.simplified) > 1)
        .all()
    )
    recs = _word_status(db, user, [w.id for w in words])
    # The learner's own words first, then by level and length.
    words.sort(key=lambda w: (w.id not in recs, levels.get(w.hsk_level_id, 9), len(w.simplified), w.id))
    total_compounds = len(words)
    words = words[:ECO_WORDS]
    wm = ss.meanings(db, [w.id for w in words], locale)
    word_nodes = [_word_card(w, recs.get(w.id), wm.get(w.id, ""), levels.get(w.hsk_level_id), now) for w in words]

    partner = Counter(c for w in words for c in w.simplified if c != center and _CJK.match(c))
    chars = [c for c, _n in partner.most_common(ECO_CHARS)]
    hrows = _hanzi(db, [center] + chars, levels)
    hm = _hanzi_meanings(db, list(hrows.values()), locale)
    hrecs = {r.hanzi_id: r for r in db.query(models.UserHanzi).filter(
        models.UserHanzi.user_id == user.id, models.UserHanzi.hanzi_id.in_([r.id for r in hrows.values()] or [0]))}
    # How many more compounds each neighbour opens (within the level filter):
    # one grouped count, not one query per character.
    degree = {}
    for c in chars:
        degree[c] = db.query(func.count(models.VocabularyWord.id)).filter(
            models.VocabularyWord.simplified.contains(c), models.VocabularyWord.hsk_level_id.in_(allowed or {0}),
            func.length(models.VocabularyWord.simplified) > 1).scalar() or 0

    def char_node(c: str) -> dict:
        r = hrows.get(c)
        rec = hrecs.get(r.id) if r else None
        return {"id": f"c:{c}", "kind": "char", "text": c, "pinyin": r.pinyin if r else "",
                "meaning": hm.get(r.id, "") if r else "", "level": levels.get(r.hsk_level_id) if r else None,
                "status": rec.status if rec else "new", "has_dna": r is not None,
                "due": bool(rec and rec.next_review_at and rec.next_review_at <= now),
                "compounds": degree.get(c)}

    nodes = [{**char_node(center), "center": True}]
    nodes += [{**n, "id": f"w:{n['id']}", "kind": "word", "word_id": n["id"]} for n in word_nodes]
    nodes += [char_node(c) for c in chars]
    edges = [{"from": f"c:{center}", "to": f"w:{n['id']}"} for n in word_nodes]
    edges += [{"from": f"w:{w.id}", "to": f"c:{c}"} for w in words for c in dict.fromkeys(w.simplified)
              if c != center and c in chars]
    by_status = Counter(n["status"] for n in word_nodes)
    by_level = Counter(n["level"] for n in word_nodes)
    return {
        "center": center, "hsk_max": hsk_max, "level": level,
        "nodes": nodes, "edges": edges,
        "stats": {
            "compounds_total": total_compounds, "shown": len(word_nodes),
            "mastered": by_status.get("mastered", 0), "learning": by_status.get("learning", 0) + by_status.get("reviewing", 0),
            "new": by_status.get("new", 0), "due": sum(1 for n in word_nodes if n["due"]),
            "by_level": {str(k): v for k, v in sorted(by_level.items(), key=lambda kv: kv[0] or 0)},
        },
        "suggested": [n for n in word_nodes if n["status"] == "new" and (n["level"] or 9) <= level][:3],
    }
