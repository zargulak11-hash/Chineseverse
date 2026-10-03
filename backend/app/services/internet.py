"""Chinese Internet: realistic online Chinese, adapted to the learner.

The content is curated (services/internet_content.py): every item exists
as the ORIGINAL plus intermediate and beginner rewrites of the same facts.
What this module adds is the learner:

  recommended version  the hardest version whose words this learner can
                       mostly read -- coverage counted from their own
                       UserVocabulary rows (reviewing/mastered = known,
                       learning = half), plus curriculum words below their
                       current HSK level; Learning DNA reading moves the
                       bar (a strong reader is trusted with less coverage)
  word states          every word in the text marked from their data:
                       mastered / reviewing / learning / due / weak (an
                       open mistake or repeated misses) / new, and above
                       their level or not
  glossary             the words worth stopping for: weak and due words
                       first, then new words within reach
  grammar              curriculum grammar points the text really uses
                       (services/sentence.GRAMMAR_RULES)
  word help            meaning, reading, the learner's own state with the
                       word, related words, its characters, the sentence
                       it appears in -- and "add to review" only when the
                       word isn't already in their schedule

Reading an item is free; the graded part (comprehension, listening, the
glossary words) is a practice round (practice.build_session, source
"internet"), so scores, SRS, mistakes and DNA stay server-side.
"""

from __future__ import annotations

import random
import re
from datetime import datetime

from sqlalchemy.orm import Session

from app import models
from app.services import sentence as sent
from app.services import story_slots as ss
from app.services.internet_content import ITEM_BY_SLUG, ITEMS, VERSIONS
from app.services.localization import load_translations, tr

_CJK = re.compile(r"[㐀-鿿]")
COVERAGE_BAR = 0.8          # share of words a version needs to be "readable"
STRONG_READER, WEAK_READER = 60.0, 20.0


class InternetError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def _text(item: dict, version: str) -> str:
    return "\n".join(b["text"] for b in item["versions"][version])


def _levels(db: Session) -> dict[int, int]:
    return {lvl.id: lvl.level for lvl in db.query(models.HSKLevel).all()}


def _reader_profile(db: Session, user: models.User) -> dict:
    from app.services.gamification import ensure_user_skills, user_rank

    ensure_user_skills(db, user)
    level, _ = user_rank(db, user)
    reading = next((s.mastery for s in user.user_skills if s.skill and s.skill.code == "reading"), 0.0) or 0.0
    bar = COVERAGE_BAR - (0.1 if reading >= STRONG_READER else 0.0) + (0.1 if reading < WEAK_READER and level >= 3 else 0.0)
    return {"level": level, "reading": round(reading, 1), "bar": round(bar, 2)}


class _UserWords:
    """The learner's records for a batch of words (one query each)."""

    def __init__(self, db: Session, user: models.User, words: list[models.VocabularyWord]):
        ids = [w.id for w in words]
        self.recs = {r.word_id: r for r in db.query(models.UserVocabulary).filter(
            models.UserVocabulary.user_id == user.id, models.UserVocabulary.word_id.in_(ids or [0]))}
        texts = [w.simplified for w in words]
        self.open_mistakes = {m.reference: m.occurrences for m in db.query(models.LearningMistake).filter(
            models.LearningMistake.user_id == user.id, models.LearningMistake.mastered.is_(False),
            models.LearningMistake.reference.in_(texts or [""]))}
        self.now = datetime.utcnow()

    def state(self, w: models.VocabularyWord) -> dict:
        rec = self.recs.get(w.id)
        due = bool(rec and rec.next_review_at and rec.next_review_at <= self.now and rec.status != "new")
        weak = w.simplified in self.open_mistakes or bool(rec and (rec.times_missed or 0) >= 2 and rec.status != "mastered")
        return {"status": rec.status if rec else "new", "due": due, "weak": weak,
                "mastery": round(rec.mastery or 0, 1) if rec else 0.0}


