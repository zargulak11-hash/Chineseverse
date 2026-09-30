import os
from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.config import settings
from app.crud import delete_user_cascade_safe
from app.database import get_db
from app.deps import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _hsk_level_for_mastery(overall: float, levels: list[int]) -> int:
    """Same threshold rule as services.gamification.user_rank, duplicated
    read-only here rather than reused: user_rank calls ensure_user_skills,
    which creates default UserSkill rows as a side effect — fine for one
    user viewing their own dashboard, but this endpoint would otherwise
    fire that write for every single account in the system just from
    an admin opening the user list."""
    current = 1
    for level in levels:
        if overall >= max(0, (level - 1) * 15):
            current = max(current, level)
    return current


_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}


def _database_info(request: Request) -> schemas.AdminDatabaseInfo:
    """Describe the database THIS API instance is connected to, without
    credentials. Local and production run the same code against different
    databases, so the page must say which one it is showing."""
    host = (request.headers.get("host") or "").rsplit(":", 1)[0].strip("[]").lower()
    if host in _LOCAL_HOSTS:
        environment = "local"
    elif host == "testserver":  # FastAPI TestClient
        environment = "test"
    else:
        environment = "production"
    url = make_url(settings.database_url)
    engine = url.get_backend_name()
    if engine == "sqlite":
        name, db_host = os.path.basename(url.database or "") or None, None
    else:
        name, db_host = url.database, url.host
    return schemas.AdminDatabaseInfo(
        environment=environment, served_by=host or "unknown", engine=engine, name=name, host=db_host,
    )


@router.get("/users", response_model=schemas.AdminUserListResponse)
def list_users(
    request: Request,
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    """Every registered account, read straight from the `users` table of the
    database this API is configured with -- one page at a time, optionally
    filtered by username/email. Read-only: nothing here writes."""
    base = db.query(models.User)
    if q and q.strip():
        like = f"%{q.strip().lower()}%"
        base = base.filter(or_(func.lower(models.User.username).like(like), func.lower(models.User.email).like(like)))
    total = base.count()

    # animal is the user's PERMANENT main companion, set once during
    # onboarding via POST /api/me/animal (see app.routers.me.choose_animal)
    # and never touched by the ephemeral, per-session Daily Voice Companion
    # (app.routers.voice picks an animal_id per request and never writes it
    # to user.animal_id/UserAnimal — see that router's own comments).
    # joinedload avoids one extra query per user for the whole list.
    users = (
        base.options(joinedload(models.User.animal))
        .order_by(models.User.id)
        .offset(offset)
        .limit(limit)
        .all()
    )
    ids = [u.id for u in users] or [0]

    mastery_by_user = dict(
        db.query(models.UserSkill.user_id, func.avg(models.UserSkill.mastery))
        .filter(models.UserSkill.user_id.in_(ids))
        .group_by(models.UserSkill.user_id)
        .all()
    )
    streaks = {
        s.user_id: s
        for s in db.query(models.UserStreak).filter(models.UserStreak.user_id.in_(ids))
    }
    last_event = dict(
        db.query(models.ActivityEvent.user_id, func.max(models.ActivityEvent.created_at))
        .filter(models.ActivityEvent.user_id.in_(ids))
        .group_by(models.ActivityEvent.user_id)
        .all()
    )
    hsk_levels = sorted({lvl.level for lvl in db.query(models.HSKLevel).all()})

    summaries = []
    for u in users:
        overall = mastery_by_user.get(u.id)
        streak = streaks.get(u.id)
        last = last_event.get(u.id)
        if last is None and streak is not None and streak.last_active_date:
            last = datetime.combine(streak.last_active_date, time.min)
        summaries.append(
            schemas.AdminUserSummary(
                id=u.id,
                username=u.username,
                email=u.email,
                is_active=bool(u.is_active),
                is_admin=u.is_admin,
                created_at=u.created_at,
                total_xp=u.total_xp,
                coins=u.coins,
                hsk_level=_hsk_level_for_mastery(overall, hsk_levels) if overall is not None else None,
                mastery=round(overall, 1) if overall is not None else None,
                current_streak=streak.current_streak if streak is not None else None,
                companion_slug=u.animal.slug if u.animal is not None else None,
                companion_name=u.animal.name if u.animal is not None else None,
                google_sub=u.google_sub,
                auth_method="google" if u.google_sub else "password",
                last_activity_at=last,
            )
        )

    total_users = db.query(models.User).count()
    admin_count = db.query(models.User).filter(models.User.is_admin.is_(True)).count()
    return schemas.AdminUserListResponse(
        total=total,
        users=summaries,
        total_users=total_users,
        admin_count=admin_count,
        regular_count=total_users - admin_count,
        limit=limit,
        offset=offset,
        database=_database_info(request),
    )


@router.get("/dashboard", response_model=schemas.AdminDashboardResponse)
def admin_dashboard(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    return schemas.AdminDashboardResponse(total_users=db.query(models.User).count())


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    if user_id == admin.id:
        raise HTTPException(
            status_code=400, detail="You cannot delete your own admin account"
        )
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    delete_user_cascade_safe(db, user)
