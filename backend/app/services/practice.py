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
  scene                    a Real Chinese dialogue at the learner's tier
                           (services/real_life.py) plus its new words/grammar
  sentence                 one Chinese sentence turned into a lesson
                           (services/sentence.py)
  detective                a generated Chinese mystery (services/detective.py)
  sound                    an immersive listening place (services/sound_world.py)
  internet                 a Chinese Internet item at the learner's version
                           (services/internet.py)

Scene and sentence rounds add question types whose options are lines of
text rather than curriculum rows (item_type "line" / "sentence"): the
stored question keeps the lines and the index of the right one, and the
browser still only sends back an option id. Their answers count through
the exchange's / sentence's real focus word (apply_srs on its
UserVocabulary row), so they reach mastery and review like any other.
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

SOURCES = ("vocab", "hanzi", "grammar", "lesson", "review", "scene", "sentence", "detective", "sound", "internet")
VIRTUAL = ("line", "sentence", "case", "sound", "reading")  # item types whose options are text, not rows
SPEAK_LIMIT = 3  # spoken attempts per question (each one is a VoiceAttempt)
VOCAB_TYPES = ("meaning_to_word", "word_to_meaning", "listen_to_word")
HANZI_TYPES = ("char_to_meaning", "char_to_pinyin")
PASS_SCORE = 0.7          # lesson counts as completed at >= 70% correct
FAST_ANSWER_MS = 4000     # correct within 4s feeds Reaction Speed
# The browser's response_ms (question shown -> answered) is only a claim. The
# server bounds it by the time it actually saw pass since the previous answer
# (or the round's start), less this allowance for reading the previous
# answer's feedback and pressing Next. Without it any request could send
# response_ms=1 and earn the Reaction Speed bonus on every correct answer.
FEEDBACK_ALLOWANCE_MS = 8000
XP_PER_CORRECT = 2
XP_GOOD_ROUND_BONUS = 10  # score >= 80%

_CJK = re.compile(r"[㐀-鿿]")
# "工作 (gōngzuò) = to work" / "你好 (nǐ hǎo) = hello" -- a word followed by
# its pinyin in parentheses, the format both the hand-written and the
# generated lessons use to introduce vocabulary.
_LESSON_WORD = re.compile(r"([㐀-鿿]{1,6})\s*[（(]\s*[a-zA-ZÀ-ɏǍ-ǜ' ]+[)）]")
# The hand-written HSK 1-2 intro lessons also introduce words in two looser
# shapes the pattern above never matched, which left "Greetings", "Introduce
# yourself", "Numbers 1-10" and "Food words" with no practice at all:
#   "我叫…… (wǒ jiào ...)" / "很高兴认识你。 (hěn gāoxìng ...)" -- a phrase,
#       then an ellipsis or sentence mark, then its pinyin in parentheses;
#   "米饭 mǐfàn = rice" / "一 yī, 二 èr" -- pinyin with no parentheses.
# The second shape requires a tone-marked vowel, so plain Latin text after
# Chinese ("X是X", "HSK 3") is never read as pinyin.
_LESSON_PHRASE = re.compile(r"([㐀-鿿]{1,8})(?:……|…|\.\.\.)?[。？！，]?\s*[（(]\s*[a-zA-ZÀ-ɏǍ-ǜ' .…]+[)）]")
_LESSON_BARE = re.compile(
    r"([㐀-鿿]{1,6})[ \t]+((?:[a-zA-ZÀ-ɏǍ-ǜ']+[ \t]?){1,4}?)(?=[ \t]*(?:=|,|，|\.|。|\n|$))"
)
_TONED = re.compile(r"[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]")
# The generated grammar lessons end with a machine-readable word list:
#   "New vocabulary:\n客人 (kè'rén) = guest\n..."
# lesson_items reads the lesson's words from it, so it stays in the stored
# content. Learners never need to see it: the lesson page shows the same
# words as structured, localized cards (/lessons/{id}/items), and the list
# itself is English-only.
_VOCAB_LIST = re.compile(r"\n[ \t]*New vocabulary:[ \t]*\n.*\Z", re.S)


def lesson_body(content: str | None) -> str | None:
    """The lesson text a learner reads: the stored content without its
    trailing "New vocabulary:" word list."""
    if not content:
        return content
    return _VOCAB_LIST.sub("", content).rstrip()
_SEGMENT_MAX = 4  # longest word tried when splitting a phrase into known words
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