def coverage(db: Session, user: models.User, item: dict, version: str, level: int, levels: dict) -> dict:
    words = [t["word"] for t in sent.segment(db, _text(item, version)) if t["word"] is not None]
    if not words:
        return {"ratio": 0.0, "known": 0, "familiar": 0, "learning": 0, "new": 0, "total": 0}
    uw = _UserWords(db, user, words)
    known = familiar = learning = new = 0
    for w in words:
        st = uw.state(w)["status"]
        if st in ("reviewing", "mastered"):
            known += 1
        elif st == "learning":
            learning += 1
        elif levels.get(w.hsk_level_id, 9) < level:
            familiar += 1   # a level the learner has already passed
        else:
            new += 1
    total = len(words)
    return {"ratio": round((known + familiar + 0.5 * learning) / total, 2), "known": known, "familiar": familiar,
            "learning": learning, "new": new, "total": total}


def recommend(db: Session, user: models.User, item: dict, prof: dict, levels: dict) -> tuple[str, dict]:
    covs = {v: coverage(db, user, item, v, prof["level"], levels) for v in VERSIONS}
    chosen = "beginner"
    for v in VERSIONS:  # easiest -> hardest
        if covs[v]["ratio"] >= prof["bar"]:
            chosen = v
    return chosen, covs


def _history(db: Session, user: models.User) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for s in db.query(models.PracticeSession).filter(
            models.PracticeSession.user_id == user.id, models.PracticeSession.source == "internet",
            models.PracticeSession.completed_at.isnot(None)):
        ctx = (s.questions or [{}])[0].get("ctx") or {}
        h = out.setdefault(ctx.get("slug"), {"rounds": 0, "best": 0.0, "versions": []})
        h["rounds"] += 1
        h["best"] = max(h["best"], s.score or 0.0)
        if ctx.get("version") and ctx["version"] not in h["versions"]:
            h["versions"].append(ctx["version"])
    return out


def feed(db: Session, user: models.User, locale: str) -> dict:
    prof = _reader_profile(db, user)
    levels = _levels(db)
    history = _history(db, user)
    items = []
    for item in ITEMS:
        version, covs = recommend(db, user, item, prof, levels)
        h = history.get(item["slug"]) or {"rounds": 0, "best": 0.0, "versions": []}
        items.append({
            "slug": item["slug"], "kind": item["kind"], "icon": item["icon"], "source": item["source"],
            "time": item["time"], "title": item["title"], "summary": item["summary"].get(locale) or item["summary"]["en"],
            "recommended": version, "coverage": covs[version], "original_coverage": covs["original"],
            "preview": item["versions"][version][0]["text"], **h,
        })
    return {"profile": prof, "items": items}


def _token_view(db: Session, user: models.User, text: str, level: int, levels: dict, locale: str, uw: _UserWords | None = None):
    tokens = sent.segment(db, text)
    words = [t["word"] for t in tokens if t["word"] is not None]
    uw = uw or _UserWords(db, user, words)
    m = ss.meanings(db, [w.id for w in words], locale)
    out = []
    for t in tokens:
        w = t["word"]
        if w is None:
            out.append({"text": t["text"], "kind": t["kind"]})
            continue
        lvl = levels.get(w.hsk_level_id)
        out.append({"text": t["text"], "kind": "word", "word_id": w.id, "pinyin": w.pinyin, "meaning": m.get(w.id, ""),
                    "level": lvl, "above": bool(lvl and lvl > level), **uw.state(w)})
    return out, words


