from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services.gamification import ensure_user_skills, user_rank
from app.services.hsk_band import split_thirds
from app.services.localization import load_translations, tr

router = APIRouter(prefix="/api/hsk", tags=["hsk"])


@router.get("/levels", response_model=list[schemas.HSKLevelResponse])
def list_levels(db: Session = Depends(get_db), locale: str = Depends(get_locale)):
    levels = db.query(models.HSKLevel).order_by(models.HSKLevel.level).all()
    translations = load_translations(db, "hsk_level", [str(l.id) for l in levels], locale)
    out = []
    for lvl in levels:
        item = schemas.HSKLevelResponse.model_validate(lvl)
        item.title = tr(translations, lvl.id, "title", item.title)
        item.description = tr(translations, lvl.id, "description", item.description)
        out.append(item)
    return out


@router.get("/skills", response_model=list[schemas.SkillResponse])
def list_skills(db: Session = Depends(get_db), locale: str = Depends(get_locale)):
    skills = db.query(models.Skill).order_by(models.Skill.id).all()
    translations = load_translations(db, "skill", [str(s.id) for s in skills], locale)
    out = []
    for skill in skills:
        item = schemas.SkillResponse.model_validate(skill)
        item.name = tr(translations, skill.id, "name", item.name)
        item.description = tr(translations, skill.id, "description", item.description)
        out.append(item)
    return out


def _mastered_count(db, model, id_field, hsk_level_id, mastered_ids, id_subset=None):
    q = db.query(model).filter(
        id_field == hsk_level_id,
        model.id.in_(list(mastered_ids) or [0]),
    )
    if id_subset is not None:
        q = q.filter(model.id.in_(id_subset or [0]))
    return q.count()


def _total_count(db, model, id_field, hsk_level_id, id_subset=None):
    q = db.query(model).filter(id_field == hsk_level_id)
    if id_subset is not None:
        q = q.filter(model.id.in_(id_subset or [0]))
    return q.count()


def _level_progress(db, user, lvl, mastered_vocab_ids, mastered_hanzi_ids, mastered_grammar_ids,
                     current_level, label_level=None, vocab_subset=None, hanzi_subset=None,
                     grammar_subset=None, is_advanced_stage=False):
    vocab_total = _total_count(db, models.VocabularyWord, models.VocabularyWord.hsk_level_id, lvl.id, vocab_subset)
    vocab_mastered = _mastered_count(db, models.VocabularyWord, models.VocabularyWord.hsk_level_id, lvl.id, mastered_vocab_ids, vocab_subset)
    hanzi_total = _total_count(db, models.Hanzi, models.Hanzi.hsk_level_id, lvl.id, hanzi_subset)
    hanzi_mastered = _mastered_count(db, models.Hanzi, models.Hanzi.hsk_level_id, lvl.id, mastered_hanzi_ids, hanzi_subset)
    grammar_total = _total_count(db, models.GrammarTopic, models.GrammarTopic.hsk_level_id, lvl.id, grammar_subset)
    grammar_mastered = _mastered_count(db, models.GrammarTopic, models.GrammarTopic.hsk_level_id, lvl.id, mastered_grammar_ids, grammar_subset)

    completed = (
        db.query(models.Progress)
        .join(models.Lesson, models.Progress.lesson_id == models.Lesson.id)
        .filter(
            models.Progress.user_id == user.id,
            models.Progress.status == "completed",
            models.Lesson.hsk_level_id == lvl.id,
        )
        .count()
    )

    domain_totals = [(vocab_mastered, vocab_total), (hanzi_mastered, hanzi_total), (grammar_mastered, grammar_total)]
    weighted = [(m / t * 100.0) for m, t in domain_totals if t]
    mastery = sum(weighted) / len(weighted) if weighted else 0.0

    display_level = label_level if label_level is not None else lvl.level
    if display_level < current_level:
        status = "unlocked"
    elif display_level == current_level:
        status = "current"
    else:
        status = "locked"
    ready = mastery >= lvl.mastery_to_unlock_next or display_level < current_level

    return schemas.HSKLevelProgress(
        level=display_level, status=status,
        vocab_mastered=vocab_mastered, vocab_total=vocab_total,
        hanzi_mastered=hanzi_mastered, hanzi_total=hanzi_total,
        grammar_mastered=grammar_mastered, grammar_total=grammar_total,
        mastery=round(mastery, 1), lessons_completed=completed,
        ready_for_next=ready, is_advanced_stage=is_advanced_stage,
    )