# Lines of the official syllabus that are not examples: sub-headings
# ("（1）是非问句", "①疑问代词+都") and notes ("※ 序数词（见【二72】...）").
_SYLLABUS_NOTE = re.compile(r"^(?:[（(]\d+[)）]|[①-⑳]|※)|见【")


def _grammar_example(topic: models.GrammarTopic) -> str | None:
    """First Chinese example sentence of a grammar point (not its title, a
    sub-heading or a cross-reference note -- a question built on those would
    show a label instead of Chinese to read)."""
    for line in (topic.examples or "").splitlines():
        line = line.strip()
        if (len(_CJK.findall(line)) >= 2 and line != topic.title and len(line) <= 80
                and not _SYLLABUS_NOTE.search(line)):
            return line
    return None


# A gloss that only points elsewhere ("see 干嘛", "variant of 淳朴", "abbr.
# for 体格检查") carries no meaning to test; 9 words keep one because their
# source entry has nothing else (see alembic c8e4a1f6b2d9).
_REFERENCE_GLOSS = re.compile(r"^(?:see|variant of|old variant of|abbr\. for)\s+\S+\s*$", re.I)


def _usable(item_type: str, row) -> bool:
    if item_type == "vocab":
        return bool(row.simplified and row.meanings and row.pinyin) and not _REFERENCE_GLOSS.match(row.meanings)
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

def _lesson_phrases(text: str) -> list[str]:
    """Every Chinese phrase the lesson introduces with its pinyin, in the
    order it appears, each once."""
    found = [(m.start(), m.group(1)) for m in _LESSON_PHRASE.finditer(text)]
    found += [(m.start(), m.group(1)) for m in _LESSON_BARE.finditer(text) if _TONED.search(m.group(2))]
    seen: set[str] = set()
    return [p for _pos, p in sorted(found) if not (p in seen or seen.add(p))]


def _segment(phrase: str, known: set[str]) -> list[str] | None:
    """Splits a phrase into known words, longest match first -- or None if
    any part of it is not a known word (then nothing is taken from it)."""
    out, i = [], 0
    while i < len(phrase):
        for size in range(min(_SEGMENT_MAX, len(phrase) - i), 0, -1):
            if phrase[i:i + size] in known:
                out.append(phrase[i:i + size])
                i += size
                break
        else:
            return None
    return out


def lesson_items(db: Session, lesson: models.Lesson) -> dict[str, list]:
    """The vocabulary and grammar a lesson actually teaches: words it
    introduces with their pinyin and the level's grammar points it covers.
    Same-level rows win over other levels for duplicates.

    A phrase that is not itself a vocabulary row ("你好", "早上好", "十一",
    "我叫") counts through its words ("你" + "好") -- but only when every
    part is a real word of the lesson's own HSK level, so an advanced
    lesson's idiom never drags in beginner words. Nothing is invented: a
    phrase that cannot be fully split into real rows is left out."""
    text = f"{lesson.summary or ''}\n{lesson.content or ''}"
    phrases = _lesson_phrases(text)
    words: list[models.VocabularyWord] = []
    if phrases:
        candidates = db.query(models.VocabularyWord).filter(models.VocabularyWord.simplified.in_(phrases)).all()
        best: dict[str, models.VocabularyWord] = {}
        for c in sorted(candidates, key=lambda c: (c.hsk_level_id != lesson.hsk_level_id, c.id)):
            best.setdefault(c.simplified, c)
        unmatched = [p for p in phrases if p not in best and len(p) > 1]
        parts: dict[str, models.VocabularyWord] = {}
        if unmatched and lesson.hsk_level_id is not None:
            pieces = {p[i:i + n] for p in unmatched for n in range(1, _SEGMENT_MAX + 1) for i in range(len(p) - n + 1)}
            parts = {
                w.simplified: w
                for w in db.query(models.VocabularyWord).filter(
                    models.VocabularyWord.hsk_level_id == lesson.hsk_level_id,
                    models.VocabularyWord.simplified.in_(pieces),
                )
            }
        taken: set[str] = set()
        for p in phrases:
            for w in [best[p]] if p in best else [parts[s] for s in (_segment(p, set(parts)) or [])]:
                if w.simplified not in taken:
                    taken.add(w.simplified)
                    words.append(w)
    grammar = []
    if lesson.hsk_level_id is not None:
        # The hand-written intro lessons name the point they teach in their
        # one-line summary by its head ("Mark the past with 了" teaches
        # "了 — completed action"); the generated lessons quote full titles.
        summary = (lesson.summary or "") if lesson.lesson_type == "lesson" else ""
        for g in db.query(models.GrammarTopic).filter_by(hsk_level_id=lesson.hsk_level_id).order_by(models.GrammarTopic.id):
            head = g.title.split(" — ")[0] if " — " in g.title else None
            if (len(g.title) >= 2 and g.title in text) or (head and head in summary):
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
    if qtype == "meaning_to_word":
        return row.simplified
    if qtype in ("word_to_meaning", "listen_to_word"):
        return (row.meanings or "").strip().lower()
    if qtype == "char_to_meaning":
        return (row.meaning or "").strip().lower()
    if qtype == "char_to_pinyin":
        return (row.pinyin or "").strip().lower()
    return row.title


