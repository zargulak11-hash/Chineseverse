from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
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


@router.get("/users", response_model=schemas.AdminUserListResponse)
def list_users(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    # animal is the user's PERMANENT main companion, set once during
    # onboarding via POST /api/me/animal (see app.routers.me.choose_animal)
    # and never touched by the ephemeral, per-session Daily Voice Companion
    # (app.routers.voice picks an animal_id per request and never writes it
    # to user.animal_id/UserAnimal — see that router's own comments).
    # joinedload avoids one extra query per user for the whole list.
    users = (
        db.query(models.User)
        .options(joinedload(models.User.animal))
        .order_by(models.User.id)
        .all()
    )

    mastery_by_user = dict(
        db.query(models.UserSkill.user_id, func.avg(models.UserSkill.mastery))
        .group_by(models.UserSkill.user_id)
        .all()
    )
    streak_by_user = dict(
        db.query(models.UserStreak.user_id, models.UserStreak.current_streak).all()
    )
    hsk_levels = sorted({lvl.level for lvl in db.query(models.HSKLevel).all()})

    summaries = []
    for u in users:
        overall = mastery_by_user.get(u.id)
        summaries.append(
            schemas.AdminUserSummary(
                id=u.id,
                username=u.username,
                email=u.email,
                is_active=u.is_active,
                is_admin=u.is_admin,
                created_at=u.created_at,
                total_xp=u.total_xp,
                coins=u.coins,
                hsk_level=_hsk_level_for_mastery(overall, hsk_levels) if overall is not None else None,
                mastery=round(overall, 1) if overall is not None else None,
                current_streak=streak_by_user.get(u.id),
                companion_slug=u.animal.slug if u.animal is not None else None,
                companion_name=u.animal.name if u.animal is not None else None,
            )
        )
    return schemas.AdminUserListResponse(total=len(summaries), users=summaries)


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
