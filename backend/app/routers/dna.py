from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.services.dna import compute_dna
from app.services.gamification import ensure_user_skills, user_rank

router = APIRouter(prefix="/api/dna", tags=["dna"])


@router.get("", response_model=schemas.DNASummaryResponse)
def my_dna(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_user_skills(db, user)
    dna = compute_dna(user)
    current, overall = user_rank(db, user)
    skills = sorted(dna["skills"].items(), key=lambda kv: kv[1], reverse=True)
    return schemas.DNASummaryResponse(
        overall=dna["overall"],
        skills=[
            schemas.SkillMasteryResponse(
                code=code,
                name=next(
                    (s.skill.name for s in user.user_skills if s.skill and s.skill.code == code),
                    code,
                ),
                mastery=value,
                xp=next(
                    (s.xp for s in user.user_skills if s.skill and s.skill.code == code),
                    0,
                ),
                status="strong" if value >= 70 else ("developing" if value >= 40 else "weak"),
            )
            for code, value in skills
        ],
        weak_areas=dna["weaknesses"],
        strong_areas=dna["strengths"],
    )