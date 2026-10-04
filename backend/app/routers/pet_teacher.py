import random

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services import ai_client
from app.services.activity import log_activity
from app.services.gamification import (
    add_bond_points,
    check_achievements,
    progress_missions,
    reinforce_mistake,
    user_rank,
)
from app.services import companion_reaction as cr
from app.services import sentence_check
from app.services.localization import load_translations, tr

router = APIRouter(prefix="/api/pet-teacher", tags=["pet-teacher"])

# The cases' explanation keywords are English and Chinese. Offline (no model
# to read the explanation) a learner writing in Russian or Tajik could never
# match them, so the common grammar terms carry their RU/TG equivalents.
_KEYWORD_SYNONYMS = {
    "adjective": ("прилагательн", "сифат"),
    "measure word": ("счётн", "счетн", "классификатор", "калимаи ҳисоб", "ҳисобӣ"),
    "word order": ("порядок слов", "тартиби калима"),
    "question word": ("вопросительн", "калимаи саволӣ"),
    "habitual": ("привычк", "регулярн", "каждый день", "одат", "ҳар рӯз"),
    "before verb": ("перед глагол", "пеш аз феъл"),
    "cause then result": ("причин", "сабаб"),
}


def _keywords(keywords: list[str] | None) -> list[str]:
    out = list(keywords or [])
    for k in keywords or []:
        out.extend(_KEYWORD_SYNONYMS.get(k.lower(), ()))
    return out


