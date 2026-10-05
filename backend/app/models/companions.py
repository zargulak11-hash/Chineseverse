"""Companions: the animals, their personalities, a learner's bond with one,
and Pet Teacher (the learner corrects the companion's grammar)."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
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
# Animals
# ---------------------------------------------------------------------------


class Animal(Base):
    __tablename__ = "animals"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    species = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    accent_color = Column(String(20), default="#f59e0b")
    personality = Column(String(300), nullable=True)
    tone_style = Column(Text, nullable=True)
    preferred_mechanics = Column(Text, nullable=True)
    special_ability = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="animal")
    personality_row = relationship(
        "AnimalPersonality", back_populates="animal", uselist=False, cascade="all, delete-orphan"
    )
    user_links = relationship("UserAnimal", back_populates="animal")


class AnimalPersonality(Base):
    __tablename__ = "animal_personalities"

    id = Column(Integer, primary_key=True, index=True)
    animal_id = Column(Integer, ForeignKey("animals.id"), nullable=False, unique=True)
    traits = Column(String(300), nullable=True)
    energy = Column(Integer, default=50)
    humor = Column(Integer, default=50)
    patience = Column(Integer, default=50)
    strictness = Column(Integer, default=50)
    catchphrase = Column(String(200), nullable=True)
    chat_style = Column(Text, nullable=True)

    animal = relationship("Animal", back_populates="personality_row")


class UserAnimal(Base):
    __tablename__ = "user_animals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    animal_id = Column(Integer, ForeignKey("animals.id"), nullable=False)
    bonded_at = Column(DateTime, default=datetime.utcnow)
    bond_level = Column(Integer, default=1)
    bond_points = Column(Integer, default=0)
    interactions = Column(Integer, default=0)

    user = relationship("User", back_populates="user_animal")
    animal = relationship("Animal", back_populates="user_links")


# ---------------------------------------------------------------------------
# Pet Teacher Mode — the animal deliberately gets a grammar point wrong and
# the learner has to catch it, correct it, and explain the rule.
# ---------------------------------------------------------------------------


class PetTeacherCase(Base):
    __tablename__ = "pet_teacher_cases"

    id = Column(Integer, primary_key=True, index=True)
    grammar_topic_id = Column(Integer, ForeignKey("grammar_topics.id"), nullable=True, index=True)
    hsk_level_id = Column(Integer, ForeignKey("hsk_levels.id"), nullable=False, index=True)
    wrong_sentence = Column(String(300), nullable=False)
    correct_sentence = Column(String(300), nullable=False)
    mistake_summary = Column(String(300), nullable=True)
    explanation_keywords = Column(JSON, nullable=True)  # what a correct explanation should mention
    hint = Column(String(300), nullable=True)
    order_index = Column(Integer, default=0)

    grammar_topic = relationship("GrammarTopic")
    level = relationship("HSKLevel")

    @property
    def hsk_level(self):
        return self.level.level if self.level else None


class UserTaughtFact(Base):
    __tablename__ = "user_taught_facts"
    __table_args__ = (
        UniqueConstraint("user_id", "case_id", name="uq_user_case_taught"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("pet_teacher_cases.id"), nullable=False, index=True)
    taught_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="taught_facts")
    case = relationship("PetTeacherCase")
