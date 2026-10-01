"""Server-graded practice and review.

A session is generated from real curriculum rows and stored (item id, the
option ids offered, question type); the client only ever sends back which
option id it picked, so correctness, mastery, mistakes, Learning DNA, XP and
lesson completion are all decided here from the stored question -- the
client cannot mark anything "correct" by itself.

Sources:
  vocab / hanzi / grammar  one HSK level's items, due-for-review first, then
                           items in progress, then new ones in curriculum order
  lesson                   the words and grammar points a lesson teaches
  review                   everything due by the spaced-repetition schedule
                           plus unresolved mistakes, across all three types
"""

from __future__ import annotations

import random
import re
from datetime import datetime

from sqlalchemy.orm import Session

from app import models
from app.services import companion_reaction as cr
from app.services.activity import log_activity
from app.services.dna import bump_skill
from app.services.gamification import (
    ensure_user_skills,
    progress_missions,
    progress_quests,
    record_mistake,
    reinforce_mistake,
    touch_streak,
)
from app.services.hsk_band import resolve_level_filter
from app.services.localization import load_translations, tr
from app.services.srs import apply_srs

SOURCES = ("vocab", "hanzi", "grammar", "lesson", "review")
VOCAB_TYPES = ("meaning_to_word", "word_to_meaning", "listen_to_word")
HANZI_TYPES = ("char_to_meaning", "char_to_pinyin")
PASS_SCORE = 0.7          # lesson counts as completed at >= 70% correct
FAST_ANSWER_MS = 4000     # correct within 4s feeds Reaction Speed
XP_PER_CORRECT = 2
XP_GOOD_ROUND_BONUS = 10  # score >= 80%

_CJK = re.compile(r"[㐀-鿿]")
# "工作 (gōngzuò) = to work" / "你好 (nǐ hǎo) = hello" -- a word followed by
# its pinyin in parentheses, the format both the hand-written and the
# generated lessons use to introduce vocabulary.
_LESSON_WORD = re.compile(r"([㐀-鿿]{1,6})\s*[（(]\s*[a-zA-ZÀ-ɏǍ-ǜ' ]+[)）]")
_TONE_MARKS = str.maketrans(
    "āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü", "aaaaeeeeiiiioooouuuuvvvvv"
)


class PracticeError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


# --------------------------------------------------------------------------- pools

_MODEL = {
    "vocab": (models.VocabularyWord, models.VocabularyWord.hsk_level_id),
    "hanzi": (models.Hanzi, models.Hanzi.hsk_level_id),
    "grammar": (models.GrammarTopic, models.GrammarTopic.hsk_level_id),
}
_USER_MODEL = {
    "vocab": (models.UserVocabulary, "word_id"),
    "hanzi": (models.UserHanzi, "hanzi_id"),
    "grammar": (models.UserGrammar, "topic_id"),
}


def _level_rows(db: Session, item_type: str, hsk_level: int) -> list:
    model, id_field = _MODEL[item_type]
    level_id, subset = resolve_level_filter(db, model, id_field, hsk_level)
    q = db.query(model).filter(id_field == (level_id or 0))
    if subset is not None:
        q = q.filter(model.id.in_(subset or [0]))
    return q.order_by(model.id).all()


def _records(db: Session, user: models.User, item_type: str, ids: list[int] | None = None) -> dict:
    rec_model, fk = _USER_MODEL[item_type]
    q = db.query(rec_model).filter(rec_model.user_id == user.id)
    if ids is not None:
        q = q.filter(getattr(rec_model, fk).in_(ids or [0]))
    return {getattr(r, fk): r for r in q}


def _grammar_example(topic: models.GrammarTopic) -> str | None:
    """First Chinese example sentence of a grammar point (not its title)."""
    for line in (topic.examples or "").splitlines():
        line = line.strip()
        if len(_CJK.findall(line)) >= 2 and line != topic.title and len(line) <= 80:
            return line
    return None


