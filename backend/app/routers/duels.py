"""/api/duels -- real 1-vs-1 duels between two users.

All rules live in services/duel.py; this module is the HTTP layer. Every
route authenticates, and every route that names a duel resolves it through
duel_svc.load_for(), which 404s for anyone who is not one of its two
participants. Nothing about the result (correctness, time, score, winner)
is accepted from the client.
"""

import random

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services import duel as duel_svc
from app.services.gamification import user_rank
from app.services.localization import load_translations, tr

router = APIRouter(prefix="/api/duels", tags=["duels"])


# ---------------------------------------------------------------------------
# Placement-test question builder (used by routers/onboarding.py). This is the
# original duel question generator; real duels now use the server-graded
# practice engine via services/duel.py.
# ---------------------------------------------------------------------------

QUESTION_COUNT = 5

TONE_LABELS = {1: "1st tone", 2: "2nd tone", 3: "3rd tone", 4: "4th tone", 5: "neutral tone"}

# The placement test is shown in the learner's language: its prompts used to
# be English for everyone. Answers are stored in the same language when the
# test starts, so grading (an exact text match) is unaffected. Chinese words
# and pinyin are the content being tested and stay as they are.
PLACEMENT_TEXT = {
    "en": {
        "translate": "{meaning} → Chinese",
        "tone": "What tone is 「{word}」?",
        "character": 'Which character means "{meaning}"?',
        "listening": "🔊 Listen, then choose the meaning",
        "memory": "What did the PREVIOUS word 「{word}」 mean?",
        "tones": TONE_LABELS,
    },
    "ru": {
        "translate": "{meaning} → по-китайски",
        "tone": "Какой тон у «{word}»?",
        "character": "Какой иероглиф означает «{meaning}»?",
        "listening": "🔊 Послушайте и выберите значение",
        "memory": "Что означало ПРЕДЫДУЩЕЕ слово «{word}»?",
        "tones": {1: "1-й тон", 2: "2-й тон", 3: "3-й тон", 4: "4-й тон", 5: "нейтральный тон"},
    },
    "tg": {
        "translate": "{meaning} → ба забони чинӣ",
        "tone": "Оҳанги «{word}» кадом аст?",
        "character": "Кадом иероглиф маънои «{meaning}»-ро дорад?",
        "listening": "🔊 Гӯш кунед ва маъноро интихоб кунед",
        "memory": "Калимаи ПЕШИНА «{word}» чӣ маъно дошт?",
        "tones": {1: "оҳанги 1", 2: "оҳанги 2", 3: "оҳанги 3", 4: "оҳанги 4", 5: "оҳанги нейтралӣ"},
    },
    "zh": {
        "translate": "{meaning} → 中文",
        "tone": "「{word}」是第几声？",
        "character": "哪个汉字的意思是“{meaning}”？",
        "listening": "🔊 听一听，选出意思",
        "memory": "上一个词「{word}」是什么意思？",
        "tones": {1: "第一声", 2: "第二声", 3: "第三声", 4: "第四声", 5: "轻声"},
    },
}
_TONE_MARKS = {1: "āēīōūǖ", 2: "áéíóúǘ", 3: "ǎěǐǒǔǚ", 4: "àèìòùǜ"}


def _tone_of(pinyin: str) -> int:
    for ch in pinyin or "":
        for tone, marks in _TONE_MARKS.items():
            if ch in marks:
                return tone
    return 5


def _meaning_of(word: models.VocabularyWord, labels: dict[int, str] | None = None) -> str:
    text = (labels or {}).get(word.id) or word.meanings or word.simplified
    return text.split(",")[0].split(";")[0].strip()


def _meaning_labels(db: Session, words, locale: str) -> dict[int, str]:
    """Each word's meaning in the learner's language -- or {} (the English
    glosses) unless every word has a real translation. The zh "meaning"
    that is the word itself never counts: it would print the answer."""
    trs = load_translations(db, "vocab_word", [str(w.id) for w in words], locale)
    out = {}
    for w in words:
        label = tr(trs, w.id, "meanings", w.meanings)
        if (label or "").strip() == w.simplified or label == w.meanings:
            # One language for the whole set: a lone translated meaning
            # among English ones would give its question's answer away.
            return {}
        out[w.id] = label
    return out


VALID_FOCUS_TYPES = {"pinyin", "meaning", "translate", "recognition", "tone", "character", "listening", "reaction", "memory"}
FOCUS_HIT_RATE = 0.7  # a "focused" duel is mostly-but-not-only that type, so it doesn't feel monotonous