# Questions whose options are meanings, and where those meanings live.
_MEANING_OPTIONS = {"word_to_meaning": "vocab_word", "listen_to_word": "vocab_word", "char_to_meaning": "hanzi"}


def _translated_ids(db: Session, content_type: str, locale: str) -> set[int]:
    field = "meanings" if content_type == "vocab_word" else "meaning"
    return {
        int(k) for (k,) in db.query(models.ContentTranslation.content_key).filter_by(
            content_type=content_type, field=field, locale=locale)
    }


def _distractors(db: Session, item_type: str, qtype: str, target, rng: random.Random, k: int = 3,
                 prefer: set[int] | None = None) -> list[int]:
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
    if prefer:
        # Options in the learner's language first, so all four can be shown
        # in it (one language per question -- see _option_labels).
        pool = [r for r in pool if r.id in prefer] + [r for r in pool if r.id not in prefer]
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


def _question(db: Session, item_type: str, row, index: int, rng: random.Random,
              translated: dict[str, set[int]] | None = None) -> dict | None:
    qtype = _pick_type(item_type, index)
    content_type = _MEANING_OPTIONS.get(qtype)
    prefer = (translated or {}).get(content_type) if content_type else None
    # Only worth it when the answer itself is translated.
    if prefer is not None and row.id not in prefer:
        prefer = None
    distractors = _distractors(db, item_type, qtype, row, rng, prefer=prefer)
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
    lesson_id: int | None = None, size: int = 10, locale: str = "en",
    scene: str | None = None, sentence: str | None = None,
    case: str | None = None, env: str | None = None, stage: int | None = None,
    item: str | None = None, version: str | None = None,
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
    elif source == "review":
        picked = _review_items(db, user, size, now)
        if not picked:
            return None

    # ru / tg meanings that really exist (zh "meanings" are the words
    # themselves, never shown as options -- see _labels).
    translated = (
        {ct: _translated_ids(db, ct, locale) for ct in ("vocab_word", "hanzi")}
        if locale in ("ru", "tg") else None
    )
    questions = []
    if source in ("scene", "sentence", "detective", "sound", "internet"):
        # The learner's real level decides the tier (imported here: these
        # modules build on this one).
        from app.services import detective, internet, real_life, sound_world
        from app.services import sentence as sentence_svc
        from app.services.gamification import user_rank

        hsk_level, _ = user_rank(db, user)
        try:
            if source == "scene":
                questions = real_life.build_questions(db, user, scene or "", hsk_level, rng, translated)
            elif source == "sentence":
                questions = sentence_svc.build_questions(db, user, sentence or "", hsk_level, rng, translated)
            elif source == "detective":
                questions = detective.build_questions(db, user, case or "", hsk_level, rng, translated)
            elif source == "internet":
                questions = internet.build_questions(db, user, item or "", version, hsk_level, rng, translated)
            else:
                if stage is None:
                    stage = sound_world.stage_status(db, user)["recommended"]
                questions = sound_world.build_questions(db, user, env or "", stage, hsk_level, rng, translated)
        except (real_life.SceneError, sentence_svc.SentenceError, detective.CaseError, sound_world.SoundError,
                internet.InternetError) as exc:
            raise PracticeError(exc.status, exc.detail) from exc
    for i, (item_type, row) in enumerate(picked):
        q = _question(db, item_type, row, i, rng, translated)
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
        if q["item_type"] in ids:
            ids[q["item_type"]].update(q["option_ids"])
    out: dict[str, dict[int, str]] = {}
    # Ids whose label really is in the learner's language (not a fallback).
    translated: dict[str, set[int]] = {}
    for item_type, content_type, field in (
        ("vocab", "vocab_word", "meanings"), ("hanzi", "hanzi", "meaning"), ("grammar", "grammar_topic", "title"),
    ):
        rows = db.query(_MODEL[item_type][0]).filter(_MODEL[item_type][0].id.in_(ids[item_type] or {0})).all()
        trs = load_translations(db, content_type, [str(r.id) for r in rows], locale)
        out[item_type] = {}
        translated[item_type] = set()
        for r in rows:
            label = tr(trs, r.id, field, getattr(r, field))
            # The zh "meaning" of a word is the word itself (a mirror, see
            # scripts/seed_vocab_zh_mirror.py). As a quiz label it gives the
            # answer away -- "which word means 喝?" with 喝 among the options --
            # so a question uses the real gloss instead.
            own = getattr(r, "simplified", None) or getattr(r, "character", None)
            if item_type != "grammar" and own and (label or "").strip() == own:
                label = getattr(r, field)
            if label != getattr(r, field):
                translated[item_type].add(r.id)
            out[item_type][r.id] = label
    out["translated"] = translated
    return out


