"""/api/missions -- longer goals that advance on their own.

A mission is never progressed by the client: services.gamification
.progress_missions moves it when the real activity happens (a voice turn in
the scenario, a solved case, a won duel, vocabulary reviews, Pet Teacher).
This router lists them and lets a learner accept one; the response says
where the mission is done (`scenario_slug` / kind) so the page can link
there. A mission above the learner's HSK level is locked: it cannot be
accepted and does not advance.

There used to be a POST /{id}/progress that took {"status": "completed"}
or any delta from the browser, so one request completed any mission (and
fired its achievements). It is gone.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services.gamification import animal_bias, user_rank
from app.services.localization import load_translations, tr

router = APIRouter(prefix="/api/missions", tags=["missions"])


def _localize_mission(mission: models.Mission, translations: dict) -> schemas.MissionResponse:
    out = schemas.MissionResponse.model_validate(mission)
    key = str(mission.id)
    out.title = tr(translations, key, "title", out.title)
    out.objective = tr(translations, key, "objective", out.objective)
    if mission.scenario is not None:
        out.scenario_slug = mission.scenario.slug
        out.scenario_type = mission.scenario.scenario_type
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


def _out(entry: models.UserMission, mission: models.Mission, translations: dict, level: int) -> schemas.UserMissionResponse:
    return schemas.UserMissionResponse(
        id=entry.id,
        mission=_localize_mission(mission, translations),
        status=entry.status,
        progress=entry.progress,
        completed_at=entry.completed_at,
        locked=entry.status != "completed" and mission.min_hsk_level > level,
    )


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
    level, _mastery = user_rank(db, user)
    translations = load_translations(db, "mission", [str(m.id) for m in missions], locale)
    out = [_out(_link(db, user, mission), mission, translations, level) for mission in missions]
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
    level, _mastery = user_rank(db, user)
    if mission.min_hsk_level > level:
        raise HTTPException(status_code=403, detail=f"This mission opens at HSK {mission.min_hsk_level}")
    entry = _link(db, user, mission)
    # Accepting used to work only for missions without a scenario, so the
    # button did nothing on the scenario missions (most of them).
    if entry.status == "available":
        entry.status = "active"
    db.commit()
    translations = load_translations(db, "mission", [str(mission.id)], locale)
    return _out(entry, mission, translations, level)
