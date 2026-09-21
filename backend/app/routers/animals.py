from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas
from app.crud import apply_updates, get_or_404
from app.database import get_db

router = APIRouter(prefix="/api/animals", tags=["animals"])


@router.get("", response_model=list[schemas.AnimalResponse])
def list_animals(db: Session = Depends(get_db)):
    return db.query(models.Animal).order_by(models.Animal.id).all()


@router.post("", response_model=schemas.AnimalResponse, status_code=201)
def create_animal(payload: schemas.AnimalCreate, db: Session = Depends(get_db)):
    animal = models.Animal(**payload.model_dump())
    db.add(animal)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail=f"Animal name '{payload.name}' already exists"
        )
    db.refresh(animal)
    return animal


@router.get("/{animal_id}", response_model=schemas.AnimalResponse)
def get_animal(animal_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, models.Animal, animal_id)


@router.put("/{animal_id}", response_model=schemas.AnimalResponse)
def update_animal(
    animal_id: int, payload: schemas.AnimalUpdate, db: Session = Depends(get_db)
):
    animal = get_or_404(db, models.Animal, animal_id)
    apply_updates(animal, payload.model_dump())
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail=f"Animal name '{payload.name}' already exists"
        )
    db.refresh(animal)
    return animal


@router.patch("/{animal_id}", response_model=schemas.AnimalResponse)
def patch_animal(
    animal_id: int, payload: schemas.AnimalPatch, db: Session = Depends(get_db)
):
    animal = get_or_404(db, models.Animal, animal_id)
    apply_updates(animal, payload.model_dump(exclude_unset=True))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Animal name already exists")
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