def _usable(item_type: str, row) -> bool:
    if item_type == "vocab":
        return bool(row.simplified and row.meanings and row.pinyin)
    if item_type == "hanzi":
        return bool(row.character and row.meaning and row.pinyin)
    return _grammar_example(row) is not None


def _prioritize(rows: list, recs: dict, size: int, now: datetime) -> list:
    """Due first, then in-progress, then new (curriculum order); mastered last."""
    due, learning, new, mastered = [], [], [], []
    for r in rows:
        rec = recs.get(r.id)
        if rec is None:
            new.append(r)
        elif rec.next_review_at and rec.next_review_at <= now and rec.status != "new":
            due.append(r)
        elif rec.status == "mastered":
            mastered.append(r)
        else:
            learning.append(r)
    due.sort(key=lambda r: recs[r.id].next_review_at)
    learning.sort(key=lambda r: recs[r.id].mastery or 0)
    return (due + learning + new + mastered)[:size]


# --------------------------------------------------------------------------- lesson links

def lesson_items(db: Session, lesson: models.Lesson) -> dict[str, list]:
    """The vocabulary and grammar a lesson actually teaches: words it
    introduces as "word (pinyin)" and the level's grammar points whose title
    appears in it. Same-level rows win over other levels for duplicates."""
    text = f"{lesson.summary or ''}\n{lesson.content or ''}"
    words: list[models.VocabularyWord] = []
    seen: set[str] = set()
    wanted = [w for w in _LESSON_WORD.findall(text) if not (w in seen or seen.add(w))]
    if wanted:
        candidates = db.query(models.VocabularyWord).filter(models.VocabularyWord.simplified.in_(wanted)).all()
        best: dict[str, models.VocabularyWord] = {}
        for c in sorted(candidates, key=lambda c: (c.hsk_level_id != lesson.hsk_level_id, c.id)):
            best.setdefault(c.simplified, c)
        words = [best[w] for w in wanted if w in best]
    grammar = []
    if lesson.hsk_level_id is not None:
        for g in db.query(models.GrammarTopic).filter_by(hsk_level_id=lesson.hsk_level_id).order_by(models.GrammarTopic.id):
            if len(g.title) >= 2 and g.title in text:
                grammar.append(g)
    return {"vocab": words, "grammar": grammar}


def lesson_round_items(db: Session, lesson: models.Lesson) -> list[tuple[str, object]]:
    """What a lesson's practice round is built from. Empty means the lesson
    is reading-only: it has no round, so it can never be passed -- the
    lesson path (services/lesson_path.py) uses this same rule so it never
    blocks a learner behind a lesson they could not complete."""
    items = lesson_items(db, lesson)
    vocab = [w for w in items["vocab"] if _usable("vocab", w)][:8]
    grammar = [g for g in items["grammar"] if _usable("grammar", g)][:4]
    return [("vocab", w) for w in vocab] + [("grammar", g) for g in grammar]


# --------------------------------------------------------------------------- building

def _pick_type(item_type: str, index: int) -> str:
    if item_type == "vocab":
        return VOCAB_TYPES[index % len(VOCAB_TYPES)]
    if item_type == "hanzi":
        return HANZI_TYPES[index % len(HANZI_TYPES)]
    return "example_to_point"


def _option_label_key(qtype: str, row) -> str:
    """The text an option shows -- options must be pairwise distinct on it,
    or two "different" answers would look identical and grading be unfair."""
    if qtype in ("meaning_to_word", "listen_to_word"):
        return row.simplified
    if qtype == "word_to_meaning":
        return (row.meanings or "").strip().lower()
    if qtype == "char_to_meaning":
        return (row.meaning or "").strip().lower()
    if qtype == "char_to_pinyin":
        return (row.pinyin or "").strip().lower()
    return row.title


