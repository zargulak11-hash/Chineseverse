from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app import models
from app.database import get_db
from app.deps import get_current_user
from app.services import notifications as svc

# Everything here is scoped to the signed-in user: the recipient is always
# the token's user, never an id from the request. Another user's
# notification is a 404 (same as a missing one) so ids don't leak.
# Notifications are only ever CREATED by the server as a side effect of a
# real action (e.g. POST /api/users/{id}/follow) -- there is no create route.
router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationActor(BaseModel):
    id: int
    username: str
    avatar_url: str | None = None


class NotificationOut(BaseModel):
    id: int
    type: str
    actor: NotificationActor | None = None
    read: bool
    read_at: datetime | None = None
    created_at: datetime | None = None
    link: str | None = None


class UnreadCount(BaseModel):
    unread: int


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    limit: int = Query(default=20, ge=1, le=100),
    unread_only: bool = False,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = (
        db.query(models.Notification)
        .options(joinedload(models.Notification.actor).joinedload(models.User.profile))
        .filter(models.Notification.recipient_id == user.id)
    )
    if unread_only:
        q = q.filter(models.Notification.read_at.is_(None))
    rows = q.order_by(models.Notification.created_at.desc(), models.Notification.id.desc()).limit(limit).all()
    return [svc.serialize(n) for n in rows]


@router.get("/unread-count", response_model=UnreadCount)
def get_unread_count(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_locale: str | None = Header(default=None),
):
    # Polled by the topbar bell, so it is also where the app learns which
    # language the learner currently uses (for emails sent while away).
    svc.remember_locale(db, user, x_locale)
    return UnreadCount(unread=svc.unread_count(db, user))


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    n = db.get(models.Notification, notification_id)
    if n is None or n.recipient_id != user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    if n.read_at is None:
        n.read_at = datetime.utcnow()
        db.commit()
        db.refresh(n)
    return svc.serialize(n)
