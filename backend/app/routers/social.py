from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.crud import get_or_404
from app.database import get_db
from app.deps import get_current_user

# Shares the /api/users prefix with routers/users.py (plain CRUD, no auth —
# a pre-existing separate concern). These routes are registered BEFORE
# users.router in main.py so the literal /api/users/search path wins path
# matching over users.py's catch-all GET /api/users/{user_id} — if the order
# were reversed, FastAPI would try to parse "search" as an int user_id and
# 422 before ever reaching this router.
router = APIRouter(prefix="/api/users", tags=["social"])


def _to_public(db: Session, target: models.User, viewer: models.User) -> schemas.PublicUserResponse:
    followers_count = db.query(models.Follow).filter_by(following_id=target.id).count()
    following_count = db.query(models.Follow).filter_by(follower_id=target.id).count()
    is_following = (
        viewer.id != target.id
        and db.query(models.Follow)
        .filter_by(follower_id=viewer.id, following_id=target.id)
        .first()
        is not None
    )
    return schemas.PublicUserResponse(
        id=target.id,
        username=target.username,
        animal_id=target.animal_id,
        total_xp=target.total_xp,
        avatar_url=target.profile.avatar_url if target.profile else None,
        created_at=target.created_at,
        followers_count=followers_count,
        following_count=following_count,
        is_following=is_following,
        is_self=(viewer.id == target.id),
    )


@router.get("/search", response_model=list[schemas.PublicUserResponse])
def search_users(
    q: str = Query(min_length=1, max_length=50),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(models.User)
        .filter(models.User.username.ilike(f"%{q}%"), models.User.id != user.id)
        .order_by(models.User.username)
        .limit(20)
        .all()
    )
    return [_to_public(db, r, user) for r in rows]


@router.get("/{user_id}/public", response_model=schemas.PublicUserResponse)
def get_public_profile(
    user_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = get_or_404(db, models.User, user_id)
    return _to_public(db, target, user)


@router.post("/{user_id}/follow", response_model=schemas.PublicUserResponse, status_code=201)
def follow_user(
    user_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="You cannot follow yourself")
    target = get_or_404(db, models.User, user_id)
    existing = (
        db.query(models.Follow)
        .filter_by(follower_id=user.id, following_id=user_id)
        .first()
    )
    if existing is None:
        db.add(models.Follow(follower_id=user.id, following_id=user_id))
        db.commit()
    return _to_public(db, target, user)


@router.delete("/{user_id}/follow", response_model=schemas.PublicUserResponse)
def unfollow_user(
    user_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = get_or_404(db, models.User, user_id)
    db.query(models.Follow).filter_by(follower_id=user.id, following_id=user_id).delete()
    db.commit()
    return _to_public(db, target, user)


@router.get("/{user_id}/followers", response_model=list[schemas.PublicUserResponse])
def list_followers(
    user_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_or_404(db, models.User, user_id)
    rows = db.query(models.Follow).filter_by(following_id=user_id).all()
    out = []
    for r in rows:
        follower = db.get(models.User, r.follower_id)
        if follower:
            out.append(_to_public(db, follower, user))
    return out


@router.get("/{user_id}/following", response_model=list[schemas.PublicUserResponse])
def list_following(
    user_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_or_404(db, models.User, user_id)
    rows = db.query(models.Follow).filter_by(follower_id=user_id).all()
    out = []
    for r in rows:
        followee = db.get(models.User, r.following_id)
        if followee:
            out.append(_to_public(db, followee, user))
    return out