def _distractors(db: Session, item_type: str, qtype: str, target, rng: random.Random, k: int = 3) -> list[int]:
    model, id_field = _MODEL[item_type]
    pool = db.query(model).filter(id_field == target.hsk_level_id, model.id != target.id).all()
    pool = [r for r in pool if _usable(item_type, r)]
    if qtype == "char_to_pinyin":
        # Same syllable, different tone first: that is what the question tests.
        base = (target.pinyin or "").translate(_TONE_MARKS)
        same = [r for r in pool if (r.pinyin or "").translate(_TONE_MARKS) == base]
        rng.shuffle(same)
        rest = [r for r in pool if r not in same]
        rng.shuffle(rest)
        pool = same + rest
    else:
        rng.shuffle(pool)
    taken = {_option_label_key(qtype, target)}
    out = []
    for r in pool:
        key = _option_label_key(qtype, r)
        if not key or key in taken:
            continue
        taken.add(key)
        out.append(r.id)
        if len(out) == k:
            break
    return out


def _question(db: Session, item_type: str, row, index: int, rng: random.Random) -> dict | None:
    qtype = _pick_type(item_type, index)
    distractors = _distractors(db, item_type, qtype, row, rng)
    if len(distractors) < 2:
        return None
    options = distractors + [row.id]
    rng.shuffle(options)
    q = {"type": qtype, "item_type": item_type, "item_id": row.id, "option_ids": options}
    if item_type == "grammar":
        q["prompt"] = _grammar_example(row)
    return q


