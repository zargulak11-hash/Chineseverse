"""AI roleplay conversations (services/roleplay.py): one row per scenario
the learner plays, with every turn as it really happened."""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class RoleplaySession(Base):
    __tablename__ = "roleplay_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    scenario = Column(String(40), nullable=False)
    hsk_level = Column(Integer, nullable=False, default=1)
    # Every turn in order: {"role": "partner"|"learner", "zh", ...}. The
    # partner's lines carry their pinyin and translation (revealed on
    # request); the learner's carry the correction they received.
    turns = Column(JSON, nullable=False, default=list)
    # The scenario goals reached so far (indices), as judged turn by turn.
    goals_met = Column(JSON, nullable=False, default=list)
    status = Column(String(20), nullable=False, default="active")  # active | finished
    summary = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="roleplay_sessions")
