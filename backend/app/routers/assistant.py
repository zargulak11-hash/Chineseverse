from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user
from app.services import ai_client
from app.services.gamification import ensure_user_skills, user_rank

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
):
    ensure_user_skills(db, user)
    level, mastery = user_rank(db, user)
    weakest = sorted(
        (s for s in user.user_skills if s.skill), key=lambda s: s.mastery
    )[:2]

    context = {
        "username": user.username,
        "hsk_level": level,
        "mastery": mastery,
        "streak": user.streak.current_streak if user.streak else 0,
        "weak_skills": [s.skill.name for s in weakest],
        "companion": user.animal.name if user.animal else None,
    }
    reply = ai_client.assistant_reply(
        [m.model_dump() for m in payload.messages], context
    )
    return AssistantResponse(reply=reply)
