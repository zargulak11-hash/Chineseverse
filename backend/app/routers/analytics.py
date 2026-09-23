from collections import defaultdict
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.services.activity import SECTION_LABELS

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

HEATMAP_WEEKS = 53
HEATMAP_DAYS = HEATMAP_WEEKS * 7


@router.get("/activity", response_model=schemas.ActivityAnalyticsResponse)
def activity_analytics(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    window_start = today - timedelta(days=HEATMAP_DAYS - 1)

    rows = (
        db.query(
            func.date(models.ActivityEvent.created_at).label("day"),
            models.ActivityEvent.section,
            func.sum(models.ActivityEvent.minutes).label("minutes"),
            func.count(models.ActivityEvent.id).label("actions"),
        )
        .filter(
            models.ActivityEvent.user_id == user.id,
            func.date(models.ActivityEvent.created_at) >= window_start,
        )
        .group_by(func.date(models.ActivityEvent.created_at), models.ActivityEvent.section)
        .all()
    )

    per_day: dict[date, dict[str, float | int]] = defaultdict(lambda: {"minutes": 0.0, "actions": 0})
    per_section: dict[str, float] = defaultdict(float)
    for row in rows:
        day = row.day if isinstance(row.day, date) else datetime.strptime(row.day, "%Y-%m-%d").date()
        per_day[day]["minutes"] += float(row.minutes or 0)
        per_day[day]["actions"] += int(row.actions or 0)
        per_section[row.section] += float(row.minutes or 0)

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

    streak = user.streak or models.UserStreak(user_id=user.id)

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