def item_view(db: Session, user: models.User, slug: str, version: str | None, locale: str) -> dict:
    item = ITEM_BY_SLUG.get(slug)
    if item is None:
        raise InternetError(404, "Content not found")
    if version is not None and version not in VERSIONS:
        raise InternetError(422, "version must be beginner, intermediate or original")
    prof = _reader_profile(db, user)
    levels = _levels(db)
    recommended, covs = recommend(db, user, item, prof, levels)
    version = version or recommended
    all_words = [t["word"] for t in sent.segment(db, _text(item, version)) if t["word"] is not None]
    uw = _UserWords(db, user, all_words)
    blocks = []
    for b in item["versions"][version]:
        tokens, _ = _token_view(db, user, b["text"], prof["level"], levels, locale, uw)
        blocks.append({"who": b.get("who"), "text": b["text"], "tokens": tokens})

    # Glossary: weak and due words first, then new words within reach.
    seen, gloss = set(), []
    flat = [t for b in blocks for t in b["tokens"] if t.get("kind") == "word"]
    order = sorted(flat, key=lambda t: (not t["weak"], not t["due"], t["status"] != "new", t["above"], t["level"] or 9))
    for t in order:
        if t["word_id"] in seen or t["status"] == "mastered" and not t["weak"]:
            continue
        if t["status"] in ("reviewing",) and not (t["weak"] or t["due"]):
            continue
        if t["status"] == "new" and t["level"] and t["level"] < prof["level"]:
            continue  # below their level: expected to be readable
        seen.add(t["word_id"])
        gloss.append(t)
        if len(gloss) >= 10:
            break

    grammar, seen_g = [], set()
    for b in item["versions"][version]:
        for g in sent.match_grammar(db, b["text"]):
            if g.id in seen_g:
                continue
            seen_g.add(g.id)
            grammar.append((g, b["text"]))
    gtr = load_translations(db, "grammar_topic", [str(g.id) for g, _ in grammar], locale)
    grammar_out = [{"id": g.id, "title": tr(gtr, g.id, "title", g.title), "pattern": g.pattern,
                    "explanation": tr(gtr, g.id, "explanation", g.explanation), "level": levels.get(g.hsk_level_id),
                    "above": (levels.get(g.hsk_level_id) or 1) > prof["level"], "example": ex}
                   for g, ex in grammar][:5]

    h = _history(db, user).get(slug) or {"rounds": 0, "best": 0.0, "versions": []}
    return {
        "slug": slug, "kind": item["kind"], "icon": item["icon"], "source": item["source"], "time": item["time"],
        "title": item["title"], "summary": item["summary"].get(locale) or item["summary"]["en"],
        "version": version, "recommended": recommended, "coverage": covs,
        "profile": prof, "blocks": blocks, "glossary": gloss, "grammar": grammar_out,
        "notes": [{"term": n["term"], "py": n["py"], "text": n["tr"].get(locale) or n["tr"]["en"]} for n in item["notes"]],
        "questions": len(item["questions"]), **h,
    }


