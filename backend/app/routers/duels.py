import random
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.services.dna import bump_skill, compute_dna
from app.services.gamification import (
    check_achievements,
    ensure_user_skills,
    progress_missions,
    progress_quests,
    record_mistake,
    reinforce_mistake,
    user_rank,
)

router = APIRouter(prefix="/api/duels", tags=["duels"])

QUESTION_COUNT = 5

# Which Learning DNA skill and LearningMistake bucket each duel question
# type feeds — this is what makes a duel a Learning-DNA activity instead of
# an isolated vocab quiz.
TYPE_SKILL = {
    "pinyin": "vocabulary",
    "meaning": "vocabulary",
    "translate": "vocabulary",
    "recognition": "speaking",
    "tone": "tones",
    "character": "reading",
    "memory": "memory",
    "listening": "listening",
    "reaction": "reaction_speed",
}
TYPE_MISTAKE = {
    "pinyin": "pinyin",
    "tone": "tone",
    "character": "character",
}

# The inverse of TYPE_SKILL, picking one representative duel type per
# skill — used to auto-focus a duel on whichever skill is currently weakest
# when the player doesn't request a specific challenge type.
SKILL_TO_FOCUS = {
    "tones": "tone",
    "listening": "listening",
    "memory": "memory",
    "reaction_speed": "reaction",
    "speaking": "recognition",
    "reading": "character",
    "vocabulary": "meaning",
    "grammar": "translate",
    "writing": "translate",
}

TONE_LABELS = {1: "1st tone", 2: "2nd tone", 3: "3rd tone", 4: "4th tone", 5: "neutral tone"}
_TONE_MARKS = {1: "āēīōūǖ", 2: "áéíóúǘ", 3: "ǎěǐǒǔǚ", 4: "àèìòùǜ"}


def _tone_of(pinyin: str) -> int:
    for ch in pinyin or "":
        for tone, marks in _TONE_MARKS.items():
            if ch in marks:
                return tone
    return 5


def _meaning_of(word: models.VocabularyWord) -> str:
    return (word.meanings or word.simplified).split(",")[0].strip()


VALID_FOCUS_TYPES = {"pinyin", "meaning", "translate", "recognition", "tone", "character", "listening", "reaction"}
FOCUS_HIT_RATE = 0.7  # a "focused" duel is mostly-but-not-only that type, so it doesn't feel monotonous


def _build_questions(
    db: Session, level_id: int | None, word_pool=None, focus_type: str | None = None
) -> list[dict]:
    if word_pool is None:
        query = db.query(models.VocabularyWord)
        if level_id is not None:
            query = query.filter(models.VocabularyWord.hsk_level_id == level_id)
        words = query.limit(40).all()
    else:
        words = word_pool
    if not words:
        words = db.query(models.VocabularyWord).all()

    chosen = random.sample(words, k=min(QUESTION_COUNT, len(words)))
    single_char = [w for w in chosen if len(w.simplified) == 1]

    base_types = ["pinyin", "meaning", "translate", "recognition", "tone", "listening", "reaction"]
    questions = []
    for i, word in enumerate(chosen):
        pool = list(base_types)
        if word in single_char and len(single_char) >= 2:
            pool.append("character")
        if focus_type and focus_type in pool and random.random() < FOCUS_HIT_RATE:
            qtype = focus_type
        else:
            qtype = random.choice(pool)

        meaning = _meaning_of(word)
        others = [w for w in chosen if w.id != word.id]
        options = None
        tts_text = None

        if qtype == "pinyin":
            prompt, answer = word.simplified, word.pinyin
            options = [answer] + random.sample([w.pinyin for w in others], k=min(3, len(others)))
        elif qtype in ("meaning", "reaction"):
            prompt, answer = word.simplified, meaning
            options = [answer] + random.sample([_meaning_of(w) for w in others], k=min(3, len(others)))
        elif qtype == "translate":
            prompt, answer = f"{meaning} → Chinese", word.simplified
            options = [answer] + random.sample([w.simplified for w in others], k=min(3, len(others)))
        elif qtype == "recognition":
            prompt, answer = meaning, word.simplified  # no options — spoken aloud
        elif qtype == "tone":
            tone = _tone_of(word.pinyin)
            prompt, answer = f"What tone is 「{word.simplified}」 ({word.pinyin})?", TONE_LABELS[tone]
            other_labels = [v for k, v in TONE_LABELS.items() if k != tone]
            options = [answer] + random.sample(other_labels, k=min(3, len(other_labels)))
        elif qtype == "character":
            prompt, answer = f'Which character means "{meaning}"?', word.simplified
            other_chars = [w.simplified for w in single_char if w.id != word.id]
            options = [answer] + random.sample(other_chars, k=min(3, len(other_chars)))
        else:  # listening
            prompt, answer = "🔊 Listen, then choose the meaning", meaning
            tts_text = word.simplified
            options = [answer] + random.sample([_meaning_of(w) for w in others], k=min(3, len(others)))

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

    # One question (if there's a "previous" one to reference) becomes a
    # short-term-recall check instead of a fresh vocabulary lookup — a
    # genuinely different mechanic, not just another vocab quiz dressed up.
    if len(questions) >= 2:
        mem_idx = random.randint(1, len(questions) - 1)
        prev_word = chosen[mem_idx - 1]
        prev_meaning = _meaning_of(prev_word)
        distractors = [_meaning_of(w) for w in chosen if w.id != prev_word.id]
        mem_options = [prev_meaning] + random.sample(distractors, k=min(3, len(distractors)))
        random.shuffle(mem_options)
        questions[mem_idx] = {
            "index": mem_idx,
            "type": "memory",
            "prompt": f"What did the PREVIOUS word 「{prev_word.simplified}」 mean?",
            "options": mem_options,
            "answer": prev_meaning,
            "tts_text": None,
        }

    return questions


