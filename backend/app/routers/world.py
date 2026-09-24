from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, get_locale, get_user_or_none
from app.services import ai_client
from app.services.activity import log_activity
from app.services.gamification import (
    ensure_bond,
    ensure_user_skills,
    location_status,
    progress_missions,
    progress_quests,
    record_mistake,
    reinforce_mistake,
    scenario_is_unlocked,
    user_rank,
)
from app.services.localization import load_translations, tr

router = APIRouter(prefix="/api/world", tags=["world"])

_computed_status = location_status


def _localize_npc(npc: models.NPC, translations: dict) -> schemas.NPCBrief:
    out = schemas.NPCBrief.model_validate(npc)
    key = str(npc.id)
    # `name` stays as-authored (a Chinese-flavored character name like 奶奶,
    # not a UI string) -- role/title/description are the English framing
    # around that character and do follow the selected locale.
    out.role = tr(translations, key, "role", out.role)
    out.title = tr(translations, key, "title", out.title)
    out.description = tr(translations, key, "description", out.description)
    return out


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


@router.get("/locations", response_model=list[schemas.LocationResponse])
def list_locations(
    user: models.User | None = Depends(get_user_or_none),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    if user:
        ensure_user_skills(db, user)
        current, _ = user_rank(db, user)
    else:
        current = 1
    locations = db.query(models.Location).order_by(models.Location.unlock_level).all()
    translations = load_translations(db, "location", [str(l.id) for l in locations], locale)
    out = []
    for loc in locations:
        item = schemas.LocationResponse.model_validate(loc)
        item.status = _computed_status(loc, current)
        item.name = tr(translations, loc.id, "name", item.name)
        item.description = tr(translations, loc.id, "description", item.description)
        out.append(item)
    return out


@router.get("/locations/{slug}", response_model=schemas.LocationDetailResponse)
def location_detail(
    slug: str,
    user: models.User | None = Depends(get_user_or_none),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    loc = db.query(models.Location).filter_by(slug=slug).first()
    if loc is None:
        raise HTTPException(status_code=404, detail="Location not found")
    current = 1
    if user:
        ensure_bond(db, user)
        current, _ = user_rank(db, user)

    status = _computed_status(loc, current)
    detail = schemas.LocationDetailResponse.model_validate(loc)
    detail.status = status
    # Locked/next locations are visible on the map (so the player can see
    # what's coming) but their people and conversations aren't playable yet
    # — matching the unlock status shown, not just a cosmetic badge.
    if status == "unlocked":
        loc_tr = load_translations(db, "location", [str(loc.id)], locale)
        detail.name = tr(loc_tr, loc.id, "name", detail.name)
        detail.description = tr(loc_tr, loc.id, "description", detail.description)

        npc_ids = [str(n.id) for n in loc.npcs]
        scenario_ids = [str(s.id) for s in loc.scenarios]
        dialogue_ids = [str(d.id) for s in loc.scenarios for d in s.dialogues]
        choice_ids = [str(c.id) for s in loc.scenarios for d in s.dialogues for c in d.choices]
        npc_tr = load_translations(db, "npc", npc_ids, locale)
        scenario_tr = load_translations(db, "scenario", scenario_ids, locale)
        dialogue_tr = load_translations(db, "dialogue", dialogue_ids, locale)
        choice_tr = load_translations(db, "dialogue_choice", choice_ids, locale)

        detail.npcs = [_localize_npc(n, npc_tr) for n in loc.npcs]
        detail.scenarios = [
            _localize_scenario(s, scenario_tr, npc_tr, dialogue_tr, choice_tr) for s in loc.scenarios
        ]
    else:
        detail.npcs = []
        detail.scenarios = []
    return detail


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
    progress_quests(db, user, "case" if solved else "case")
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
        "xp_reward": 50 if solved else 5,
    }