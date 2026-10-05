"""Real 1-vs-1 duels: the duel, its two participants and their answers."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base

# ---------------------------------------------------------------------------
# Duels
# ---------------------------------------------------------------------------


class Duel(Base):
    """A 1-vs-1 duel between two real users (see routers/duels.py).

    Lifecycle: pending (challenge sent) -> active (opponent accepted) ->
    completed; or pending -> declined | cancelled | expired. "finished",
    "open" and "aborted" are legacy values mapped by migration a7d3c9e1f402.

    question_data holds the shared question set ({"engine": "practice_v1",
    "questions": [{type, item_type, item_id, option_ids}]}) -- the same
    shape the server-graded practice engine uses, so both players get the
    identical questions and only the server knows the answers."""

    __tablename__ = "duels"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(20), default="pending", index=True)
    challenge_type = Column(String(30), nullable=True)
    question_data = Column(JSON, nullable=True)
    winner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    hsk_level = Column(Integer, nullable=True)
    time_limit_seconds = Column(Integer, nullable=True)
    expires_at = Column(DateTime, nullable=True)      # pending challenge lapses
    started_at = Column(DateTime, nullable=True)      # accepted -> active
    play_deadline = Column(DateTime, nullable=True)   # last moment to start one's attempt
    responded_at = Column(DateTime, nullable=True)    # accepted/declined/cancelled at
    decided_by = Column(String(20), nullable=True)    # correct|score|time|draw
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    participants = relationship(
        "DuelParticipant", back_populates="duel", cascade="all, delete-orphan"
    )
    answers = relationship(
        "DuelAnswer", back_populates="duel", cascade="all, delete-orphan"
    )


class DuelParticipant(Base):
    """One player's side of a duel. Each player's clock is their own:
    started_at is when THEY began, and their deadline is started_at +
    duel.time_limit_seconds -- nothing the opponent does moves it."""

    __tablename__ = "duel_participants"
    __table_args__ = (UniqueConstraint("duel_id", "user_id", name="uq_duel_user"),)

    id = Column(Integer, primary_key=True, index=True)
    duel_id = Column(Integer, ForeignKey("duels.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(20), default="challenger")  # challenger|opponent
    score = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    answered = Column(Integer, default=0)
    finished = Column(Boolean, default=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    finish_reason = Column(String(20), nullable=True)  # completed|timeout|forfeit|no_show
    time_used_ms = Column(Integer, nullable=True)

    duel = relationship("Duel", back_populates="participants")
    user = relationship("User", back_populates="participants")


class DuelAnswer(Base):
    """One graded answer. The unique key makes a question count at most once
    per player, whatever the client sends (double click, retry, two tabs)."""

    __tablename__ = "duel_answers"
    __table_args__ = (
        UniqueConstraint("duel_id", "user_id", "question_index", name="uq_duel_answer"),
    )

    id = Column(Integer, primary_key=True, index=True)
    duel_id = Column(Integer, ForeignKey("duels.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_index = Column(Integer, nullable=False)
    choice_id = Column(Integer, nullable=False)
    correct = Column(Boolean, nullable=False)
    points = Column(Integer, nullable=False, default=0)
    response_ms = Column(Integer, nullable=False, default=0)
    answered_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    duel = relationship("Duel", back_populates="answers")
