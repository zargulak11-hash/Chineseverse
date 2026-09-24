from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.crud import apply_updates, commit_or_409, get_or_404
from app.database import get_db
from app.deps import get_locale
from app.services.localization import load_translations, tr

router = APIRouter(prefix="/api/animals", tags=["animals"])


def _localize_animal(animal: models.Animal, translations: dict) -> schemas.AnimalDetailResponse:
    # name/species/slug stay as-authored: `name` is a fixed character
    # identity used elsewhere (AI prompts, duel/mission text matching), and
    # `species` is a Latin binomial (language-independent already).
    out = schemas.AnimalDetailResponse.model_validate(animal)
    key = str(animal.id)
    out.description = tr(translations, key, "description", out.description)
    out.personality = tr(translations, key, "personality", out.personality)
    out.tone_style = tr(translations, key, "tone_style", out.tone_style)
    out.special_ability = tr(translations, key, "special_ability", out.special_ability)
    out.preferred_mechanics = tr(translations, key, "preferred_mechanics", out.preferred_mechanics)
    return out


@router.get("", response_model=list[schemas.AnimalDetailResponse])
def list_animals(db: Session = Depends(get_db), locale: str = Depends(get_locale)):
    # AnimalDetailResponse adds personality_row (traits/energy/humor/patience/
    # strictness/catchphrase) on top of the existing fields -- purely
    # additive, so nothing that already reads this endpoint breaks. The
    # Voice Companion picker is what actually needs these to build a
    # distinct voice profile per animal instead of one generic voice.
    animals = db.query(models.Animal).order_by(models.Animal.id).all()
    translations = load_translations(db, "animal", [str(a.id) for a in animals], locale)
    return [_localize_animal(a, translations) for a in animals]


@router.post("", response_model=schemas.AnimalResponse, status_code=201)
def create_animal(payload: schemas.AnimalCreate, db: Session = Depends(get_db)):
    animal = models.Animal(**payload.model_dump())
    db.add(animal)
    commit_or_409(db, f"Animal name '{payload.name}' already exists")
    db.refresh(animal)
    return animal


@router.get("/{animal_id}", response_model=schemas.AnimalResponse)
def get_animal(animal_id: int, db: Session = Depends(get_db), locale: str = Depends(get_locale)):
    animal = get_or_404(db, models.Animal, animal_id)
    translations = load_translations(db, "animal", [str(animal.id)], locale)
    out = schemas.AnimalResponse.model_validate(animal)
    key = str(animal.id)
    out.description = tr(translations, key, "description", out.description)
    out.personality = tr(translations, key, "personality", out.personality)
    out.tone_style = tr(translations, key, "tone_style", out.tone_style)
    out.special_ability = tr(translations, key, "special_ability", out.special_ability)
    out.preferred_mechanics = tr(translations, key, "preferred_mechanics", out.preferred_mechanics)
    return out


@router.put("/{animal_id}", response_model=schemas.AnimalResponse)
def update_animal(
    animal_id: int, payload: schemas.AnimalUpdate, db: Session = Depends(get_db)
):
    animal = get_or_404(db, models.Animal, animal_id)
    apply_updates(animal, payload.model_dump())
    commit_or_409(db, f"Animal name '{payload.name}' already exists")
    db.refresh(animal)
    return animal


@router.patch("/{animal_id}", response_model=schemas.AnimalResponse)
def patch_animal(
    animal_id: int, payload: schemas.AnimalPatch, db: Session = Depends(get_db)
):
    animal = get_or_404(db, models.Animal, animal_id)
    apply_updates(animal, payload.model_dump(exclude_unset=True))
    commit_or_409(db, "Animal name already exists")
    db.refresh(animal)
    return animal


@router.delete("/{animal_id}", status_code=204)
def delete_animal(animal_id: int, db: Session = Depends(get_db)):
    animal = get_or_404(db, models.Animal, animal_id)
    users_count = db.query(models.User).filter(models.User.animal_id == animal_id).count()
    if users_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Animal is assigned to one or more users and cannot be deleted",
        )
    db.delete(animal)
    db.commit()