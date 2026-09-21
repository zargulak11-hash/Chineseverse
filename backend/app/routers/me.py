from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.services.gamification import touch_streak

router = APIRouter(prefix="/api/me", tags=["me"])


class AnimalChoice(BaseModel):
    animal_id: int = Field(ge=1)


class ProfilePatch(BaseModel):
    native_language: str | None = Field(default=None, max_length=50)
    goal_text: str | None = Field(default=None, max_length=300)
    daily_goal_minutes: int | None = Field(default=None, ge=5, le=240)
    avatar_color: str | None = Field(default=None, max_length=20)
    bio: str | None = None


class PingResponse(BaseModel):
    streak: schemas.StreakResponse
    new_day: bool


@router.get("", response_model=schemas.MeResponse)
def get_me(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.refresh(user)
    profile = user.profile or models.UserProfile(user_id=user.id)
    streak = user.streak or models.UserStreak(user_id=user.id)
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


@router.post("/ping", response_model=PingResponse)
def ping(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_day = touch_streak(user)
    db.commit()
    return PingResponse(streak=user.streak, new_day=new_day)