def _personalized_word_pool(db: Session, user: models.User, level: int) -> list[models.VocabularyWord]:
    """Bias the duel toward the challenger's own weak/unseen vocabulary at
    their current HSK level — this is what makes a duel a Learning-DNA
    challenge instead of a generic quiz everyone gets the same version of."""
    level_obj = db.query(models.HSKLevel).filter_by(level=level).first()
    query = db.query(models.VocabularyWord)
    if level_obj is not None:
        query = query.filter(models.VocabularyWord.hsk_level_id == level_obj.id)
    words = query.all()
    if not words:
        words = db.query(models.VocabularyWord).all()

    mastery_by_word = {uv.word_id: uv.mastery for uv in user.user_vocabulary}
    words.sort(key=lambda w: mastery_by_word.get(w.id, 0.0))
    return words[:40] or words


def _buddy(db: Session) -> models.User:
    """Get-or-create the system 'Buddy' sparring partner."""
    buddy = db.query(models.User).filter_by(username="__buddy_ai__").first()
    if buddy is None:
        buddy = models.User(
            username="__buddy_ai__",
            email="buddy.ai@linguaverse.internal",
            password_hash="!",
        )
        db.add(buddy)
        db.flush()
    return buddy


@router.post("", response_model=schemas.DuelResponse, status_code=201)
def create_duel(
    payload: schemas.DuelCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    opponent = (
        db.query(models.User)
        .filter(models.User.username == payload.opponent_username)
        .first()
    )
    if payload.opponent_username.lower() == "buddy" or opponent is None:
        opponent = None

    ensure_user_skills(db, user)
    level, _mastery = user_rank(db, user)
    word_pool = _personalized_word_pool(db, user, level)

    focus_type = payload.challenge_type if payload.challenge_type in VALID_FOCUS_TYPES else None
    challenge_label = payload.challenge_type
    if focus_type is None:
        weakest = compute_dna(user).get("weakest_skill")
        focus_type = SKILL_TO_FOCUS.get(weakest)
        challenge_label = f"weakest strand · {weakest}" if weakest else None

    questions = _build_questions(db, None, word_pool=word_pool, focus_type=focus_type)

    duel = models.Duel(
        status="active",
        challenge_type=challenge_label,
        question_data={"questions": questions},
    )
    db.add(duel)
    db.flush()

    db.add(models.DuelParticipant(duel_id=duel.id, user_id=user.id, role="challenger"))
    if opponent is not None:
        db.add(models.DuelParticipant(duel_id=duel.id, user_id=opponent.id, role="opponent"))
    else:
        buddy = _buddy(db)
        db.add(models.DuelParticipant(duel_id=duel.id, user_id=buddy.id, role="opponent"))

    db.commit()
    return schemas.DuelResponse(
        id=duel.id, status=duel.status, challenge_type=duel.challenge_type,
        questions=[schemas.DuelQuestion(**q) for q in questions],
        opponent=opponent.username if opponent else "Buddy",
        my_score=0, opp_score=0,
    )


@router.get("", response_model=list[schemas.DuelResponse])
def list_duels(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    participant_ids = {p.duel_id for p in user.participants}
    duels = (
        db.query(models.Duel)
        .filter(models.Duel.id.in_(list(participant_ids) or [0]))
        .order_by(models.Duel.created_at.desc())
        .all()
    )
    return [_serialize(db, d, user) for d in duels]


@router.get("/{duel_id}", response_model=schemas.DuelResponse)
def get_duel(
    duel_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    duel = db.get(models.Duel, duel_id)
    if duel is None:
        raise HTTPException(status_code=404, detail="Duel not found")
    return _serialize(db, duel, user)


def _serialize(db: Session, duel: models.Duel, user: models.User) -> schemas.DuelResponse:
    questions = (duel.question_data or {}).get("questions", [])
    me = next((p for p in duel.participants if p.user_id == user.id), None)
    opp = next((p for p in duel.participants if p.user_id != user.id), None)
    opp_user = None
    if opp and opp.user_id > 0:
        opp_user = db.get(models.User, opp.user_id)
    opp_name = "Buddy"
    if opp_user and opp_user.username != "__buddy_ai__":
        opp_name = opp_user.username
    winner = None
    if duel.status == "finished" and duel.winner_id:
        winner_user = db.get(models.User, duel.winner_id)
        if winner_user:
            winner = (
                "Buddy"
                if winner_user.username == "__buddy_ai__"
                else winner_user.username
            )
    return schemas.DuelResponse(
        id=duel.id, status=duel.status, challenge_type=duel.challenge_type,
        questions=[schemas.DuelQuestion(**q) for q in questions],
        opponent=opp_name,
        my_score=me.score if me else None,
        opp_score=opp.score if opp else None,
        finished=duel.status == "finished",
        winner=winner,
    )


@router.post("/{duel_id}/answer", response_model=dict)
def answer_question(
    duel_id: int,
    payload: schemas.DuelAnswer,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    duel = db.get(models.Duel, duel_id)
    if duel is None:
        raise HTTPException(status_code=404, detail="Duel not found")
    me = next((p for p in duel.participants if p.user_id == user.id), None)
    if me is None:
        raise HTTPException(status_code=403, detail="Not your duel")
    if duel.status == "finished":
        raise HTTPException(status_code=409, detail="Duel already finished")

    questions = (duel.question_data or {}).get("questions", [])
    if payload.index >= len(questions):
        raise HTTPException(status_code=400, detail="Question index out of range")

    q = questions[payload.index]
    qtype = q.get("type", "meaning")
    correct = (payload.answer or "").strip().lower() == (q.get("answer") or "").strip().lower()

    ensure_user_skills(db, user)
    if correct:
        base = 10
        if qtype == "reaction":
            # Reward speed on top of correctness — the whole point of this type.
            speed_bonus = round(max(0.0, 1 - payload.response_time_ms / 6000) * 8)
            base += speed_bonus
        me.score += base
        me.correct_count += 1
        bump_skill(user, TYPE_SKILL.get(qtype, "vocabulary"), 2.0)
    else:
        me.score += 2
        bump_skill(user, TYPE_SKILL.get(qtype, "vocabulary"), -0.3)
    me.answered += 1

    mistake_type = TYPE_MISTAKE.get(qtype)
    if mistake_type:
        reference = q.get("prompt") or (q.get("answer") or "")[:300]
        if correct:
            reinforce_mistake(db, user, mistake_type, reference)
        else:
            record_mistake(
                db, user, mistake_type, reference,
                question_text=q.get("prompt"), answer_given=payload.answer,
                correct_answer=q.get("answer"),
            )

    db.commit()

    return {
        "index": payload.index,
        "answer": q.get("answer"),
        "correct": correct,
        "my_score": me.score,
    }


@router.post("/{duel_id}/finish", response_model=schemas.DuelResponse)
def finish_duel(
    duel_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    duel = db.get(models.Duel, duel_id)
    if duel is None:
        raise HTTPException(status_code=404, detail="Duel not found")
    if duel.status == "finished":
        return _serialize(db, duel, user)

    me = next((p for p in duel.participants if p.user_id == user.id), None)
    opp = next((p for p in duel.participants if p.user_id != user.id), None)
    if me is None:
        raise HTTPException(status_code=403, detail="Not your duel")

    # Buddy (or an unanswered opponent) plays out the remaining questions.
    # Accuracy rubber-bands around the challenger's own performance (55-85%)
    # so the duel feels competitive instead of a fixed pushover/wall.
    total = len((duel.question_data or {}).get("questions", []))
    if opp and opp.answered == 0:
        my_accuracy = (me.correct_count / me.answered) if me and me.answered else 0.7
        target_accuracy = max(0.55, min(0.85, my_accuracy + random.uniform(-0.1, 0.1)))
        opp_correct = round(total * target_accuracy)
        opp.score = opp_correct * 10 + (total - opp_correct) * 2
        opp.correct_count = opp_correct
        opp.answered = total
    if opp and opp.user_id == user.id:
        opp = None

    duel.status = "finished"
    duel.finished_at = datetime.now(timezone.utc)
    winner = None
    if me and opp:
        winner = me if me.score >= opp.score else opp
    elif me and me.score > 0:
        winner = me
    if winner is not None and winner.user_id > 0:
        duel.winner_id = winner.user_id
    db.commit()

    if winner is not None and winner.user_id == user.id:
        progress_quests(db, user, "duel", amount=1)
        progress_missions(db, user, "duel")
        check_achievements(db, user)
        db.commit()

    return _serialize(db, duel, user)