from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, get_locale, get_user_or_none
from app.services import ai_client
from app.services.activity import log_activity
from app.services.gamification import (
    check_achievements,
    progress_missions,
    progress_quests,
    record_mistake,
    reinforce_mistake,
    scenario_is_unlocked,
)
from app.services.localization import load_translations, tr

router = APIRouter(prefix="/api/world", tags=["world"])

# The old World map endpoints (/locations, /locations/{slug}) are gone: the
# living world on /real-chinese reads GET /api/real-life/world. The voice
# talks and detective cases below still live here and are opened from it.


def _localize_scenario(
    scenario: models.Scenario, scenario_tr: dict, npc_tr: dict, dialogue_tr: dict, choice_tr: dict
) -> schemas.ScenarioResponse:
    out = schemas.ScenarioResponse.model_validate(scenario)
    skey = str(scenario.id)
    out.title = tr(scenario_tr, skey, "title", out.title)
    out.description = tr(scenario_tr, skey, "description", out.description)
    dialogues = sorted(scenario.dialogues, key=lambda d: d.turn_index)
    serialized = []
    for d in dialogues:
        item = schemas.DialogueResponse.model_validate(d)
        item.reactions = {"correct": d.reaction_correct, "incorrect": d.reaction_incorrect}
        dkey = str(d.id)
        # text/pinyin (the actual Chinese being taught) are never touched;
        # english/prompt are explanation/instruction and follow the locale.
        item.english = tr(dialogue_tr, dkey, "english", item.english)
        item.prompt = tr(dialogue_tr, dkey, "prompt", item.prompt)
        for choice in item.choices:
            ckey = str(choice.id)
            choice.feedback = tr(choice_tr, ckey, "feedback", choice.feedback)
        serialized.append(item)
    out.dialogues = serialized
    return out


def _scenarios_translations(db: Session, scenarios: list[models.Scenario], locale: str):
    scenario_ids = [str(s.id) for s in scenarios]
    npc_ids = [str(d.npc_id) for s in scenarios for d in s.dialogues if d.npc_id]
    dialogue_ids = [str(d.id) for s in scenarios for d in s.dialogues]
    choice_ids = [str(c.id) for s in scenarios for d in s.dialogues for c in d.choices]
    return (
        load_translations(db, "scenario", scenario_ids, locale),
        load_translations(db, "npc", npc_ids, locale),
        load_translations(db, "dialogue", dialogue_ids, locale),
        load_translations(db, "dialogue_choice", choice_ids, locale),
    )


@router.get("/scenarios", response_model=list[schemas.ScenarioResponse])
def list_scenarios(
    location_slug: str | None = None,
    user: models.User | None = Depends(get_user_or_none),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    query = db.query(models.Scenario)
    if location_slug:
        query = query.join(models.Location, models.Scenario.location_id == models.Location.id)
        query = query.filter(models.Location.slug == location_slug)
    scenarios = query.order_by(models.Scenario.order_index).all()
    scenario_tr, npc_tr, dialogue_tr, choice_tr = _scenarios_translations(db, scenarios, locale)
    return [_localize_scenario(s, scenario_tr, npc_tr, dialogue_tr, choice_tr) for s in scenarios]


@router.get("/scenarios/{slug}", response_model=schemas.ScenarioResponse)
def scenario_detail(
    slug: str,
    user: models.User | None = Depends(get_user_or_none),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    scenario = db.query(models.Scenario).filter_by(slug=slug).first()
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    if not scenario_is_unlocked(db, user, scenario):
        raise HTTPException(status_code=403, detail="This location isn't unlocked yet")

    scenario_tr, npc_tr, dialogue_tr, choice_tr = _scenarios_translations(db, [scenario], locale)
    return _localize_scenario(scenario, scenario_tr, npc_tr, dialogue_tr, choice_tr)


@router.post("/scenarios/{slug}/solve")
def solve_case(
    slug: str,
    payload: schemas.CaseSolveRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    scenario = db.query(models.Scenario).filter_by(slug=slug).first()
    if scenario is None or not scenario.is_case:
        raise HTTPException(status_code=404, detail="Case scenario not found")
    if not scenario_is_unlocked(db, user, scenario):
        raise HTTPException(status_code=403, detail="This location isn't unlocked yet")
    case_data = scenario.case_data or {}
    solution_kws = case_data.get("solution_kws", [])
    verdict = ai_client.evaluate_case_solution(
        scenario.description or scenario.title,
        payload.conclusion or "",
        solution_kws,
        case_data.get("hint", ""),
    )
    solved = verdict["solved"]
    progress_quests(db, user, "case")
    if solved:
        progress_missions(db, user, "case", scenario_id=scenario.id)
        reinforce_mistake(db, user, "grammar", scenario.slug)
    else:
        record_mistake(
            db, user, "grammar", scenario.slug,
            question_text=case_data.get("prompt") or scenario.title,
            answer_given=payload.conclusion,
            correct_answer=case_data.get("hint", ""),
        )
    log_activity(db, user, "case_solve")
    db.commit()
    check_achievements(db, user)  # a solved case can complete a mission

    scenario_tr = load_translations(db, "scenario", [str(scenario.id)], locale)
    hint = tr(scenario_tr, scenario.id, "hint", case_data.get("hint", ""))
    ui_tr = load_translations(db, "ui_string", ["case_solve"], locale)
    fallback_feedback = tr(
        ui_tr, "case_solve",
        "solved_feedback" if solved else "unsolved_feedback",
        "You cracked it!" if solved else "Keep investigating the clues.",
    )
    return {
        "solved": solved,
        "correct_answer": hint,
        "feedback": verdict["feedback"] or fallback_feedback,
        # (An "xp_reward" of 50/5 used to be reported here although no XP was
        # ever granted for it; the case's real reward is its mission's.)
    }