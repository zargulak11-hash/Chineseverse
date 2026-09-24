from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services.activity import log_activity
from app.services.gamification import add_bond_points, check_achievements, generate_daily_quests
from app.services.localization import load_translations, tr

router = APIRouter(prefix="/api/quests", tags=["quests"])


def _localize_quest(quest: models.DailyQuest, translations: dict) -> schemas.QuestResponse:
    # Title/description/flavor are baked into the row at creation from a
    # fixed template (QUEST_TEMPLATES), so they're looked up by quest_type
    # -- the template's own stable key -- not by the row's own id, which
    # would need a fresh translation for every quest ever generated.
    out = schemas.QuestResponse.model_validate(quest)
    key = quest.quest_type
    out.title = tr(translations, key, "title", out.title)
    out.description = tr(translations, key, "description", out.description)
    out.flavor = tr(translations, key, "flavor", out.flavor)
    return out


@router.get("/today", response_model=list[schemas.QuestResponse])
def today_quests(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    quests = generate_daily_quests(db, user)
    translations = load_translations(db, "quest_template", [q.quest_type for q in quests], locale)
    return [_localize_quest(q, translations) for q in quests]


@router.post("/{quest_id}/claim", response_model=schemas.QuestResponse)
def claim_quest(
    quest_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
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
    translations = load_translations(db, "quest_template", [quest.quest_type], locale)
    return _localize_quest(quest, translations)