def _option_labels(labels: dict, item_type: str, option_ids: list[int], rows: dict[int, object]) -> dict[int, str]:
    """One language for all options of a question. If any option has no
    translation in the learner's language, every option uses the source
    text: a lone Russian option among English ones would give the answer
    away (the translated words are the ones lessons teach)."""
    field = {"vocab": "meanings", "hanzi": "meaning", "grammar": "title"}[item_type]
    if all(oid in labels["translated"][item_type] for oid in option_ids):
        return {oid: labels[item_type].get(oid) for oid in option_ids}
    return {oid: getattr(rows[oid], field) for oid in option_ids if oid in rows}


def render_session(db: Session, session: models.PracticeSession, locale: str) -> dict:
    labels = _labels(db, session.questions, locale)
    rendered = []
    for i, q in enumerate(session.questions):
        item_type, qtype = q["item_type"], q["type"]
        if item_type in VIRTUAL:
            rendered.append(_render_virtual(db, q, i, session.answers[i], locale))
            continue
        target = _row(db, item_type, q["item_id"])
        options = []
        rows = {oid: r for oid in q["option_ids"] if (r := _row(db, item_type, oid)) is not None}
        option_text = _option_labels(labels, item_type, list(rows), rows)
        for oid in q["option_ids"]:
            r = rows.get(oid)
            if r is None:
                continue
            if qtype == "meaning_to_word":
                label = r.simplified
            elif qtype in ("word_to_meaning", "listen_to_word"):
                # A listening question is answered by meaning: the browser has
                # to be sent the word to speak it (prompt.speak), so options
                # in Chinese would let the answer be read straight off the
                # payload. Hearing it and knowing what it means is the task.
                label = _short(option_text.get(r.id))
            elif qtype == "char_to_meaning":
                label = _short(option_text.get(r.id))
            elif qtype == "char_to_pinyin":
                label = r.pinyin
            else:
                label = _short(option_text.get(r.id), 90)
            options.append({"id": oid, "label": label})
        prompt: dict = {}
        if target is not None:
            if qtype == "meaning_to_word":
                prompt = {"text": _short(labels["vocab"].get(target.id), 90)}
            elif qtype == "word_to_meaning":
                prompt = {"text": target.simplified, "pinyin": target.pinyin, "speak": target.simplified}
            elif qtype == "listen_to_word":
                # pinyin: shown only on a device that cannot speak Chinese, so
                # the question stays answerable there (the options are
                # meanings, so the reading does not give the answer away).
                prompt = {"speak": target.simplified, "pinyin": target.pinyin}
            elif qtype in ("char_to_meaning", "char_to_pinyin"):
                prompt = {"text": target.character, "speak": target.character if qtype == "char_to_meaning" else None}
            else:
                prompt = {"text": q.get("prompt") or "", "speak": q.get("prompt")}
        answer = session.answers[i]
        item = {"index": i, "type": qtype, "item_type": item_type, "prompt": prompt, "options": options, "answer": None}
        if q.get("tag"):
            # Detective Mode: an evidence note / grammar clue inside a case.
            item["tag"] = q["tag"]
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
        "context": _context(session, locale),
    }


# --------------------------------------------------------------------------- scene / sentence questions

def _context(session: models.PracticeSession, locale: str) -> dict | None:
    """What a scene/sentence round is about (stored with its first question)."""
    ctx = (session.questions or [{}])[0].get("ctx")
    if not ctx:
        return None
    if ctx.get("kind") == "scene":
        from app.services import real_life

        return real_life.ctx_render(ctx, locale)
    return ctx


