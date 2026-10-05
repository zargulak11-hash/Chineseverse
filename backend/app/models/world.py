"""The Chinese World: locations, characters, scenarios and their dialogues,
and the missions built on them."""

from sqlalchemy import (
    JSON,
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
# Chinese World
# ---------------------------------------------------------------------------


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    kind = Column(String(30), default="place")
    description = Column(Text, nullable=True)
    unlock_level = Column(Integer, default=1)
    unlock_skill_mastery = Column(Float, default=20.0)
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    icon = Column(String(20), default="🏠")
    accent = Column(String(20), default="#f59e0b")

    npcs = relationship("NPC", back_populates="location", cascade="all, delete-orphan")
    scenarios = relationship("Scenario", back_populates="location", cascade="all, delete-orphan")


class NPC(Base):
    __tablename__ = "npcs"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    role = Column(String(100), nullable=True)
    title = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    personality = Column(String(300), nullable=True)
    speech_style = Column(Text, nullable=True)

    location = relationship("Location", back_populates="npcs")
    dialogues = relationship("Dialogue", back_populates="npc")


class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    slug = Column(String(80), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    scenario_type = Column(String(20), default="conversation")  # conversation|mission|case|practice
    description = Column(Text, nullable=True)
    min_hsk_level = Column(Integer, default=1)
    difficulty = Column(Integer, default=1)
    is_case = Column(Boolean, default=False)
    case_data = Column(JSON, nullable=True)  # {clues:[], contradiction_text, solution_kws}
    requires_voice = Column(Boolean, default=False)
    order_index = Column(Integer, default=0)

    location = relationship("Location", back_populates="scenarios")
    dialogues = relationship("Dialogue", back_populates="scenario", cascade="all, delete-orphan")
    missions = relationship("Mission", back_populates="scenario", cascade="all, delete-orphan")


class Dialogue(Base):
    __tablename__ = "dialogues"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=True, index=True)
    npc_id = Column(Integer, ForeignKey("npcs.id"), nullable=True, index=True)
    turn_index = Column(Integer, default=0)
    speaker = Column(String(10), default="npc")  # npc|learner
    text = Column(Text, nullable=False)
    pinyin = Column(String(300), nullable=True)
    english = Column(String(300), nullable=True)
    prompt = Column(Text, nullable=True)
    expected_keywords = Column(JSON, nullable=True)
    requires_voice = Column(Boolean, default=False)
    reaction_correct = Column(String(200), nullable=True)
    reaction_incorrect = Column(String(200), nullable=True)

    scenario = relationship("Scenario", back_populates="dialogues")
    npc = relationship("NPC", back_populates="dialogues")
    choices = relationship("DialogueChoice", back_populates="dialogue", cascade="all, delete-orphan")


class DialogueChoice(Base):
    __tablename__ = "dialogue_choices"

    id = Column(Integer, primary_key=True, index=True)
    dialogue_id = Column(Integer, ForeignKey("dialogues.id"), nullable=False, index=True)
    label = Column(String(200), nullable=False)
    response_text = Column(Text, nullable=True)
    is_best = Column(Boolean, default=False)
    feedback = Column(Text, nullable=True)
    next_turn = Column(Integer, nullable=True)

    dialogue = relationship("Dialogue", back_populates="choices")


# ---------------------------------------------------------------------------
# Missions
# ---------------------------------------------------------------------------


class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=True, index=True)
    slug = Column(String(80), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    objective = Column(Text, nullable=True)
    kind = Column(String(30), default="world")  # speak|listening|conversation|vocab|case|duel|teach
    min_hsk_level = Column(Integer, default=1)
    reward_xp = Column(Integer, default=50)
    reward_coins = Column(Integer, default=0)
    target_count = Column(Integer, default=1)
    sort_order = Column(Integer, default=0)

    scenario = relationship("Scenario", back_populates="missions")
    user_entries = relationship("UserMission", back_populates="mission")


class UserMission(Base):
    __tablename__ = "user_missions"
    __table_args__ = (UniqueConstraint("user_id", "mission_id", name="uq_user_mission"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=False, index=True)
    status = Column(String(20), default="available")  # available|active|completed
    progress = Column(Integer, default=0)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="user_missions")
    mission = relationship("Mission", back_populates="user_entries")