def _build_questions(
    db: Session, level_id: int | None, word_pool=None, focus_type: str | None = None, locale: str = "en",
) -> list[dict]:
    if word_pool is None:
        query = db.query(models.VocabularyWord)
        if level_id is not None:
            query = query.filter(models.VocabularyWord.hsk_level_id == level_id)
        words = query.limit(40).all()
        if locale != "en" and level_id is not None:
            # Prefer this level's words that have a meaning in the learner's
            # language, so the whole test can be shown in it.
            keys = {
                int(t.content_key)
                for t in db.query(models.ContentTranslation.content_key).filter_by(
                    content_type="vocab_word", field="meanings", locale=locale)
            }
            local = [w for w in db.query(models.VocabularyWord).filter_by(hsk_level_id=level_id).order_by(models.VocabularyWord.id)
                     if w.id in keys]
            if len(local) >= QUESTION_COUNT + 3:
                words = local[:40]
    else:
        words = word_pool
    if not words:
        words = db.query(models.VocabularyWord).all()

    chosen = random.sample(words, k=min(QUESTION_COUNT, len(words)))
    single_char = [w for w in chosen if len(w.simplified) == 1]
    text = PLACEMENT_TEXT.get(locale, PLACEMENT_TEXT["en"])
    labels = _meaning_labels(db, chosen, locale)

    # "tone" is only asked about a single character: the prompt cannot show
    # the pinyin (its tone mark IS the answer), and a word without it has
    # one tone per syllable.
    base_types = ["pinyin", "meaning", "translate", "recognition", "listening", "reaction"]
    if locale == "zh":
        # There are no Chinese glosses (a zh "meaning" is the word itself), so
        # a prompt that IS a meaning would be English in the Chinese UI.
        base_types = [t for t in base_types if t not in ("translate", "recognition")]
    questions = []
    for i, word in enumerate(chosen):
        pool = list(base_types)
        if word in single_char:
            pool.append("tone")
        if word in single_char and len(single_char) >= 2 and locale != "zh":
            pool.append("character")
        if focus_type and focus_type in pool and random.random() < FOCUS_HIT_RATE:
            qtype = focus_type
        else:
            qtype = random.choice(pool)

        meaning = _meaning_of(word, labels)
        others = [w for w in chosen if w.id != word.id]
        options = None
        tts_text = None

        if qtype == "pinyin":
            prompt, answer = word.simplified, word.pinyin
            options = [answer] + random.sample([w.pinyin for w in others], k=min(3, len(others)))
        elif qtype in ("meaning", "reaction"):
            prompt, answer = word.simplified, meaning
            options = [answer] + random.sample([_meaning_of(w, labels) for w in others], k=min(3, len(others)))
        elif qtype == "translate":
            prompt, answer = text["translate"].format(meaning=meaning), word.simplified
            options = [answer] + random.sample([w.simplified for w in others], k=min(3, len(others)))
        elif qtype == "recognition":
            prompt, answer = meaning, word.simplified  # no options — spoken aloud
        elif qtype == "tone":
            tone = _tone_of(word.pinyin)
            prompt, answer = text["tone"].format(word=word.simplified), text["tones"][tone]
            other_labels = [v for k, v in text["tones"].items() if k != tone]
            options = [answer] + random.sample(other_labels, k=min(3, len(other_labels)))
        elif qtype == "character":
            prompt, answer = text["character"].format(meaning=meaning), word.simplified
            other_chars = [w.simplified for w in single_char if w.id != word.id]
            options = [answer] + random.sample(other_chars, k=min(3, len(other_chars)))
        else:  # listening
            prompt, answer = text["listening"], meaning
            tts_text = word.simplified
            options = [answer] + random.sample([_meaning_of(w, labels) for w in others], k=min(3, len(others)))

        if options is not None:
            random.shuffle(options)

        questions.append(
            {
                "index": i,
                "type": qtype,
                "prompt": prompt,
                "options": options,
                "answer": answer,
                "tts_text": tts_text,
            }
        )

    # At least one question (if there's a "previous" one to reference)
    # becomes a short-term-recall check instead of a fresh vocabulary
    # lookup — a genuinely different mechanic, not just another vocab quiz
    # dressed up. A "memory"-focused duel (Snake's preferred mechanic)
    # converts most eligible questions this way instead of just one.
    if len(questions) >= 2:
        eligible = list(range(1, len(questions)))
        if focus_type == "memory":
            mem_indices = [i for i in eligible if random.random() < FOCUS_HIT_RATE] or [random.choice(eligible)]
        else:
            mem_indices = [random.choice(eligible)]
        for mem_idx in mem_indices:
            prev_word = chosen[mem_idx - 1]
            prev_meaning = _meaning_of(prev_word, labels)
            distractors = [_meaning_of(w, labels) for w in chosen if w.id != prev_word.id]
            mem_options = [prev_meaning] + random.sample(distractors, k=min(3, len(distractors)))
            random.shuffle(mem_options)
            questions[mem_idx] = {
                "index": mem_idx,
                "type": "memory",
                "prompt": text["memory"].format(word=prev_word.simplified),
                "options": mem_options,
                "answer": prev_meaning,
                "tts_text": None,
            }

    return questions


# ---------------------------------------------------------------------------
# Real duels
# ---------------------------------------------------------------------------


class DuelCreate(BaseModel):
    opponent_id: int = Field(ge=1)
    hsk_level: int | None = Field(default=None, ge=1, le=9)
    focus: str | None = Field(default=None, max_length=20)


class DuelAnswerIn(BaseModel):
    index: int = Field(ge=0)
    choice_id: int