def build_session(
    db: Session, user: models.User, source: str, *, hsk_level: int | None = None,
    lesson_id: int | None = None, size: int = 10,
) -> models.PracticeSession | None:
    if source not in SOURCES:
        raise PracticeError(422, f"source must be one of {', '.join(SOURCES)}")
    size = max(4, min(20, size))
    now = datetime.utcnow()
    rng = random.Random()
    picked: list[tuple[str, object]] = []
    lesson = None

    if source in ("vocab", "hanzi", "grammar"):
        if hsk_level is None or not 1 <= hsk_level <= 9:
            raise PracticeError(422, "hsk_level (1-9) is required for this source")
        rows = [r for r in _level_rows(db, source, hsk_level) if _usable(source, r)]
        recs = _records(db, user, source, [r.id for r in rows])
        picked = [(source, r) for r in _prioritize(rows, recs, size, now)]
    elif source == "lesson":
        lesson = db.get(models.Lesson, lesson_id) if lesson_id else None
        if lesson is None:
            raise PracticeError(404, "Lesson not found")
        picked = lesson_round_items(db, lesson)
        if not picked:
            raise PracticeError(422, "This lesson has no linked vocabulary or grammar to practice yet")
    else:  # review
        picked = _review_items(db, user, size, now)
        if not picked:
            return None

    questions = []
    for i, (item_type, row) in enumerate(picked):
        q = _question(db, item_type, row, i, rng)
        if q:
            questions.append(q)
    if not questions:
        raise PracticeError(422, "Not enough content at this level to build a practice round")
    session = models.PracticeSession(
        user_id=user.id, source=source, hsk_level=hsk_level,
        lesson_id=lesson.id if lesson else None,
        questions=questions, answers=[None] * len(questions),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _review_items(db: Session, user: models.User, size: int, now: datetime) -> list[tuple[str, object]]:
    """Due SRS items of every type plus unresolved mistakes, most urgent first."""
    scored: dict[tuple[str, int], tuple[float, object]] = {}

    def add(item_type, row, urgency):
        if row is None or not _usable(item_type, row):
            return
        key = (item_type, row.id)
        if key not in scored or scored[key][0] < urgency:
            scored[key] = (urgency, row)

    for item_type, (rec_model, fk) in _USER_MODEL.items():
        rel = {"vocab": "word", "hanzi": "hanzi", "grammar": "topic"}[item_type]
        due = (
            db.query(rec_model)
            .filter(rec_model.user_id == user.id, rec_model.next_review_at.isnot(None), rec_model.next_review_at <= now)
            .all()
        )
        for rec in due:
            overdue_h = (now - rec.next_review_at).total_seconds() / 3600
            add(item_type, getattr(rec, rel), 1.0 + min(overdue_h, 72) / 72 + (100 - (rec.mastery or 0)) / 100)

    mistakes = (
        db.query(models.LearningMistake)
        .filter(models.LearningMistake.user_id == user.id, models.LearningMistake.mastered.is_(False))
        .order_by(models.LearningMistake.priority.desc())
        .limit(40)
        .all()
    )
    for m in mistakes:
        urgency = 2.0 + (m.priority or 1) / 5
        if m.mistake_type in ("word", "tone", "pinyin"):
            w = db.query(models.VocabularyWord).filter_by(simplified=m.reference).order_by(models.VocabularyWord.id).first()
            add("vocab", w, urgency)
        elif m.mistake_type in ("hanzi", "character", "hanzi_write"):
            h = db.query(models.Hanzi).filter_by(character=m.reference).order_by(models.Hanzi.id).first()
            add("hanzi", h, urgency)
        elif m.mistake_type == "grammar":
            g = db.query(models.GrammarTopic).filter_by(title=m.reference).order_by(models.GrammarTopic.id).first()
            add("grammar", g, urgency)

    ranked = sorted(scored.items(), key=lambda kv: -kv[1][0])[:size]
    return [(item_type, row) for (item_type, _id), (_u, row) in ranked]


def review_counts(db: Session, user: models.User) -> dict[str, int]:
    now = datetime.utcnow()
    out = {}
    for item_type, (rec_model, _fk) in _USER_MODEL.items():
        out[item_type] = (
            db.query(rec_model)
            .filter(rec_model.user_id == user.id, rec_model.next_review_at.isnot(None), rec_model.next_review_at <= now)
            .count()
        )
    out["mistakes"] = (
        db.query(models.LearningMistake)
        .filter(models.LearningMistake.user_id == user.id, models.LearningMistake.mastered.is_(False))
        .count()
    )
    out["total"] = out["vocab"] + out["hanzi"] + out["grammar"]
    return out


# --------------------------------------------------------------------------- rendering

def _row(db: Session, item_type: str, item_id: int):
    return db.get(_MODEL[item_type][0], item_id)


def _short(text: str | None, limit: int = 70) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip(" ,;") + "…"


def _item_card(item_type: str, row, labels: dict) -> dict:
    """What the learner should see as the correct answer after grading."""
    if item_type == "vocab":
        return {"hanzi": row.simplified, "pinyin": row.pinyin, "meaning": labels["vocab"].get(row.id, row.meanings)}
    if item_type == "hanzi":
        return {"hanzi": row.character, "pinyin": row.pinyin, "meaning": labels["hanzi"].get(row.id, row.meaning)}
    return {"hanzi": row.pattern or "", "pinyin": "", "meaning": labels["grammar"].get(row.id, row.title)}


def _labels(db: Session, questions: list[dict], locale: str) -> dict[str, dict[int, str]]:
    ids: dict[str, set[int]] = {"vocab": set(), "hanzi": set(), "grammar": set()}
    for q in questions:
        ids[q["item_type"]].update(q["option_ids"])
    out: dict[str, dict[int, str]] = {}
    for item_type, content_type, field in (
        ("vocab", "vocab_word", "meanings"), ("hanzi", "hanzi", "meaning"), ("grammar", "grammar_topic", "title"),
    ):
        rows = db.query(_MODEL[item_type][0]).filter(_MODEL[item_type][0].id.in_(ids[item_type] or {0})).all()
        trs = load_translations(db, content_type, [str(r.id) for r in rows], locale)
        out[item_type] = {r.id: tr(trs, r.id, field, getattr(r, field)) for r in rows}
    return out


def render_session(db: Session, session: models.PracticeSession, locale: str) -> dict:
    labels = _labels(db, session.questions, locale)
    rendered = []
    for i, q in enumerate(session.questions):
        item_type, qtype = q["item_type"], q["type"]
        target = _row(db, item_type, q["item_id"])
        options = []
        for oid in q["option_ids"]:
            r = _row(db, item_type, oid)
            if r is None:
                continue
            if qtype in ("meaning_to_word", "listen_to_word"):
                label = r.simplified
            elif qtype == "word_to_meaning":
                label = _short(labels["vocab"].get(r.id))
            elif qtype == "char_to_meaning":
                label = _short(labels["hanzi"].get(r.id))
            elif qtype == "char_to_pinyin":
                label = r.pinyin
            else:
                label = _short(labels["grammar"].get(r.id), 90)
            options.append({"id": oid, "label": label})
        prompt: dict = {}
        if target is not None:
            if qtype == "meaning_to_word":
                prompt = {"text": _short(labels["vocab"].get(target.id), 90)}
            elif qtype == "word_to_meaning":
                prompt = {"text": target.simplified, "pinyin": target.pinyin, "speak": target.simplified}
            elif qtype == "listen_to_word":
                prompt = {"speak": target.simplified}
            elif qtype in ("char_to_meaning", "char_to_pinyin"):
                prompt = {"text": target.character, "speak": target.character if qtype == "char_to_meaning" else None}
            else:
                prompt = {"text": q.get("prompt") or "", "speak": q.get("prompt")}
        answer = session.answers[i]
        item = {"index": i, "type": qtype, "item_type": item_type, "prompt": prompt, "options": options, "answer": None}
        if answer is not None and target is not None:
            item["answer"] = {**answer, "correct_id": q["item_id"], "card": _item_card(item_type, target, labels)}
        rendered.append(item)
    return {
        "id": session.id,
        "source": session.source,
        "hsk_level": session.hsk_level,
        "lesson_id": session.lesson_id,
        "questions": rendered,
        "completed": session.completed_at is not None,
        "score": session.score,
    }


# --------------------------------------------------------------------------- grading

def _focus(item_type: str, row, labels: dict) -> dict:
    """The real item a companion reaction talks about: its answer card plus,
    for words, the curriculum's own example sentence (never invented)."""
    card = {"item_type": item_type, **_item_card(item_type, row, labels)}
    if item_type == "vocab" and row.example:
        card["example"] = row.example
        card["example_pinyin"] = row.example_pinyin
    elif item_type == "grammar":
        card["example"] = _grammar_example(row)
    return card


def _record(db: Session, user: models.User, session: models.PracticeSession, q: dict, row, correct: bool, response_ms: int) -> dict:
    """Applies one graded answer to mastery, DNA, mistakes, quests and XP.
    Returns what changed (status before/after, the primary DNA skill's value
    before/after) so the companion can react to the real result."""
    item_type, qtype = q["item_type"], q["type"]
    rec_model, fk = _USER_MODEL[item_type]
    rec = db.query(rec_model).filter(rec_model.user_id == user.id, getattr(rec_model, fk) == row.id).first()
    status_before = rec.status if rec is not None else None
    if rec is None:
        rec = rec_model(user_id=user.id, mastery=0.0, status="new", times_missed=0, **{fk: row.id})
        db.add(rec)
    apply_srs(rec, correct, user, counter="times_practiced" if item_type == "grammar" else "times_seen")

    ensure_user_skills(db, user)
    primary = cr.PRIMARY_SKILL.get(qtype)
    skill_before = cr.skill_value(user, primary) if primary else None
    plus, minus = 2.0, -0.3
    if item_type == "vocab":
        bump_skill(user, "vocabulary", plus if correct else minus)
        if qtype == "listen_to_word":
            bump_skill(user, "listening", 1.5 if correct else minus)
            bump_skill(user, "tones", 0.5 if correct else 0.0)
        elif qtype == "word_to_meaning":
            bump_skill(user, "reading", 0.5 if correct else 0.0)
        ref_type, ref = "word", row.simplified
        quest = "vocab"
    elif item_type == "hanzi":
        bump_skill(user, "reading", plus if correct else minus)
        if qtype == "char_to_pinyin":
            bump_skill(user, "tones", 1.5 if correct else minus)
        ref_type, ref = "hanzi", row.character
        quest = "hanzi"
    else:
        bump_skill(user, "grammar", plus if correct else minus)
        bump_skill(user, "reading", 0.5 if correct else 0.0)
        ref_type, ref = "grammar", row.title
        quest = "grammar"
    if session.source == "review":
        # Recalling an item the schedule brought back is memory, literally.
        bump_skill(user, "memory", 1.5 if correct else minus)
    if correct and 0 < response_ms <= FAST_ANSWER_MS:
        bump_skill(user, "reaction_speed", 0.5)

    if correct:
        reinforce_mistake(db, user, ref_type, ref)
        progress_quests(db, user, quest, amount=1)
        progress_missions(db, user, quest)
        user.total_xp += XP_PER_CORRECT
    else:
        card = _item_card(item_type, row, {"vocab": {}, "hanzi": {}, "grammar": {}})
        record_mistake(
            db, user, ref_type, ref,
            question_text=q.get("prompt") or card["meaning"],
            correct_answer=" ".join(x for x in (card["hanzi"], card["pinyin"]) if x) or card["meaning"],
        )
    touch_streak(user)
    log_activity(db, user, "practice_answer")
    return {
        "mastery": rec.mastery,
        "status_before": status_before,
        "status_after": rec.status,
        "times_missed": rec.times_missed or 0,
        "skill": cr.skill_crossing(primary, skill_before, cr.skill_value(user, primary)) if primary else None,
    }


def answer_question(
    db: Session, user: models.User, session: models.PracticeSession, index: int, choice_id: int,
    response_ms: int, locale: str,
) -> dict:
    if session.completed_at is not None:
        raise PracticeError(409, "This practice round is already finished")
    if not 0 <= index < len(session.questions):
        raise PracticeError(422, "No such question")
    if session.answers[index] is not None:
        raise PracticeError(409, "This question was already answered")
    q = session.questions[index]
    if choice_id not in q["option_ids"]:
        raise PracticeError(422, "That option was not offered for this question")
    row = _row(db, q["item_type"], q["item_id"])
    if row is None:
        raise PracticeError(410, "This item no longer exists")

    correct = choice_id == q["item_id"]
    change = _record(db, user, session, q, row, correct, response_ms)
    answers = list(session.answers)  # reassign so the JSON column is marked dirty
    answers[index] = {"choice_id": choice_id, "correct": correct, "response_ms": response_ms}
    session.answers = answers
    db.commit()
    labels = _labels(db, [q], locale)
    return {
        "correct": correct,
        "correct_id": q["item_id"],
        "card": _item_card(q["item_type"], row, labels),
        "mastery": round(change["mastery"], 1),
        "xp_gained": XP_PER_CORRECT if correct else 0,
        "reaction": cr.answer_reaction(
            user, answers,
            item_type=q["item_type"], focus=_focus(q["item_type"], row, labels),
            status_before=change["status_before"], status_after=change["status_after"],
            times_missed=change["times_missed"], skill=change["skill"],
        ),
    }


def complete_session(db: Session, user: models.User, session: models.PracticeSession, locale: str) -> dict:
    answers = session.answers
    total = len(session.questions)
    correct = sum(1 for a in answers if a and a["correct"])
    answered = sum(1 for a in answers if a is not None)
    score = correct / total if total else 0.0
    first_completion = session.completed_at is None
    xp = 0
    lesson_status = None
    newly_completed = False
    next_lesson_id = None
    if first_completion:
        if answered == 0:
            raise PracticeError(422, "Answer at least one question before finishing")
        session.completed_at = datetime.utcnow()
        session.score = round(score * 100, 1)
        if score >= 0.8:
            user.total_xp += XP_GOOD_ROUND_BONUS
            xp = XP_GOOD_ROUND_BONUS
        if session.lesson_id:
            # Imported here: lesson_path builds on this module.
            from app.services import lesson_path

            prev = db.query(models.Progress).filter_by(user_id=user.id, lesson_id=session.lesson_id).first()
            was_completed = prev is not None and prev.status == "completed"
            state = lesson_path.path_state(db, user)
            if state.is_open(session.lesson_id):
                lesson_status = _record_lesson(db, user, session.lesson_id, score)
                newly_completed = lesson_status == "completed" and not was_completed
                if newly_completed:
                    # Passing the current lesson opens the next step; passing
                    # an older one (left open by pre-path progress) does not
                    # move the learner, who continues at their current lesson.
                    is_current = state.current is not None and state.current.lesson.id == session.lesson_id
                    nxt = state.after(session.lesson_id) if is_current else state.current
                    next_lesson_id = nxt.lesson.id if nxt else None
            else:
                # A round started on a lesson that is locked by now (e.g.
                # built before the lesson path existed) still grades its
                # words, but cannot complete a lesson out of order.
                lesson_status = prev.status if prev else None
        db.commit()
    elif session.lesson_id:
        p = db.query(models.Progress).filter_by(user_id=user.id, lesson_id=session.lesson_id).first()
        lesson_status = p.status if p else None

    labels = _labels(db, session.questions, locale)
    missed = []
    focus = None
    for q, a in zip(session.questions, answers):
        if a is not None and not a["correct"]:
            row = _row(db, q["item_type"], q["item_id"])
            if row is not None:
                missed.append({"item_type": q["item_type"], **_item_card(q["item_type"], row, labels)})
                # The first missed item is the one the companion suggests
                # revisiting -- it is already queued for Review.
                focus = focus or _focus(q["item_type"], row, labels)
    return {
        "correct": correct,
        "answered": answered,
        "total": total,
        "score": round(score * 100, 1),
        "xp_bonus": xp,
        "lesson_status": lesson_status,
        # Set only when this round just completed its lesson: the lesson the
        # learner should study next on the path (None at the end of it).
        "next_lesson_id": next_lesson_id,
        "passed": score >= PASS_SCORE,
        "missed": missed,
        "reaction": cr.session_reaction(
            user, answers, total, source=session.source,
            # Celebrate the completion only when THIS round completed it --
            # re-practicing an already completed lesson is judged by score.
            lesson_completed=newly_completed,
            focus=focus, skill=cr.trained_skill(user, session.questions, answers),
        ),
    }


def start_reaction(db: Session, user: models.User, session: models.PracticeSession, locale: str) -> dict:
    """The companion greeting a freshly built round. A lesson round previews
    the lesson's own real words (the ones the round will ask about)."""
    words = []
    if session.lesson_id:
        lesson = db.get(models.Lesson, session.lesson_id)
        vocab = [w for w in lesson_items(db, lesson)["vocab"] if _usable("vocab", w)][:4] if lesson else []
        trs = load_translations(db, "vocab_word", [str(w.id) for w in vocab], locale)
        words = [
            {"hanzi": w.simplified, "pinyin": w.pinyin, "meaning": _short(tr(trs, w.id, "meanings", w.meanings), 40)}
            for w in vocab
        ]
    due = len(session.questions) if session.source == "review" else 0
    return cr.start_reaction(user, session.source, words=words, due=due)


def _record_lesson(db: Session, user: models.User, lesson_id: int, score: float) -> str:
    p = db.query(models.Progress).filter_by(user_id=user.id, lesson_id=lesson_id).first()
    if p is None:
        p = models.Progress(user_id=user.id, lesson_id=lesson_id, status="in_progress", score=0)
        db.add(p)
    pct = int(round(score * 100))
    p.score = max(p.score or 0, pct)
    if score >= PASS_SCORE and p.status != "completed":
        p.status = "completed"
        p.completed_at = datetime.utcnow()
        log_activity(db, user, "lesson_complete")
        progress_quests(db, user, "lesson", amount=1)
    elif p.status != "completed":
        p.status = "in_progress"
    return p.status
