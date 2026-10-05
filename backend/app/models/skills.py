"""HSK levels and the Learning Compass skills (a learner's mastery of each)."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base

# ---------------------------------------------------------------------------
# HSK, skills, mastery
# ---------------------------------------------------------------------------


class HSKLevel(Base):
    __tablename__ = "hsk_levels"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(Integer, unique=True, nullable=False, index=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    total_vocab_target = Column(Integer, default=150)
    mastery_to_unlock_next = Column(Float, default=60.0)
    # True only for the single "HSK 7-9 (Advanced)" row: per the real HSK 3.0
    # standard, 7/8/9 share one advanced vocabulary/Hanzi/grammar pool rather
    # than three independent official lists. The frontend still renders three
    # progression stages, computed from mastery thirds within this one band.
    is_advanced_band = Column(Boolean, default=False)

    lessons = relationship("Lesson", back_populates="level")
    vocabulary = relationship("VocabularyWord", back_populates="level")
    grammar = relationship("GrammarTopic", back_populates="level")
    hanzi = relationship("Hanzi", back_populates="level")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), default="core")
    description = Column(Text, nullable=True)

    user_skills = relationship("UserSkill", back_populates="skill")
    lessons = relationship(
        "Lesson", secondary="lesson_skills", back_populates="skills"
    )


class UserSkill(Base):
    __tablename__ = "user_skills"
    __table_args__ = (UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False, index=True)
    level = Column(Integer, default=1)
    xp = Column(Integer, default=0)
    mastery = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="user_skills")
    skill = relationship("Skill", back_populates="user_skills")
