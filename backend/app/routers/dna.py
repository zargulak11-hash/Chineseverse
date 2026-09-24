from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services.dna import compute_dna
from app.services.gamification import ensure_user_skills, user_rank
from app.services.localization import load_translations, tr

router = APIRouter(prefix="/api/dna", tags=["dna"])


@router.get("", response_model=schemas.DNASummaryResponse)
def my_dna(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    ensure_user_skills(db, user)
    dna = compute_dna(user)
    current, overall = user_rank(db, user)
    skills = sorted(dna["skills"].items(), key=lambda kv: kv[1], reverse=True)

    skill_rows = {s.skill.code: s.skill for s in user.user_skills if s.skill}
    translations = load_translations(db, "skill", [str(s.id) for s in skill_rows.values()], locale)

    def skill_name(code: str) -> str:
        row = skill_rows.get(code)
        if row is None:
            return code
        return tr(translations, row.id, "name", row.name)

    return schemas.DNASummaryResponse(
        overall=dna["overall"],
        skills=[
            schemas.SkillMasteryResponse(
                code=code,
                name=skill_name(code),
                mastery=value,
                xp=next(
                    (s.xp for s in user.user_skills if s.skill and s.skill.code == code),
                    0,
                ),
                status="strong" if value >= 70 else ("developing" if value >= 40 else "weak"),
            )
            for code, value in skills
        ],
        # Same thresholds compute_dna uses (mastery >= 70 / <= 30), just
        # recomputed here off user_skills directly so the name can be
        # localized instead of taking compute_dna's already-English names.
        strong_areas=[skill_name(s.skill.code) for s in user.user_skills if s.skill and s.mastery >= 70],
        weak_areas=[skill_name(s.skill.code) for s in user.user_skills if s.skill and s.mastery <= 30],
    )