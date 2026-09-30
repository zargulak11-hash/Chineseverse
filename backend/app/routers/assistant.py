from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services import ai_client
from app.services.gamification import ensure_user_skills, user_rank
from app.services.localization import load_translations, tr

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=2000)


class AssistantRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)


class AssistantResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=AssistantResponse)
def chat(
    payload: AssistantRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    ensure_user_skills(db, user)
    level, mastery = user_rank(db, user)
    weakest = sorted(
        (s for s in user.user_skills if s.skill), key=lambda s: s.mastery
    )[:2]
    skill_tr = load_translations(db, "skill", [str(s.skill.id) for s in weakest], locale)

    context = {
        "username": user.username,
        "hsk_level": level,
        "mastery": mastery,
        "streak": user.streak.current_streak if user.streak else 0,
        # Same localized skill names the dashboard/DNA pages show, so a reply
        # in the selected language doesn't splice in English skill names.
        "weak_skills": [tr(skill_tr, s.skill.id, "name", s.skill.name) for s in weakest],
        "companion": user.animal.name if user.animal else None,
    }
    reply = ai_client.assistant_reply(
        [m.model_dump() for m in payload.messages], context, locale
    )
    return AssistantResponse(reply=reply)
