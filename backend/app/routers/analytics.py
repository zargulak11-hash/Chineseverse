from collections import defaultdict
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.services.activity import SECTION_LABELS
from app.services.gamification import activity_today, local_date, local_day_start, streak_snapshot
from app.services.recall import TYPED_TYPES
from app.services.srs import SLIP_AFTER, retrievability

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

HEATMAP_WEEKS = 53
HEATMAP_DAYS = HEATMAP_WEEKS * 7


@router.get("/activity", response_model=schemas.ActivityAnalyticsResponse)
def activity_analytics(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # The learner's own calendar, the same days the streak counts: grouping
    # by the stored (UTC) date put a Dushanbe learner's 01:00 session on the
    # day before.
    today = activity_today(user)
    window_start = today - timedelta(days=HEATMAP_DAYS - 1)

    rows = (
        db.query(models.ActivityEvent.created_at, models.ActivityEvent.minutes)
        .filter(
            models.ActivityEvent.user_id == user.id,
            models.ActivityEvent.created_at >= local_day_start(user, window_start),
        )
        .all()
    )

    per_day: dict[date, dict[str, float | int]] = defaultdict(lambda: {"minutes": 0.0, "actions": 0})
    for at, minutes in rows:
        day = local_date(user, at)
        per_day[day]["minutes"] += float(minutes or 0)
        per_day[day]["actions"] += 1

    # All-time total (not windowed) — the "Learning Rhythm" headline number.
    total_minutes = float(
        db.query(func.coalesce(func.sum(models.ActivityEvent.minutes), 0.0))
        .filter(models.ActivityEvent.user_id == user.id)
        .scalar()
        or 0.0
    )
    # All-time section breakdown, not just the heatmap window, so a long-time
    # user's "Time by Section" reflects their whole history.
    section_rows = (
        db.query(models.ActivityEvent.section, func.sum(models.ActivityEvent.minutes))
        .filter(models.ActivityEvent.user_id == user.id)
        .group_by(models.ActivityEvent.section)
        .all()
    )
    sections = []
    for section, minutes in section_rows:
        minutes = float(minutes or 0)
        sections.append(
            schemas.SectionBreakdownResponse(
                section=section,
                label=SECTION_LABELS.get(section, section.replace("_", " ").title()),
                minutes=round(minutes, 1),
                percent=round((minutes / total_minutes * 100) if total_minutes else 0, 1),
            )
        )
    sections.sort(key=lambda s: s.minutes, reverse=True)

    def sum_range(start: date, end: date) -> tuple[float, int]:
        m = a = 0
        for d in range(0, (end - start).days + 1):
            cell = per_day.get(start + timedelta(days=d))
            if cell:
                m += cell["minutes"]
                a += cell["actions"]
        return round(m, 1), int(a)

    today_minutes, today_actions = sum_range(today, today)
    week_minutes, week_actions = sum_range(today - timedelta(days=6), today)
    last_week_minutes, last_week_actions = sum_range(today - timedelta(days=13), today - timedelta(days=7))

    days = []
    best_run = run = 0
    total_actions_year = 0
    d = window_start
    while d <= today:
        cell = per_day.get(d, {"minutes": 0.0, "actions": 0})
        days.append(schemas.ActivityDayResponse(date=d, minutes=round(cell["minutes"], 1), actions=int(cell["actions"])))
        total_actions_year += int(cell["actions"])
        if cell["actions"] > 0:
            run += 1
            best_run = max(best_run, run)
        else:
            run = 0
        d += timedelta(days=1)

    streak = schemas.StreakResponse(**streak_snapshot(user))

    return schemas.ActivityAnalyticsResponse(
        total_minutes=round(total_minutes, 1),
        today_minutes=today_minutes,
        today_actions=today_actions,
        week_minutes=week_minutes,
        week_actions=week_actions,
        last_week_minutes=last_week_minutes,
        last_week_actions=last_week_actions,
        streak=streak,
        best_streak_past_year=best_run,
        total_actions_past_year=total_actions_year,
        sections=sections,
        days=days,
    )


RECALL_WINDOW_DAYS = 30
AT_RISK_BELOW = 0.8  # FSRS-predicted recall under this: likely to be forgotten soon


def _stages(rows, now: datetime) -> dict:
    """Each word/character the learner has met, in exactly one stage:

      learning    met in practice, not yet answered reliably (status new/learning)
      recognised  answered reliably, but only by choosing it -- never produced
                  from memory (times_recalled 0; services/srs.py won't call
                  it mastered)
      recalled    produced from memory at least once, still being reinforced
      mastered    status mastered AND recalled from memory

    plus two readings of the schedule that overlap the stages: `due` (its
    review time has come) and `slipping` (known, and days past it --
    services/srs.is_slipping)."""
    out = {"learning": 0, "recognised": 0, "recalled": 0, "mastered": 0, "due": 0, "slipping": 0}
    # FSRS's own prediction (services/srs.py), only over items that have an
    # FSRS memory -- `tracked` says how many that is, so the average is
    # never read as covering words the scheduler hasn't modelled yet.
    probs: list[float] = []
    for status, recalled, next_review_at, stability, last_reviewed_at in rows:
        if stability is not None and last_reviewed_at is not None:
            probs.append(retrievability((now - last_reviewed_at).total_seconds() / 86400, stability))
        if status in ("reviewing", "mastered") and not recalled:
            out["recognised"] += 1
        elif status == "mastered":
            out["mastered"] += 1
        elif status == "reviewing":
            out["recalled"] += 1
        else:
            out["learning"] += 1
        if next_review_at is not None and next_review_at <= now:
            out["due"] += 1
            if status in ("reviewing", "mastered") and now - next_review_at >= SLIP_AFTER:
                out["slipping"] += 1
    out["met"] = out["learning"] + out["recognised"] + out["recalled"] + out["mastered"]
    out["memory"] = {
        "tracked": len(probs),
        "predicted_recall": round(sum(probs) / len(probs) * 100) if probs else None,
        "at_risk": sum(1 for p in probs if p < AT_RISK_BELOW),
    }
    return out


@router.get("/knowledge")
def knowledge(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """What the learner knows, from their own graded records only: words
    and characters by stage (see _stages), and how their answers from memory
    went in the last RECALL_WINDOW_DAYS (correct of answered -- the
    denominator is always sent, so a small sample reads as one)."""
    now = datetime.utcnow()
    out = {}
    for key, model in (("vocab", models.UserVocabulary), ("hanzi", models.UserHanzi)):
        rows = (db.query(model.status, model.times_recalled, model.next_review_at, model.stability,
                         model.last_reviewed_at)
                .filter(model.user_id == user.id).all())
        out[key] = _stages(rows, now)
    since = now - timedelta(days=RECALL_WINDOW_DAYS)
    answered = correct = 0
    sessions = (db.query(models.PracticeSession.questions, models.PracticeSession.answers)
                .filter(models.PracticeSession.user_id == user.id, models.PracticeSession.created_at >= since).all())
    for questions, answers in sessions:
        for q, a in zip(questions or [], answers or []):
            if a and q.get("type") in TYPED_TYPES:
                answered += 1
                correct += bool(a.get("correct"))
    out["recall"] = {"answered": answered, "correct": correct, "days": RECALL_WINDOW_DAYS}
    return out
