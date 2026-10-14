"""Speaking practice records: AI roleplay conversations
(services/roleplay.py), one row per scenario played with every turn as it
really happened, and Tone Coach attempts (services/tone_coach.py)."""

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


class ToneAttempt(Base):
    """One word or character said aloud in the Tone Coach
    (services/tone_coach.py): the tones expected (with tone changes) and,
    per syllable, the tone its pitch shape showed. Only pitch numbers ever
    reach the server -- never audio -- and only the verdicts are kept."""

    __tablename__ = "tone_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    item_type = Column(String(10), nullable=False)  # vocab | hanzi
    item_id = Column(Integer, nullable=False)
    text = Column(String(10), nullable=False)
    expected = Column(String(20), nullable=False)  # surface tones, e.g. "2-3"
    verdict = Column(String(10), nullable=False)  # correct | wrong | unclear
    syllables = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="tone_attempts")