def _error(exc: duel_svc.DuelError) -> JSONResponse:
    # `detail` stays a readable sentence (what api.js shows by default);
    # `code` lets the UI show it in the learner's language.
    return JSONResponse(status_code=exc.status, content={"detail": exc.detail, "code": exc.code})


def _guard(fn):
    """Turns a DuelError anywhere in the route into a {detail, code} reply."""
    import functools
    import inspect

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except duel_svc.DuelError as exc:
            return _error(exc)

    wrapper.__signature__ = inspect.signature(fn)
    return wrapper


def _load(db: Session, duel_id: int, user: models.User) -> models.Duel:
    return duel_svc.load_for(db, duel_id, user)


@router.get("/opponents")
def list_opponents(
    q: str | None = Query(default=None, max_length=50),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Who can be challenged: the user's following/followers, or anyone by
    username search. Each entry says whether a duel with them is already
    open (one open duel per pair) and their current HSK level."""
    out = []
    for u in duel_svc.opponent_candidates(db, user, q):
        open_duel = duel_svc.open_duel_between(db, user.id, u.id)
        out.append({
            "id": u.id,
            "username": u.username,
            "avatar_url": u.profile.avatar_url if u.profile else None,
            "animal_slug": u.animal.slug if u.animal else None,
            "hsk_level": user_rank(db, u)[0],
            "open_duel_id": open_duel.id if open_duel else None,
        })
    db.commit()
    return {
        "my_level": user_rank(db, user)[0],
        "rules": {"question_count": duel_svc.QUESTION_COUNT, "time_limit_seconds": duel_svc.TIME_LIMIT_SECONDS},
        "opponents": out,
    }


@router.post("", status_code=201)
def create_duel(
    payload: DuelCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    try:
        duel = duel_svc.create(db, user, payload.opponent_id, payload.hsk_level, payload.focus)
    except duel_svc.DuelError as exc:
        db.rollback()
        return _error(exc)
    return duel_svc.view(db, duel, user, locale)


@router.get("")
def list_duels(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    ids = [p.duel_id for p in db.query(models.DuelParticipant).filter_by(user_id=user.id)]
    duels = (
        db.query(models.Duel)
        .filter(models.Duel.id.in_(ids or [0]))
        .order_by(models.Duel.created_at.desc(), models.Duel.id.desc())
        .limit(100)
        .all()
    )
    changed = False
    for d in duels:
        if d.status in duel_svc.OPEN_STATUSES:
            changed = duel_svc.refresh(db, d) or changed
    if changed:
        db.commit()
    return [duel_svc.view(db, d, user, locale, with_questions=False) for d in duels]


@router.get("/{duel_id}")
@_guard
def get_duel(
    duel_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    duel = _load(db, duel_id, user)
    duel_svc.refresh(db, duel)
    db.commit()
    return duel_svc.view(db, duel, user, locale)


def _act(db, duel_id, user, locale, fn, *args):
    duel = _load(db, duel_id, user)
    result = fn(db, duel, user, *args)
    duel = _load(db, duel_id, user)
    return result, duel_svc.view(db, duel, user, locale)


@router.post("/{duel_id}/accept")
@_guard
def accept_duel(duel_id: int, user: models.User = Depends(get_current_user),
                db: Session = Depends(get_db), locale: str = Depends(get_locale)):
    return _act(db, duel_id, user, locale, duel_svc.accept)[1]


@router.post("/{duel_id}/decline")
@_guard
def decline_duel(duel_id: int, user: models.User = Depends(get_current_user),
                 db: Session = Depends(get_db), locale: str = Depends(get_locale)):
    return _act(db, duel_id, user, locale, duel_svc.decline)[1]


@router.post("/{duel_id}/cancel")
@_guard
def cancel_duel(duel_id: int, user: models.User = Depends(get_current_user),
                db: Session = Depends(get_db), locale: str = Depends(get_locale)):
    return _act(db, duel_id, user, locale, duel_svc.cancel)[1]


@router.post("/{duel_id}/start")
@_guard
def start_duel(duel_id: int, user: models.User = Depends(get_current_user),
               db: Session = Depends(get_db), locale: str = Depends(get_locale)):
    """Starts the caller's own clock (idempotent)."""
    return _act(db, duel_id, user, locale, duel_svc.start_attempt)[1]


@router.post("/{duel_id}/answer")
@_guard
def answer_duel(duel_id: int, payload: DuelAnswerIn, user: models.User = Depends(get_current_user),
                db: Session = Depends(get_db), locale: str = Depends(get_locale)):
    graded, state = _act(db, duel_id, user, locale, duel_svc.answer, payload.index, payload.choice_id)
    return {"answer": graded, "duel": state}


@router.post("/{duel_id}/forfeit")
@_guard
def forfeit_duel(duel_id: int, user: models.User = Depends(get_current_user),
                 db: Session = Depends(get_db), locale: str = Depends(get_locale)):
    """Ends the caller's own attempt early; the opponent keeps playing."""
    return _act(db, duel_id, user, locale, duel_svc.forfeit)[1]