def word_help(db: Session, user: models.User, word_id: int, slug: str | None, locale: str,
              version: str | None = None) -> dict:
    w = db.get(models.VocabularyWord, word_id)
    if w is None:
        raise InternetError(404, "Word not found")
    levels = _levels(db)
    from app.services.gamification import user_rank

    level, _ = user_rank(db, user)
    rec = db.query(models.UserVocabulary).filter_by(user_id=user.id, word_id=w.id).first()
    trs = load_translations(db, "vocab_word", [str(w.id)], locale)
    meaning = tr(trs, w.id, "meanings", w.meanings) or ""
    if meaning.strip() == w.simplified:
        meaning = w.meanings or ""
    mistakes = db.query(models.LearningMistake).filter_by(user_id=user.id, reference=w.simplified).all()
    open_m = [m for m in mistakes if not m.mastered]
    now = datetime.utcnow()

    # Related words: real words sharing a character, the learner's own first.
    chars = [c for c in dict.fromkeys(w.simplified) if _CJK.match(c)]
    from sqlalchemy import or_

    rel = db.query(models.VocabularyWord).filter(
        models.VocabularyWord.id != w.id,
        or_(*[models.VocabularyWord.simplified.contains(c) for c in chars]) if chars else models.VocabularyWord.id < 0,
    ).limit(80).all()
    rel_recs = {r.word_id: r for r in db.query(models.UserVocabulary).filter(
        models.UserVocabulary.user_id == user.id, models.UserVocabulary.word_id.in_([r.id for r in rel] or [0]))}
    rel.sort(key=lambda r: (r.id not in rel_recs, levels.get(r.hsk_level_id, 9), len(r.simplified), r.id))
    rel = rel[:6]
    rm = ss.meanings(db, [r.id for r in rel], locale)

    hz = {h.character: h for h in db.query(models.Hanzi).filter(models.Hanzi.character.in_(chars or [""])).order_by(models.Hanzi.id)}
    htr = load_translations(db, "hanzi", [str(h.id) for h in hz.values()], locale)

    context = None
    item = ITEM_BY_SLUG.get(slug or "")
    if item:
        # The version the learner is reading first, then the others.
        order = [version] if version in VERSIONS else []
        for v in order + [v for v in ("original", "intermediate", "beginner") if v not in order]:
            b = next((b for b in item["versions"][v] if w.simplified in b["text"]), None)
            if b:
                context = {"text": b["text"], "version": v, "gloss": ss.gloss(db, b["text"], locale)}
                break

    skills = {s.skill.code: round(s.mastery, 1) for s in user.user_skills if s.skill}
    tracked = rec is not None and rec.status != "new"
    lvl = levels.get(w.hsk_level_id)
    return {
        "id": w.id, "text": w.simplified, "pinyin": w.pinyin, "meaning": meaning, "level": lvl,
        "above_level": bool(lvl and lvl > level), "example": w.example, "example_pinyin": w.example_pinyin,
        "state": {
            "status": rec.status if rec else "new", "mastery": round(rec.mastery or 0, 1) if rec else 0.0,
            "times_seen": rec.times_seen if rec else 0, "times_missed": rec.times_missed if rec else 0,
            "next_review_at": rec.next_review_at.isoformat() if rec and rec.next_review_at else None,
            "due": bool(rec and rec.next_review_at and rec.next_review_at <= now and rec.status != "new"),
            "open_mistakes": sum(m.occurrences for m in open_m),
        },
        # Only a word that isn't in the learner's schedule can be added --
        # one they're reviewing or have mastered is left as it is.
        "can_add": not tracked,
        "add_reason": "mastered" if rec and rec.status == "mastered" else ("in_review" if tracked else "new"),
        "related": [{"id": r.id, "text": r.simplified, "pinyin": r.pinyin, "meaning": rm.get(r.id, ""),
                     "level": levels.get(r.hsk_level_id), "status": rel_recs[r.id].status if r.id in rel_recs else "new"}
                    for r in rel],
        "characters": [{"char": c, "pinyin": hz[c].pinyin if c in hz else "",
                        "meaning": (tr(htr, hz[c].id, "meaning", hz[c].meaning) if c in hz else ""),
                        "has_dna": c in hz} for c in chars],
        "context": context,
        "dna": {"vocabulary": skills.get("vocabulary", 0.0), "reading": skills.get("reading", 0.0)},
    }


def track_word(db: Session, user: models.User, word_id: int) -> dict:
    """Put one word on the learner's review schedule (due now). Mastery is
    not touched -- it only rises from graded answers."""
    from app.services.activity import log_activity

    w = db.get(models.VocabularyWord, word_id)
    if w is None:
        raise InternetError(404, "Word not found")
    rec = db.query(models.UserVocabulary).filter_by(user_id=user.id, word_id=w.id).first()
    if rec is not None and rec.status != "new":
        raise InternetError(409, "This word is already in your review" if rec.status != "mastered"
                            else "You have already mastered this word")
    now = datetime.utcnow()
    if rec is None:
        rec = models.UserVocabulary(user_id=user.id, word_id=w.id, mastery=0.0, times_seen=0, times_missed=0)
        db.add(rec)
    rec.status = "learning"
    rec.next_review_at = now
    log_activity(db, user, "word_saved")
    db.commit()
    return {"id": w.id, "status": rec.status, "next_review_at": rec.next_review_at.isoformat()}


# --------------------------------------------------------------------------- graded round

