"""All SQLAlchemy models, one module per area of the app.

Everything is re-exported here, so `from app import models` and
`models.User` keep working everywhere (routers, services, Alembic's env.py).
Importing this package registers every table on Base.metadata, which is
what Alembic autogenerate and the string-based relationships rely on.
"""

from app.database import Base

from app.models.users import (
    User,
    UserProfile,
    PlacementAttempt,
    UserStreak,
    ActivityEvent,
    Follow,
    Notification,
)
from app.models.companions import Animal, AnimalPersonality, UserAnimal, PetTeacherCase, UserTaughtFact
from app.models.skills import HSKLevel, Skill, UserSkill
from app.models.learning import (
    Lesson,
    VocabularyWord,
    UserVocabulary,
    Hanzi,
    UserHanzi,
    GrammarTopic,
    UserGrammar,
    Progress,
    lesson_skills,
)
from app.models.world import Location, NPC, Scenario, Dialogue, DialogueChoice, Mission, UserMission
from app.models.practice import (
    VoiceAttempt,
    PracticeSession,
    HSKExamAttempt,
    StoryProgress,
    AIExplanation,
    HanziTraceAttempt,
    LearningMistake,
)
from app.models.duels import Duel, DuelParticipant, DuelAnswer
from app.models.gamification import Achievement, UserAchievement, DailyQuest
from app.models.localization import ContentTranslation

__all__ = [
    "Base",
    "User",
    "UserProfile",
    "PlacementAttempt",
    "UserStreak",
    "ActivityEvent",
    "Follow",
    "Notification",
    "Animal",
    "AnimalPersonality",
    "UserAnimal",
    "PetTeacherCase",
    "UserTaughtFact",
    "HSKLevel",
    "Skill",
    "UserSkill",
    "Lesson",
    "VocabularyWord",
    "UserVocabulary",
    "Hanzi",
    "UserHanzi",
    "GrammarTopic",
    "UserGrammar",
    "Progress",
    "lesson_skills",
    "Location",
    "NPC",
    "Scenario",
    "Dialogue",
    "DialogueChoice",
    "Mission",
    "UserMission",
    "VoiceAttempt",
    "PracticeSession",
    "HSKExamAttempt",
    "StoryProgress",
    "AIExplanation",
    "HanziTraceAttempt",
    "LearningMistake",
    "Duel",
    "DuelParticipant",
    "DuelAnswer",
    "Achievement",
    "UserAchievement",
    "DailyQuest",
    "ContentTranslation",
]
