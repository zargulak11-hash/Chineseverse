import uuid

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.services.avatars import AVATAR_DIR, UPLOAD_PREFIX, file_for
from app.services.gamification import touch_streak
from app.services.notifications import remember_locale

router = APIRouter(prefix="/api/me", tags=["me"])

# Local static storage for uploaded profile pictures — no cloud storage
# integration exists anywhere else in this project, so this doesn't invent
# one. Files are served back out via the /static mount in main.py; the
# photo-or-initial rule lives in services/avatars.py.
AVATAR_CONTENT_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MAX_AVATAR_BYTES = 3 * 1024 * 1024


def _is_image(data: bytes, content_type: str) -> bool:
    """The declared type is the client's word; the leading bytes have to
    agree before anything is written to disk and served back to everyone
    as that user's photo (same rule as the assistant's attachments)."""
    if content_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if content_type == "image/webp":
        return data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    return False


def _delete_existing_avatar(avatar_url: str | None) -> None:
    path = file_for(avatar_url)
    if path is not None:
        path.unlink(missing_ok=True)


class AnimalChoice(BaseModel):
    animal_id: int = Field(ge=1)


class ProfilePatch(BaseModel):
    native_language: str | None = Field(default=None, max_length=50)
    goal_text: str | None = Field(default=None, max_length=300)
    daily_goal_minutes: int | None = Field(default=None, ge=5, le=240)
    avatar_color: str | None = Field(default=None, max_length=20)
    bio: str | None = Field(default=None, max_length=1000)
    learning_motivation: str | None = Field(default=None, max_length=30)
    learning_motivation_other: str | None = Field(default=None, max_length=200)
    discovery_source: str | None = Field(default=None, max_length=30)
    discovery_source_other: str | None = Field(default=None, max_length=200)


class AccountPatch(BaseModel):
    username: str = Field(min_length=3, max_length=50)


class PingResponse(BaseModel):
    streak: schemas.StreakResponse
    new_day: bool


@router.get("", response_model=schemas.MeResponse)
def get_me(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_locale: str | None = Header(default=None),
):
    remember_locale(db, user, x_locale)  # the language emails to them should use
    db.refresh(user)
    profile = user.profile
    if profile is None:
        # A transient (never-flushed) UserProfile() would leave every column
        # at Python's bare None instead of the model's default=, since
        # SQLAlchemy only applies Column(default=...) during an actual
        # INSERT. Persist it so the row — and its real defaults — exist for
        # this and every future request.
        profile = models.UserProfile(user_id=user.id)
        db.add(profile)
    streak = user.streak
    if streak is None:
        streak = models.UserStreak(user_id=user.id)
        db.add(streak)
    db.commit()
    db.refresh(profile)
    db.refresh(streak)
    return schemas.MeResponse(user=user, profile=profile, streak=streak)


@router.post("/animal", response_model=schemas.UserAnimalResponse)
def choose_animal(
    payload: AnimalChoice,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    animal = db.get(models.Animal, payload.animal_id)
    if animal is None:
        raise HTTPException(status_code=404, detail="Animal not found")

    link = user.user_animal
    if link is None:
        link = models.UserAnimal(user_id=user.id, animal_id=animal.id, bond_level=1)
        db.add(link)
    else:
        link.animal_id = animal.id
        link.interactions += 1

    user.animal_id = animal.id
    touch_streak(user)
    db.commit()
    db.refresh(link)
    return link


@router.patch("/profile", response_model=schemas.UserProfileResponse)
def update_profile(
    payload: ProfilePatch,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = user.profile
    if profile is None:
        profile = models.UserProfile(user_id=user.id)
        db.add(profile)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile


@router.patch("/account", response_model=schemas.UserResponse)
def update_account(
    payload: AccountPatch,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Case-insensitive, as registration checks: "Alice" next to "alice" is
    # two accounts people can't tell apart (and one login-throttle bucket,
    # which keys on the case-folded name).
    conflict = (
        db.query(models.User)
        .filter(func.lower(models.User.username) == payload.username.lower(), models.User.id != user.id)
        .first()
    )
    if conflict is not None:
        raise HTTPException(status_code=409, detail="username already taken")
    user.username = payload.username
    db.commit()
    db.refresh(user)
    return user


@router.post("/avatar", response_model=schemas.UserProfileResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ext = AVATAR_CONTENT_TYPES.get(file.content_type)
    if ext is None:
        raise HTTPException(status_code=415, detail="Only JPG, PNG or WEBP images are allowed")
    data = await file.read()
    if len(data) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=413, detail="Image must be 3 MB or smaller")
    if not _is_image(data, file.content_type):
        raise HTTPException(status_code=415, detail="Only JPG, PNG or WEBP images are allowed")

    profile = user.profile
    if profile is None:
        profile = models.UserProfile(user_id=user.id)
        db.add(profile)
        db.flush()

    _delete_existing_avatar(profile.avatar_url)
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"user{user.id}_{uuid.uuid4().hex[:10]}.{ext}"
    (AVATAR_DIR / filename).write_bytes(data)
    profile.avatar_url = f"{UPLOAD_PREFIX}{filename}"
    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/avatar", response_model=schemas.UserProfileResponse)
def remove_avatar(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = user.profile
    if profile is None:
        profile = models.UserProfile(user_id=user.id)
        db.add(profile)
    else:
        _delete_existing_avatar(profile.avatar_url)
        profile.avatar_url = None
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/ping", response_model=PingResponse)
def ping(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_day = touch_streak(user)
    db.commit()
    return PingResponse(streak=user.streak, new_day=new_day)