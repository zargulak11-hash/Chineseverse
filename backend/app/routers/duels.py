from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.services.gamification import check_achievements, progress_quests

router = APIRouter(prefix="/api/duels", tags=["duels"])

QUESTION_COUNT = 5


def _build_questions(db: Session, level_id: int | None, word_pool=None) -> list[dict]:
    if word_pool is None:
        query = db.query(models.VocabularyWord)
        if level_id is not None:
            query = query.filter(models.VocabularyWord.hsk_level_id == level_id)
        words = query.limit(40).all()
    else:
        words = word_pool
    if not words:
        words = db.query(models.VocabularyWord).all()

    import random
    chosen = random.sample(words, k=min(QUESTION_COUNT, len(words)))
    questions = []
    for i, word in enumerate(chosen):
        qtype = random.choice(["pinyin", "meaning", "translate"])
        if qtype == "pinyin":
            prompt = word.simplified
            answer = word.pinyin
        elif qtype == "meaning":
            prompt = word.simplified
            answer = (word.meanings or word.simplified).split(",")[0].strip()
        else:
            prompt = (word.meanings or word.simplified).split(",")[0].strip() + " → Chinese"
            answer = word.simplified
        distractors = [w for w in chosen if w.id != word.id][:3]
        options = [answer] + random.sample(
            [w.simplified if qtype != "pinyin" else w.pinyin for w in distractors],
            k=min(3, len(distractors)),
        )
        random.shuffle(options)
        questions.append(
            {
                "index": i,
                "type": qtype,
                "prompt": prompt,
                "options": options,
                "answer": answer,
            }
        )
    return questions


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

    level_obj = db.query(models.HSKLevel).filter_by(level=1).first()
    questions = _build_questions(db, level_obj.id if level_obj else None)

    duel = models.Duel(
        status="active",
        challenge_type=payload.challenge_type,
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
    correct = (payload.answer or "").strip().lower() == (q.get("answer") or "").strip().lower()
    if correct:
        me.score += 10
        me.correct_count += 1
    else:
        me.score += 2
    me.answered += 1
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

    # Opponent (or Buddy) answers the rest at ~70% accuracy.
    total = len((duel.question_data or {}).get("questions", []))
    if opp:
        seed = (opp.score if opp else 0) or 0
        opp.score = round(total * 7)
        opp.answered = total
        if opp.user_id == user.id:
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
        check_achievements(db, user)
        db.commit()

    return _serialize(db, duel, user)