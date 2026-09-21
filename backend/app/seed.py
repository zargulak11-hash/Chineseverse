import logging

from sqlalchemy.orm import Session

from app import models
from app.seed_data import ANIMALS, HSK_LEVELS, SKILLS
from app.seed_learning import GRAMMAR, LESSONS, VOCAB
from app.seed_world import ACHIEVEMENTS, LOCATIONS, MISSIONS, NPCS, SCENARIOS

logger = logging.getLogger(__name__)


def seed_hsk_levels(db: Session) -> None:
    for level, title, desc, total, mastery in HSK_LEVELS:
        if db.query(models.HSKLevel).filter_by(level=level).first():
            continue
        db.add(
            models.HSKLevel(
                level=level, title=title, description=desc,
                total_vocab_target=total, mastery_to_unlock_next=mastery,
            )
        )


def seed_skills(db: Session) -> None:
    for code, name, category, desc in SKILLS:
        if db.query(models.Skill).filter_by(code=code).first():
            continue
        db.add(models.Skill(code=code, name=name, category=category, description=desc))


def seed_gen_animals(db: Session) -> None:
    for (slug, name, species, accent, desc, personality, tone_style, mechanics,
         ability, traits, energy, humor, patience, strictness, catchphrase, chat) in ANIMALS:
        animal = db.query(models.Animal).filter_by(slug=slug).first()
        if animal is None:
            # Pre-V2 rows have NULL slug but a matching unique name.
            animal = db.query(models.Animal).filter_by(name=name).first()
        if animal is None:
            animal = models.Animal(
                slug=slug, name=name, species=species,
                accent_color=accent, description=desc,
                personality=personality, tone_style=tone_style,
                preferred_mechanics=mechanics, special_ability=ability,
            )
            db.add(animal)
            db.flush()
        else:
            animal.slug = animal.slug or slug
            animal.accent_color = animal.accent_color or accent
            animal.personality = animal.personality or personality
            animal.tone_style = animal.tone_style or tone_style
            animal.preferred_mechanics = animal.preferred_mechanics or mechanics
            animal.special_ability = animal.special_ability or ability
        if not db.query(models.AnimalPersonality).filter_by(animal_id=animal.id).first():
            db.add(
                models.AnimalPersonality(
                    animal_id=animal.id, traits=traits,
                    energy=energy, humor=humor, patience=patience,
                    strictness=strictness, catchphrase=catchphrase,
                    chat_style=chat,
                )
            )


def seed_locations(db: Session) -> None:
    for (slug, name, kind, icon, accent, desc,
         unlock, mastery, x, y) in LOCATIONS:
        if db.query(models.Location).filter_by(slug=slug).first():
            continue
        db.add(
            models.Location(
                slug=slug, name=name, kind=kind, icon=icon, accent=accent,
                description=desc, unlock_level=unlock,
                unlock_skill_mastery=mastery, position_x=x, position_y=y,
            )
        )


def seed_npcs(db: Session) -> None:
    db.flush()
    for loc_slug, name, role, title, avatar, desc, personality, speech in NPCS:
        location = db.query(models.Location).filter_by(slug=loc_slug).first()
        if not location:
            continue
        existing = (
            db.query(models.NPC)
            .filter_by(location_id=location.id, name=name)
            .first()
        )
        if existing:
            continue
        db.add(
            models.NPC(
                location_id=location.id, name=name, role=role, title=title,
                avatar_url=avatar, description=desc,
                personality=personality, speech_style=speech,
            )
        )


def _find_npc(db: Session, location_id: int, npc_name: str):
    return (
        db.query(models.NPC)
        .filter_by(location_id=location_id, name=npc_name)
        .first()
    )


def seed_scenarios(db: Session) -> None:
    db.flush()
    for item in SCENARIOS:
        location = db.query(models.Location).filter_by(slug=item["location"]).first()
        if not location:
            logger.warning("seed_scenarios: missing location %s", item["location"])
            continue
        scenario = db.query(models.Scenario).filter_by(slug=item["slug"]).first()
        if not scenario:
            scenario = models.Scenario(
                location_id=location.id,
                slug=item["slug"],
                title=item["title"],
                scenario_type=item["scenario_type"],
                description=item["description"],
                min_hsk_level=item["min_hsk_level"],
                difficulty=item["difficulty"],
                is_case=item["is_case"],
                case_data=item["case_data"],
                requires_voice=item["requires_voice"],
                order_index=item["order_index"],
            )
            db.add(scenario)
            db.flush()

        if item.get("npc"):
            npc = _find_npc(db, location.id, item["npc"])
        else:
            npc = db.query(models.NPC).filter_by(location_id=location.id).first()

        for line in item["dialogues"]:
            dup = (
                db.query(models.Dialogue)
                .filter_by(scenario_id=scenario.id, turn_index=line["turn"])
                .first()
            )
            if dup:
                continue
            db.add(
                models.Dialogue(
                    scenario_id=scenario.id,
                    npc_id=npc.id if npc else None,
                    turn_index=line["turn"],
                    speaker=line["speaker"],
                    text=line.get("text", ""),
                    pinyin=line.get("pinyin"),
                    english=line.get("english"),
                    prompt=line.get("prompt"),
                    expected_keywords=line.get("expected_keywords"),
                    requires_voice=line.get("requires_voice", False),
                    reaction_correct=line.get("reaction_correct"),
                    reaction_incorrect=line.get("reaction_incorrect"),
                )
            )

        for choice in item.get("choices", []):
            dialogue = (
                db.query(models.Dialogue)
                .filter_by(scenario_id=scenario.id, turn_index=choice["turn"])
                .first()
            )
            if not dialogue:
                continue
            dup = db.query(models.DialogueChoice).filter_by(
                dialogue_id=dialogue.id, label=choice["label"]
            ).first()
            if dup:
                continue
            db.add(
                models.DialogueChoice(
                    dialogue_id=dialogue.id,
                    label=choice["label"],
                    response_text=choice["response_text"],
                    is_best=choice["is_best"],
                    feedback=choice["feedback"],
                    next_turn=choice["next_turn"],
                )
            )


