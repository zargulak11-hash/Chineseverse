from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services.gamification import animal_bias, check_achievements
from app.services.localization import load_translations, tr

router = APIRouter(prefix="/api/missions", tags=["missions"])


def _localize_mission(mission: models.Mission, translations: dict) -> schemas.MissionResponse:
    out = schemas.MissionResponse.model_validate(mission)
    key = str(mission.id)
    out.title = tr(translations, key, "title", out.title)
    out.objective = tr(translations, key, "objective", out.objective)
    return out


def _link(db: Session, user: models.User, mission: models.Mission) -> models.UserMission:
    entry = (
        db.query(models.UserMission)
        .filter_by(user_id=user.id, mission_id=mission.id)
        .first()
    )
    if entry is None:
        entry = models.UserMission(user_id=user.id, mission_id=mission.id, status="available")
        db.add(entry)
        db.flush()
    return entry


@router.get("", response_model=list[schemas.UserMissionResponse])
def list_missions(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    missions = db.query(models.Mission).order_by(models.Mission.sort_order).all()
    # Surface missions matching the user's animal's preferred mechanic first
    # (e.g. Wolf's "missions, hard challenges, streaks" -> duel/world kinds),
    # without hiding or reordering anything beyond that front-loading.
    preferred_kinds = animal_bias(user)["mission_kinds"]
    if preferred_kinds:
        missions = sorted(missions, key=lambda m: (0 if m.kind in preferred_kinds else 1, m.sort_order))
    translations = load_translations(db, "mission", [str(m.id) for m in missions], locale)
    out = []
    for mission in missions:
        entry = _link(db, user, mission)
        out.append(
            schemas.UserMissionResponse(
                id=entry.id,
                mission=_localize_mission(mission, translations),
                status=entry.status,
                progress=entry.progress,
                completed_at=entry.completed_at,
            )
        )
    db.commit()
    return out


@router.post("/{mission_id}/accept", response_model=schemas.UserMissionResponse)
def accept_mission(
    mission_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    mission = db.get(models.Mission, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    entry = _link(db, user, mission)
    if mission.scenario is None and entry.status == "available":
        entry.status = "active"
    db.commit()
    translations = load_translations(db, "mission", [str(mission.id)], locale)
    return schemas.UserMissionResponse(
        id=entry.id,
        mission=_localize_mission(mission, translations),
        status=entry.status,
        progress=entry.progress,
        completed_at=entry.completed_at,
    )


@router.post("/{mission_id}/progress", response_model=schemas.UserMissionResponse)
def progress_mission(
    mission_id: int,
    payload: schemas.MissionProgressUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    mission = db.get(models.Mission, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    entry = _link(db, user, mission)

    if payload.status == "completed":
        entry.status = "completed"
        entry.completed_at = datetime.utcnow()
        entry.progress = mission.target_count
        check_achievements(db, user)
    else:
        if payload.delta:
            entry.progress = min(mission.target_count, entry.progress + payload.delta)
        if entry.progress >= mission.target_count:
            entry.status = "completed"
            entry.completed_at = datetime.utcnow()
            check_achievements(db, user)

    db.commit()
    translations = load_translations(db, "mission", [str(mission.id)], locale)
    return schemas.UserMissionResponse(
        id=entry.id,
        mission=_localize_mission(mission, translations),
        status=entry.status,
        progress=entry.progress,
        completed_at=entry.completed_at,
    )