def _line_tr(d: dict | None, locale: str) -> str:
    # zh UI reads the English gloss of a Chinese line (see real_life.text_for).
    d = d or {}
    return d.get(locale) or d.get("en") or ""


def _word_meaning(db: Session, word_id: int | None, locale: str) -> str:
    w = db.get(models.VocabularyWord, word_id) if word_id else None
    if w is None:
        return ""
    label = tr(load_translations(db, "vocab_word", [str(w.id)], locale), w.id, "meanings", w.meanings)
    return w.meanings if (label or "").strip() == w.simplified else (label or "")


def _virtual_card(db: Session, q: dict, locale: str) -> dict:
    """The correct answer, shown after grading."""
    qtype = q["type"]
    if q["item_type"] == "case":
        from app.services import detective

        return detective.card(db, q, locale)
    if q["item_type"] == "sound":
        from app.services import sound_world

        return sound_world.card(db, q, locale)
    if q["item_type"] == "reading":
        from app.services import internet

        return internet.card(db, q, locale)
    if qtype == "scene_reply":
        r = q["reply"]
        return {"hanzi": r["zh"], "pinyin": r["py"], "meaning": _line_tr(r.get("tr"), locale)}
    if qtype == "scene_listen":
        n = q["npc"]
        return {"hanzi": n["zh"], "pinyin": n["py"], "meaning": _line_tr(n.get("tr"), locale)}
    if qtype == "sentence_word":
        w = db.get(models.VocabularyWord, q.get("word_id"))
        return {"hanzi": q["options"][q["item_id"]]["zh"], "pinyin": w.pinyin if w else "",
                "meaning": _word_meaning(db, q.get("word_id"), locale)}
    return {"hanzi": q["sentence"], "pinyin": q.get("pinyin") or "", "meaning": ""}


def _render_virtual(db: Session, q: dict, index: int, answer: dict | None, locale: str) -> dict:
    qtype = q["type"]
    answered = answer is not None
    if q["item_type"] in ("case", "sound", "reading"):
        from app.services import detective, internet, sound_world

        mod = {"case": detective, "sound": sound_world, "reading": internet}[q["item_type"]]
        prompt, options = mod.render(db, q, answered, locale)
        item = {"index": index, "type": qtype, "item_type": q["item_type"], "prompt": prompt, "options": options,
                "answer": None, "can_speak": bool(q.get("say"))}
        if answered:
            item["answer"] = {**answer, "correct_id": q["item_id"], "card": _virtual_card(db, q, locale),
                              "say": (q.get("say") or {}).get("zh")}
        return item
    rules: dict = {}
    if q.get("scene"):
        from app.services.real_life import RULES

        rules = RULES.get(q.get("tier"), {})
    options = []
    for oid in q["option_ids"]:
        o = q["options"][oid]
        if qtype == "scene_listen":
            options.append({"id": oid, "label": _line_tr(o.get("tr"), locale)})
        else:
            options.append({"id": oid, "label": o["zh"],
                            "pinyin": (o.get("py") or None) if rules.get("option_pinyin") else None})
    prompt: dict = {}
    if qtype == "scene_listen":
        n = q["npc"]
        # Audio first; the reading is only for a device with no Chinese
        # voice (the options are meanings, so it doesn't give them away).
        prompt = {"speak": n["zh"], "pinyin": n["py"], "rate": q.get("rate") or rules.get("rate"), "turn": q.get("turn")}
    elif qtype == "scene_reply":
        n = q["npc"]
        prompt = {
            "speak": n["zh"], "rate": q.get("rate") or rules.get("rate"), "turn": q.get("turn"),
            "text": n["zh"] if (rules.get("show_text") or answered) else None,
            "pinyin": n["py"] if (rules.get("show_pinyin") or answered) else None,
            # Beginners may peek at the meaning; others see it after answering.
            "translation": _line_tr(n.get("tr"), locale) if (rules.get("show_translation") or answered) else None,
        }
    elif qtype == "sentence_word":
        prompt = {"text": q["sentence"], "speak": q["sentence"], "meaning": _word_meaning(db, q.get("word_id"), locale)}
    elif qtype == "sentence_listen":
        prompt = {"speak": q["sentence"], "pinyin": q.get("pinyin")}
    elif qtype == "sentence_order":
        prompt = {"chunks": q.get("chunks") or []}
    item = {"index": index, "type": qtype, "item_type": q["item_type"], "prompt": prompt, "options": options,
            "answer": None, "can_speak": bool(q.get("say"))}
    if answered:
        item["answer"] = {**answer, "correct_id": q["item_id"], "card": _virtual_card(db, q, locale),
                          "say": (q.get("say") or {}).get("zh")}
    return item


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