def seed_missions(db: Session) -> None:
    db.flush()
    for (slug, kind, title, objective, min_hsk,
         xp, coins, count, scenario_slug) in MISSIONS:
        if db.query(models.Mission).filter_by(slug=slug).first():
            continue
        scenario = None
        if scenario_slug:
            scenario = db.query(models.Scenario).filter_by(slug=scenario_slug).first()
        db.add(
            models.Mission(
                scenario_id=scenario.id if scenario else None,
                slug=slug, title=title, objective=objective, kind=kind,
                min_hsk_level=min_hsk, reward_xp=xp, reward_coins=coins,
                target_count=count,
                sort_order=int(scenario.order_index) if scenario else 0,
            )
        )


def seed_vocabulary(db: Session) -> None:
    db.flush()
    levels = {h.level: h.id for h in db.query(models.HSKLevel).all()}
    for (hsk, simplified, traditional, pinyin, meanings,
         word_type, example, example_pinyin) in VOCAB:
        level_id = levels.get(hsk)
        if not level_id:
            continue
        dup = (
            db.query(models.VocabularyWord)
            .filter_by(hsk_level_id=level_id, simplified=simplified)
            .first()
        )
        if dup:
            continue
        db.add(
            models.VocabularyWord(
                hsk_level_id=level_id, simplified=simplified,
                traditional=traditional, pinyin=pinyin, meanings=meanings,
                word_type=word_type, example=example,
                example_pinyin=example_pinyin,
            )
        )


def seed_grammar(db: Session) -> None:
    db.flush()
    levels = {h.level: h.id for h in db.query(models.HSKLevel).all()}
    for (hsk, title, pattern, explanation, examples, order) in GRAMMAR:
        level_id = levels.get(hsk)
        if not level_id:
            continue
        dup = db.query(models.GrammarTopic).filter_by(
            hsk_level_id=level_id, title=title
        ).first()
        if dup:
            continue
        db.add(
            models.GrammarTopic(
                hsk_level_id=level_id, title=title, pattern=pattern,
                explanation=explanation, examples=examples, order_index=order,
            )
        )


def seed_lessons(db: Session) -> None:
    db.flush()
    levels = {h.level: h.id for h in db.query(models.HSKLevel).all()}
    for (hsk, title, summary, content, lesson_type, order, codes) in LESSONS:
        level_id = levels.get(hsk)
        if not level_id:
            continue
        lesson = db.query(models.Lesson).filter_by(title=title).first()
        if not lesson:
            lesson = models.Lesson(
                hsk_level_id=level_id, title=title, summary=summary,
                content=content, lesson_type=lesson_type, order_index=order,
            )
            db.add(lesson)
            db.flush()
        for code in codes:
            skill = db.query(models.Skill).filter_by(code=code).first()
            if skill and skill not in lesson.skills:
                lesson.skills.append(skill)


def seed_achievements(db: Session) -> None:
    for code, title, desc, icon, category, criteria in ACHIEVEMENTS:
        if db.query(models.Achievement).filter_by(code=code).first():
            continue
        db.add(
            models.Achievement(
                code=code, title=title, description=desc,
                icon=icon, category=category, criteria=criteria,
            )
        )


def seed_all(db: Session) -> None:
    seed_hsk_levels(db)
    seed_skills(db)
    seed_gen_animals(db)
    seed_locations(db)
    seed_npcs(db)
    seed_scenarios(db)
    seed_missions(db)
    seed_vocabulary(db)
    seed_grammar(db)
    seed_lessons(db)
    seed_achievements(db)
    db.commit()
    logger.info("Database seeded.")


def needs_seed(db: Session) -> bool:
    return db.query(models.HSKLevel).count() == 0