@router.get("/roadmap", response_model=schemas.HSKRoadmapResponse)
def roadmap(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_user_skills(db, user)
    levels = db.query(models.HSKLevel).order_by(models.HSKLevel.level).all()
    current_level, overall = user_rank(db, user)

    mastered_vocab_ids = {w.word_id for w in user.user_vocabulary if w.status == "mastered"}
    mastered_hanzi_ids = {h.hanzi_id for h in user.user_hanzi if h.status == "mastered"}
    mastered_grammar_ids = {g.topic_id for g in user.user_grammar if g.status == "mastered"}

    results = []
    for lvl in levels:
        if lvl.is_advanced_band:
            # user_rank's level threshold formula only knows about real
            # HSKLevel rows (max = this one band, level 7), so it can never
            # itself return 8 or 9. Once the band is reached, refine which
            # of the 3 real-mastery-based stages counts as "current" from
            # the band's OWN overall mastery -- still real data, not a
            # second fabricated leveling system.
            effective_stage = current_level
            if current_level >= lvl.level:
                band_totals = [
                    (
                        _mastered_count(db, models.VocabularyWord, models.VocabularyWord.hsk_level_id, lvl.id, mastered_vocab_ids),
                        _total_count(db, models.VocabularyWord, models.VocabularyWord.hsk_level_id, lvl.id),
                    ),
                    (
                        _mastered_count(db, models.Hanzi, models.Hanzi.hsk_level_id, lvl.id, mastered_hanzi_ids),
                        _total_count(db, models.Hanzi, models.Hanzi.hsk_level_id, lvl.id),
                    ),
                    (
                        _mastered_count(db, models.GrammarTopic, models.GrammarTopic.hsk_level_id, lvl.id, mastered_grammar_ids),
                        _total_count(db, models.GrammarTopic, models.GrammarTopic.hsk_level_id, lvl.id),
                    ),
                ]
                band_weighted = [(m / t * 100.0) for m, t in band_totals if t]
                band_mastery = sum(band_weighted) / len(band_weighted) if band_weighted else 0.0
                if band_mastery >= 66.7:
                    effective_stage = 9
                elif band_mastery >= 33.3:
                    effective_stage = 8
                else:
                    effective_stage = 7
            # Real HSK 3.0 standard: 7/8/9 share ONE advanced pool. Split
            # that pool's real rows into 3 contiguous thirds so the roadmap
            # can still show three progression stages, without inventing
            # three independent official vocab/hanzi/grammar lists.
            vocab_ids = [w.id for w in db.query(models.VocabularyWord.id).filter_by(hsk_level_id=lvl.id).order_by(models.VocabularyWord.id).all()]
            hanzi_ids = [h.id for h in db.query(models.Hanzi.id).filter_by(hsk_level_id=lvl.id).order_by(models.Hanzi.id).all()]
            grammar_ids = [g.id for g in db.query(models.GrammarTopic.id).filter_by(hsk_level_id=lvl.id).order_by(models.GrammarTopic.id).all()]
            vocab_thirds = split_thirds(vocab_ids)
            hanzi_thirds = split_thirds(hanzi_ids)
            grammar_thirds = split_thirds(grammar_ids)
            for i, stage_level in enumerate((7, 8, 9)):
                results.append(_level_progress(
                    db, user, lvl, mastered_vocab_ids, mastered_hanzi_ids, mastered_grammar_ids,
                    effective_stage, label_level=stage_level,
                    vocab_subset=vocab_thirds[i], hanzi_subset=hanzi_thirds[i], grammar_subset=grammar_thirds[i],
                    is_advanced_stage=True,
                ))
        else:
            results.append(_level_progress(
                db, user, lvl, mastered_vocab_ids, mastered_hanzi_ids, mastered_grammar_ids, current_level,
            ))
    return schemas.HSKRoadmapResponse(
        levels=results, current_level=current_level, overall_mastery=overall
    )