def _pinyin(db: Session, text: str) -> str:
    toks = sent.segment(db, text)
    chars = {t["text"] for t in toks if t["kind"] == "char"}
    hz = sent.hanzi_rows(db, chars)
    parts = []
    for t in toks:
        if t["word"] is not None:
            parts.append(t["word"].pinyin)
        elif t["kind"] == "char" and t["text"] in hz:
            parts.append(hz[t["text"]].pinyin or "")
        elif t["kind"] == "other" and parts:
            parts[-1] += t["text"]
    return " ".join(p for p in parts if p)


def _focus_of(db: Session, text: str) -> int | None:
    words = [t["word"] for t in sent.segment(db, text) if t["word"] is not None and len(t["text"]) >= 2]
    return max(words, key=lambda w: len(w.simplified)).id if words else None


def build_questions(db: Session, user: models.User, slug: str, version: str | None, level: int, rng: random.Random,
                    translated: dict | None) -> list[dict]:
    from app.services import practice

    item = ITEM_BY_SLUG.get(slug or "")
    if item is None:
        raise InternetError(404, "Content not found")
    view = item_view(db, user, slug, version, "en")
    version = view["version"]
    show_py = version == "beginner" or level <= 2
    questions: list[dict] = []
    for i, cq in enumerate(item["questions"]):
        order = list(range(len(cq["options"])))
        rng.shuffle(order)
        opts = [cq["options"][k] for k in order]
        questions.append({
            "type": "net_comprehension", "item_type": "reading", "q": cq["q"],
            "q_py": _pinyin(db, cq["q"]) if show_py else None,
            "options": [{"zh": o, "py": _pinyin(db, o) if show_py else ""} for o in opts],
            "item_id": order.index(cq["answer"]), "option_ids": list(range(len(opts))),
            "focus_id": _focus_of(db, cq["options"][cq["answer"]]), "show_py": show_py,
        })
    # Listening: one line of the text, heard, picked among the others.
    lines = [b["text"] for b in item["versions"][version] if len(_CJK.findall(b["text"])) >= 6]
    if len(lines) >= 3:
        heard = rng.choice(lines)
        opts = [heard] + [x for x in lines if x != heard][:2]
        rng.shuffle(opts)
        questions.insert(1, {
            "type": "net_listen", "item_type": "reading", "speak": heard,
            "options": [{"zh": o, "py": ""} for o in opts], "item_id": opts.index(heard),
            "option_ids": list(range(len(opts))), "focus_id": _focus_of(db, heard), "show_py": False,
        })
    # The words worth stopping for (weak/due first, new within reach).
    rows = [db.get(models.VocabularyWord, g["word_id"]) for g in view["glossary"]]
    rows = [r for r in rows if r is not None and practice._usable("vocab", r)][:3]
    for k, r in enumerate(rows):
        q = practice._question(db, "vocab", r, k, rng, translated)
        if q:
            questions.append(q)
    questions[0]["ctx"] = {"kind": "internet", "slug": slug, "version": version, "icon": item["icon"],
                           "title": item["title"], "source": item["source"]}
    return questions


def render(db: Session, q: dict, answered: bool, locale: str) -> tuple[dict, list[dict]]:
    """Also renders Chinese Stories questions (services/stories.py): the same
    shapes, plus a story's slower audio and its translated question."""
    options = [{"id": i, "label": o["zh"], "pinyin": o["py"] or None} for i, o in enumerate(q["options"])]
    if q["type"] in ("net_listen", "story_listen"):
        return {"speak": q["speak"], "text": q["speak"] if answered else None, "rate": q.get("rate"),
                "fallback": _pinyin(db, q["speak"])}, options
    tr = (q.get("q_tr") or {}).get(locale) if locale != "zh" else None
    return {"text": q["q"], "pinyin": q.get("q_py"), "speak": q["q"], "translation": tr}, options


def card(db: Session, q: dict, locale: str) -> dict:
    o = q["options"][q["item_id"]]
    text = q["speak"] if q["type"] in ("net_listen", "story_listen") else o["zh"]
    return {"hanzi": text, "pinyin": _pinyin(db, text), "meaning": "", "gloss": ss.gloss(db, text, locale)}
