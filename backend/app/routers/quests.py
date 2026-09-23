from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.services.activity import log_activity
from app.services.gamification import add_bond_points, check_achievements, generate_daily_quests

router = APIRouter(prefix="/api/quests", tags=["quests"])


@router.get("/today", response_model=list[schemas.QuestResponse])
def today_quests(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return generate_daily_quests(db, user)


@router.post("/{quest_id}/claim", response_model=schemas.QuestResponse)
def claim_quest(
    quest_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quest = (
        db.query(models.DailyQuest)
        .filter(models.DailyQuest.id == quest_id, models.DailyQuest.user_id == user.id)
        .first()
    )
    if quest is None:
        raise HTTPException(status_code=404, detail="Quest not found")
    if not quest.completed:
        raise HTTPException(status_code=409, detail="Quest not completed yet")
    if quest.claimed:
        raise HTTPException(status_code=409, detail="Quest already claimed")

    quest.claimed = True
    user.total_xp += quest.reward_xp
    user.coins += quest.reward_coins
    add_bond_points(user, points=2)
    check_achievements(db, user)
    log_activity(db, user, "quest_claim")
    db.commit()
    db.refresh(quest)
    return quest