# DNA skill moves per scene/sentence question type: (code, +correct, -wrong).
_VIRTUAL_SKILLS = {
    "scene_reply": (("reading", 1.5, -0.3), ("vocabulary", 0.5, 0.0)),
    "scene_listen": (("listening", 2.0, -0.3), ("tones", 0.5, 0.0)),
    "sentence_listen": (("listening", 2.0, -0.3), ("tones", 0.5, 0.0)),
    "sentence_order": (("grammar", 2.0, -0.3), ("reading", 0.5, 0.0)),
    "sentence_word": (("reading", 1.5, -0.3), ("vocabulary", 0.5, 0.0)),
    # Detective Mode: a read clue trains reading, a heard one listening
    # (see _skills_for); the deduction is reasoning over remembered clues.
    "case_clue": (("reading", 1.5, -0.3), ("vocabulary", 0.5, 0.0)),
    "case_deduce": (("reading", 1.0, -0.3), ("memory", 1.5, -0.3)),
    # Sound World: every interaction is heard first.
    "sound_identify": (("listening", 2.0, -0.3), ("vocabulary", 0.5, 0.0)),
    "sound_info": (("listening", 2.0, -0.3), ("tones", 0.5, 0.0)),
    "sound_find": (("listening", 2.0, -0.3), ("vocabulary", 0.5, 0.0)),
    "sound_respond": (("listening", 1.5, -0.3), ("speaking", 0.5, 0.0)),
    "sound_conversation": (("listening", 2.0, -0.3), ("memory", 0.5, 0.0)),
    "sound_memory": (("listening", 1.5, -0.3), ("memory", 2.0, -0.3)),
    # Chinese Internet: real-text comprehension and a heard line.
    "net_comprehension": (("reading", 2.0, -0.3), ("vocabulary", 0.5, 0.0)),
    "net_listen": (("listening", 2.0, -0.3), ("reading", 0.5, 0.0)),
}
_LISTEN_CLUE = (("listening", 2.0, -0.3), ("tones", 0.5, 0.0))


def _skills_for(q: dict) -> tuple:
    if q["type"] == "case_clue" and q.get("mode") == "listen":
        return _LISTEN_CLUE
    return _VIRTUAL_SKILLS.get(q["type"], ())
VIRTUAL_SRS_DELTA = 6.0  # a dialogue line exercises its focus word less directly than a word card


def _record_virtual(db: Session, user: models.User, session: models.PracticeSession, q: dict,
                    correct: bool, response_ms: int) -> dict:
    """Applies a graded scene/sentence answer: the focus word's mastery
    (apply_srs), Learning DNA, mistakes (on the focus word, so Review
    brings it back), quests and XP -- the same real effects as _record."""
    qtype = q["type"]
    focus = db.get(models.VocabularyWord, q["focus_id"]) if q.get("focus_id") else None
    rec = status_before = None
    if focus is not None:
        rec = db.query(models.UserVocabulary).filter_by(user_id=user.id, word_id=focus.id).first()
        status_before = rec.status if rec is not None else None
        if rec is None:
            rec = models.UserVocabulary(user_id=user.id, word_id=focus.id, mastery=0.0, status="new", times_missed=0)
            db.add(rec)
        apply_srs(rec, correct, user, delta=VIRTUAL_SRS_DELTA)

    ensure_user_skills(db, user)
    primary = cr.PRIMARY_SKILL.get(qtype)
    skill_before = cr.skill_value(user, primary) if primary else None
    for code, plus, minus in _skills_for(q):
        bump_skill(user, code, plus if correct else minus)
    # Advanced scenes are heard before they're read: picking the right
    # reply is a listening task there too.
    if qtype == "scene_reply" and q.get("tier") == "advanced":
        bump_skill(user, "listening", 1.0 if correct else 0.0)
    if correct and 0 < response_ms <= FAST_ANSWER_MS:
        bump_skill(user, "reaction_speed", 0.5)

    if correct:
        if focus is not None:
            reinforce_mistake(db, user, "word", focus.simplified)
        if qtype in ("scene_listen", "sentence_listen", "net_listen") or q["item_type"] == "sound" or (
                qtype == "case_clue" and q.get("mode") == "listen"):
            progress_quests(db, user, "listening", amount=1)
        user.total_xp += XP_PER_CORRECT
    elif focus is not None:
        card = _virtual_card(db, q, "en")
        record_mistake(
            db, user, "word", focus.simplified,
            question_text=(q.get("npc") or {}).get("zh") or q.get("sentence") or card["hanzi"],
            correct_answer=" ".join(x for x in (card["hanzi"], card["pinyin"]) if x),
        )
    touch_streak(user)
    log_activity(db, user, "practice_answer")
    return {
        "mastery": rec.mastery if rec is not None else 0.0,
        "status_before": status_before if rec is not None else "learning",
        "status_after": rec.status if rec is not None else "learning",
        "times_missed": (rec.times_missed or 0) if rec is not None else 0,
        "skill": cr.skill_crossing(primary, skill_before, cr.skill_value(user, primary)) if primary else None,
        "vocab_mastered": rec is not None and rec.status == "mastered" and status_before != "mastered",
    }