@router.get("/lesson", response_model=schemas.PetTeacherCaseResponse)
def get_lesson(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    """The animal makes a deliberate mistake at (or below) the learner's
    current HSK level. Prefers a case not yet taught, so the loop keeps
    introducing new rules instead of repeating the same one forever."""
    level, _mastery = user_rank(db, user)
    taught_ids = {t.case_id for t in user.taught_facts}

    cases = (
        db.query(models.PetTeacherCase)
        .join(models.HSKLevel, models.PetTeacherCase.hsk_level_id == models.HSKLevel.id)
        .filter(models.HSKLevel.level <= level)
        .all()
    )
    if not cases:
        # Nothing at or below the learner's level yet: the easiest cases,
        # not every case (answer_lesson accepts the same reach).
        lowest = (
            db.query(models.HSKLevel.level)
            .join(models.PetTeacherCase, models.PetTeacherCase.hsk_level_id == models.HSKLevel.id)
            .order_by(models.HSKLevel.level)
            .first()
        )
        if lowest:
            cases = (
                db.query(models.PetTeacherCase)
                .join(models.HSKLevel, models.PetTeacherCase.hsk_level_id == models.HSKLevel.id)
                .filter(models.HSKLevel.level == lowest[0])
                .all()
            )
    if not cases:
        raise HTTPException(status_code=404, detail="No Pet Teacher content available yet")

    untaught = [c for c in cases if c.id not in taught_ids]
    pool = untaught or cases
    case = random.choice(pool)

    item = schemas.PetTeacherCaseResponse.model_validate(case)
    item.already_taught = case.id in taught_ids
    item.taught_count = len(taught_ids)
    case_tr = load_translations(db, "pet_teacher_case", [str(case.id)], locale)
    item.hint = tr(case_tr, case.id, "hint", item.hint)
    return item


@router.post("/lesson/{case_id}/answer", response_model=schemas.PetTeacherResultResponse)
def answer_lesson(
    case_id: int,
    payload: schemas.PetTeacherAnswerRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    case = db.get(models.PetTeacherCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    # GET /lesson only hands out cases at or below the learner's level; an
    # answer to a higher one is refused the same way, not taught.
    level, _mastery = user_rank(db, user)
    lowest = (
        db.query(models.HSKLevel.level)
        .join(models.PetTeacherCase, models.PetTeacherCase.hsk_level_id == models.HSKLevel.id)
        .order_by(models.HSKLevel.level)
        .first()
    )
    # Same reach as GET /lesson, including its "nothing at your level yet"
    # fallback to the easiest cases.
    allowed = max(level, lowest[0] if lowest else level)
    case_level = db.get(models.HSKLevel, case.hsk_level_id)
    if case_level is not None and case_level.level > allowed:
        raise HTTPException(status_code=403, detail="This case is above your current HSK level")

    case_tr = load_translations(db, "pet_teacher_case", [str(case.id)], locale)
    mistake_summary = tr(case_tr, case.id, "mistake_summary", case.mistake_summary)

    # The correction is graded by meaning and grammar, not as one exact
    # string (see services/sentence_check.py for the bug this replaces).
    check = sentence_check.check(payload.correction, case.correct_sentence, wrong=case.wrong_sentence)
    judge_feedback = ""
    if not check["final"]:
        judged = ai_client.judge_sentence(
            payload.correction, case.correct_sentence,
            f"Correct the grammar mistake in: {case.wrong_sentence}", locale, wrong=case.wrong_sentence,
        )
        if judged:
            check["source"] = "ai"
            check["category"] = judged["category"]
            check["verdict"] = {"correct": "correct", "alternative": "acceptable",
                                "typo": "close"}.get(judged["category"], "incorrect")
            judge_feedback = judged["feedback"]
    correct_fix = check["verdict"] in ("correct", "acceptable")
    verdict = ai_client.evaluate_pet_teacher_explanation(
        mistake_summary or "", payload.explanation, _keywords(case.explanation_keywords),
        wrong_sentence=case.wrong_sentence, correct_sentence=case.correct_sentence,
        correction=payload.correction, correction_ok=correct_fix, locale=locale,
    )
    understood = verdict["understood"]
    success = correct_fix and understood
    if success:
        outcome = "success"
    elif correct_fix:
        # The sentence is right; only the "why" is missing. This used to be
        # shown as a red failure with the learner's own sentence offered as
        # the "correct" one.
        outcome = "fixed_needs_explanation"
    elif check["verdict"] == "close":
        outcome = "close"
    else:
        outcome = "incorrect"

    first_time = False
    if success:
        already = (
            db.query(models.UserTaughtFact)
            .filter_by(user_id=user.id, case_id=case.id)
            .first()
        )
        if already is None:
            first_time = True
            db.add(models.UserTaughtFact(user_id=user.id, case_id=case.id))
            # Only a newly taught fact earns bond points and moves "teach"
            # missions: re-submitting a case already solved (its answer is
            # known) used to count each time -- a dozen repeats reached bond
            # level 3 and its achievement.
            add_bond_points(user, points=5)
            progress_missions(db, user, "teach")
        if case.grammar_topic_id:
            topic = db.get(models.GrammarTopic, case.grammar_topic_id)
            if topic:
                reinforce_mistake(db, user, "grammar", topic.title)
    log_activity(db, user, "pet_teacher_answer")
    db.commit()

    taught_count = db.query(models.UserTaughtFact).filter_by(user_id=user.id).count()
    newly = check_achievements(db, user)

    ui_tr = load_translations(db, "ui_string", ["pet_teacher"], locale)
    # Feedback on the explanation only once the sentence itself is right;
    # for a wrong sentence the model's words about the sentence come first.
    feedback = verdict["feedback"] if correct_fix else (judge_feedback or "")
    if not feedback:
        if success:
            feedback = tr(ui_tr, "pet_teacher", "success",
                           "Perfect — you fixed it and explained why. Your companion just learned something!")
        elif not correct_fix:
            feedback = tr(ui_tr, "pet_teacher", "wrong_correction",
                           "The correction isn't quite right yet — look at the sentence again.")
        else:
            feedback = tr(ui_tr, "pet_teacher", "needs_more_explanation",
                           "The correction is right, but explain the rule a bit more so it really sticks.")
    unlocked = [a.title for a in newly]

    topic = _topic_for(db, case, check["issues"])
    topic_tr = load_translations(db, "grammar_topic", [str(topic.id)], locale) if topic else {}

    return schemas.PetTeacherResultResponse(
        correct_fix=correct_fix,
        understood=understood,
        success=success,
        outcome=outcome,
        correction_verdict=check["verdict"],
        correction_category=check["category"],
        issues=[i["code"] for i in check["issues"] if i["severity"] == "error"] if not correct_fix else [],
        restated=verdict.get("restated", False),
        # The model sentence is shown only when the learner's isn't right --
        # never their own sentence back to them as "the correct one".
        correct_sentence=case.correct_sentence,
        show_correct_sentence=not correct_fix,
        mistake_summary=mistake_summary,
        feedback=feedback,
        unlocked=unlocked,
        taught_count=taught_count,
        grammar_topic_id=topic.id if topic else None,
        grammar_topic_title=tr(topic_tr, topic.id, "title", topic.title) if topic else None,
        # The permanent companion reacts to the real outcome.
        reaction=cr.teach_reaction(user, outcome=outcome, first_time=first_time),
    )


def _topic_for(db: Session, case: models.PetTeacherCase, issues: list[dict]) -> models.GrammarTopic | None:
    """The grammar page that explains this case: the topic of the error the
    learner's sentence still has, else the case's own topic."""
    for issue in issues:
        if issue.get("topic"):
            row = db.query(models.GrammarTopic).filter_by(title=issue["topic"]).order_by(models.GrammarTopic.id).first()
            if row:
                return row
    return db.get(models.GrammarTopic, case.grammar_topic_id) if case.grammar_topic_id else None
