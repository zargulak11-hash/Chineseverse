from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, get_user_or_none
from app.services.gamification import ensure_bond, ensure_user_skills, progress_quests, user_rank

router = APIRouter(prefix="/api/world", tags=["world"])


def _computed_status(location: models.Location, current: int) -> str:
    if location.unlock_level <= current:
        return "unlocked"
    if location.unlock_level == current + 1:
        return "next"
    return "locked"


@router.get("/locations", response_model=list[schemas.LocationResponse])
def list_locations(
    user: models.User | None = Depends(get_user_or_none),
    db: Session = Depends(get_db),
):
    if user:
        ensure_user_skills(db, user)
        _, current = user_rank(db, user)
    else:
        current = 1
    out = []
    for loc in db.query(models.Location).order_by(models.Location.unlock_level).all():
        item = schemas.LocationResponse.model_validate(loc)
        item.status = _computed_status(loc, current)
        out.append(item)
    return out


@router.get("/locations/{slug}", response_model=schemas.LocationDetailResponse)
def location_detail(
    slug: str,
    user: models.User | None = Depends(get_user_or_none),
    db: Session = Depends(get_db),
):
    loc = db.query(models.Location).filter_by(slug=slug).first()
    if loc is None:
        raise HTTPException(status_code=404, detail="Location not found")
    current = 1
    if user:
        ensure_bond(db, user)
        _, current = user_rank(db, user)

    detail = schemas.LocationDetailResponse.model_validate(loc)
    detail.status = _computed_status(loc, current)
    detail.npcs = [schemas.NPCBrief.model_validate(n) for n in loc.npcs]
    detail.scenarios = [
        schemas.ScenarioResponse.model_validate(s) for s in loc.scenarios
    ]
    return detail


@router.get("/scenarios", response_model=list[schemas.ScenarioResponse])
def list_scenarios(
    location_slug: str | None = None,
    user: models.User | None = Depends(get_user_or_none),
    db: Session = Depends(get_db),
):
    query = db.query(models.Scenario)
    if location_slug:
        query = query.join(models.Location, models.Scenario.location_id == models.Location.id)
        query = query.filter(models.Location.slug == location_slug)
    return query.order_by(models.Scenario.order_index).all()


@router.get("/scenarios/{slug}", response_model=schemas.ScenarioResponse)
def scenario_detail(
    slug: str,
    user: models.User | None = Depends(get_user_or_none),
    db: Session = Depends(get_db),
):
    scenario = db.query(models.Scenario).filter_by(slug=slug).first()
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    out = schemas.ScenarioResponse.model_validate(scenario)
    dialogues = sorted(scenario.dialogues, key=lambda d: d.turn_index)
    serialized = []
    for d in dialogues:
        item = schemas.DialogueResponse.model_validate(d)
        item.reactions = {
            "correct": d.reaction_correct,
            "incorrect": d.reaction_incorrect,
        }
        serialized.append(item)
    out.dialogues = serialized
    return out


@router.post("/scenarios/{slug}/solve")
def solve_case(
    slug: str,
    payload: schemas.CaseSolveRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scenario = db.query(models.Scenario).filter_by(slug=slug).first()
    if scenario is None or not scenario.is_case:
        raise HTTPException(status_code=404, detail="Case scenario not found")
    case_data = scenario.case_data or {}
    solution_kws = case_data.get("solution_kws", [])
    conclusion = (payload.conclusion or "").lower()
    solved = any(kw.lower() in conclusion for kw in solution_kws)
    progress_quests(db, user, "case" if solved else "case")
    return {
        "solved": solved,
        "correct_answer": case_data.get("hint", ""),
        "feedback": "You cracked it!" if solved else "Keep investigating the clues.",
        "xp_reward": 50 if solved else 5,
    }