def _focus_virtual(db: Session, q: dict, locale: str) -> dict | None:
    w = db.get(models.VocabularyWord, q["focus_id"]) if q.get("focus_id") else None
    if w is None:
        return None
    card = {"item_type": "vocab", "hanzi": w.simplified, "pinyin": w.pinyin, "meaning": _word_meaning(db, w.id, locale)}
    if w.example:
        card["example"] = w.example
        card["example_pinyin"] = w.example_pinyin
    return card


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
    virtual = q["item_type"] in VIRTUAL
    row = None if virtual else _row(db, q["item_type"], q["item_id"])
    if row is None and not virtual:
        raise PracticeError(410, "This item no longer exists")

    correct = choice_id == q["item_id"]
    now = datetime.utcnow()
    seen = [datetime.fromisoformat(a["answered_at"]) for a in session.answers if a and a.get("answered_at")]
    since = max(seen) if seen else (session.created_at or now)
    observed_ms = int((now - since).total_seconds() * 1000)
    response_ms = max(response_ms, observed_ms - FEEDBACK_ALLOWANCE_MS)

    # A wrong pick between two curriculum items the learner has mixed up
    # before (counted from their own stored answers, before this one).
    confused = None
    if not virtual and not correct and q["type"] in companion_memory_confusable():
        from app.services import companion_memory

        prior = companion_memory.confusion_count(db, user, q["item_type"], q["item_id"], choice_id,
                                                 exclude_session=session.id)
        picked = _row(db, q["item_type"], choice_id)
        if prior >= 1 and picked is not None:
            own = lambda r: getattr(r, "simplified", None) or getattr(r, "character", None)  # noqa: E731
            confused = {"a": own(row), "b": own(picked), "count": prior + 1}

    if virtual:
        change = _record_virtual(db, user, session, q, correct, response_ms)
    else:
        status_was = None
        if q["item_type"] == "vocab":
            rec = db.query(models.UserVocabulary).filter_by(user_id=user.id, word_id=row.id).first()
            status_was = rec.status if rec else None
        change = _record(db, user, session, q, row, correct, response_ms)
        change["vocab_mastered"] = (q["item_type"] == "vocab" and change["status_after"] == "mastered"
                                    and status_was != "mastered")
    answers = list(session.answers)  # reassign so the JSON column is marked dirty
    answers[index] = {"choice_id": choice_id, "correct": correct, "response_ms": response_ms,
                      "answered_at": now.isoformat()}
    if change.get("vocab_mastered"):
        # Counted at completion for the mastered-words milestone.
        answers[index]["mastered_vocab"] = True
    session.answers = answers
    db.commit()
    if virtual:
        card = _virtual_card(db, q, locale)
        focus = _focus_virtual(db, q, locale)
    else:
        labels = _labels(db, [q], locale)
        card = _item_card(q["item_type"], row, labels)
        focus = _focus(q["item_type"], row, labels)
    out = {
        "correct": correct,
        "correct_id": q["item_id"],
        "card": card,
        "mastery": round(change["mastery"], 1),
        "xp_gained": XP_PER_CORRECT if correct else 0,
        "reaction": cr.answer_reaction(
            user, answers,
            item_type=(focus or {}).get("item_type", q["item_type"]) if virtual else q["item_type"], focus=focus,
            status_before=change["status_before"], status_after=change["status_after"],
            times_missed=change["times_missed"], skill=change["skill"], confused=confused,
        ),
    }
    if virtual:
        out["say"] = (q.get("say") or {}).get("zh")
        # The question as it reads now that it's answered (a hidden line is
        # revealed), so the dialogue thread can show it.
        out["question"] = _render_virtual(db, q, index, answers[index], locale)
    return out


