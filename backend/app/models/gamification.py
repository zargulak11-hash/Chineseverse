"""Achievements and daily quests."""

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base

# ---------------------------------------------------------------------------
# Achievements & quests
# ---------------------------------------------------------------------------


class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(60), unique=True, nullable=False, index=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(20), default="🏆")
    category = Column(String(30), default="general")
    criteria = Column(JSON, nullable=True)  # {type, target}

    user_links = relationship("UserAchievement", back_populates="achievement")


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (
        UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    achievement_id = Column(Integer, ForeignKey("achievements.id"), nullable=False, index=True)
    unlocked_at = Column(DateTime, default=datetime.utcnow)
    # When the learner was shown the "Achievement unlocked!" note (null = not
    # yet). Stored, not kept in the browser, so it appears once per unlock
    # across refreshes, devices and re-logins.
    notified_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="user_achievements")
    achievement = relationship("Achievement", back_populates="user_links")


class DailyQuest(Base):
    __tablename__ = "daily_quests"
    __table_args__ = (
        UniqueConstraint("user_id", "quest_date", "quest_type", name="uq_user_quest"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    quest_date = Column(Date, default=date.today)
    quest_type = Column(String(30), nullable=False)  # speaking|vocab|case|duel|lesson|listening
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    target = Column(Integer, default=1)
    progress = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    claimed = Column(Boolean, nullable=False, server_default="false", default=False)
    reward_xp = Column(Integer, default=50)
    reward_coins = Column(Integer, default=0)
    flavor = Column(Text, nullable=True)

    user = relationship("User", back_populates="daily_quests")