def companion_memory_confusable() -> set[str]:
    from app.services.companion_memory import _CONFUSABLE

    return _CONFUSABLE


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
        if session.source == "scene":
            log_activity(db, user, "real_life_scene")
        elif session.source == "sentence":
            log_activity(db, user, "sentence_lesson")
        elif session.source == "detective":
            log_activity(db, user, "detective_case")
            # "Detective hour" counts an attempted case; "Solve ... Cases"
            # missions only a case whose deduction was right.
            progress_quests(db, user, "case", amount=1)
            final = answers[-1] if answers else None
            if final and final.get("correct") and session.questions[-1]["type"] == "case_deduce":
                progress_missions(db, user, "case")
        elif session.source == "sound":
            log_activity(db, user, "sound_world")
        elif session.source == "internet":
            log_activity(db, user, "internet_read")
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
        if a is not None and not a["correct"] and q["item_type"] in VIRTUAL:
            missed.append({"item_type": q["item_type"], **_virtual_card(db, q, locale)})
            focus = focus or _focus_virtual(db, q, locale)
            continue
        if a is not None and not a["correct"]:
            row = _row(db, q["item_type"], q["item_id"])
            if row is not None:
                missed.append({"item_type": q["item_type"], **_item_card(q["item_type"], row, labels)})
                # The first missed item is the one the companion suggests
                # revisiting -- it is already queued for Review.
                focus = focus or _focus(q["item_type"], row, labels)
    # Did this round push the learner's mastered-word count past a milestone?
    words_milestone = None
    newly = sum(1 for a in answers if a and a.get("mastered_vocab"))
    if first_completion and newly:
        from app.services.companion_memory import WORD_MILESTONES

        total_now = db.query(models.UserVocabulary).filter_by(user_id=user.id, status="mastered").count()
        crossed = [m for m in WORD_MILESTONES if total_now - newly < m <= total_now]
        words_milestone = crossed[-1] if crossed else None
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
            words_milestone=words_milestone,
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
    from app.services.companion_memory import days_away

    return cr.start_reaction(user, session.source, words=words, due=due, away_days=days_away(db, user))


# --------------------------------------------------------------------------- speaking

def speak(db: Session, user: models.User, session: models.PracticeSession, index: int, spoken_text: str,
          response_ms: int) -> dict:
    """Say the line / sentence of an answered scene or sentence question.

    The answer key is the stored question's own text (never anything the
    browser sends), graded by the same voice pipeline as World turns and
    stored as a real VoiceAttempt, so speaking feeds the speaking/tones DNA,
    the speaking quest and the voice achievements. Capped per question."""
    from app.services import voice_eval
    from app.services.dna import apply_voice_to_skills

    if not 0 <= index < len(session.questions):
        raise PracticeError(422, "No such question")
    q = session.questions[index]
    say = q.get("say")
    if not say:
        raise PracticeError(422, "This question has nothing to say aloud")
    answer = session.answers[index]
    if answer is None:
        raise PracticeError(409, "Answer the question before saying it aloud")
    if (answer.get("spoken") or 0) >= SPEAK_LIMIT:
        raise PracticeError(409, "You've already practised saying this one")

    ensure_user_skills(db, user)
    result = voice_eval.grade_turn(None, spoken_text, expected_keywords=say.get("keywords") or [say["zh"]])
    attempt = models.VoiceAttempt(
        user_id=user.id, prompt_text=say["zh"], spoken_text=spoken_text, transcript=result["transcript"],
        pronunciation=result["pronunciation"], tones=result["tones"], fluency=result["fluency"],
        grammar=result["grammar"], relevance=result["relevance"], response_time_ms=response_ms,
        overall=result["overall"], feedback=result["feedback"],
    )
    db.add(attempt)
    db.flush()
    apply_voice_to_skills(user, attempt)
    progress_quests(db, user, "speaking", amount=1)
    log_activity(db, user, "voice_attempt")
    answers = list(session.answers)
    answers[index] = {**answer, "spoken": (answer.get("spoken") or 0) + 1,
                      "spoken_best": max(answer.get("spoken_best") or 0, round(result["overall"], 1))}
    session.answers = answers
    db.commit()
    return {
        "target": say["zh"],
        "transcript": result["transcript"],
        "scores": {k: round(result[k], 1) for k in ("pronunciation", "tones", "fluency", "relevance", "overall")},
        "is_correct": result["is_correct"],
        "attempts_left": SPEAK_LIMIT - answers[index]["spoken"],
    }


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
