"""Accounts and the learner's own records: the user row, profile, placement,
streak, activity log, follows and notifications."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
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
# Core user tables
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    # Google's permanent account id (the ID token's `sub` claim). Set on the
    # first Google sign-in and used before email for every later one, so a
    # Google identity always resolves to the same row (see routers/auth.py).
    google_sub = Column(String(255), unique=True, nullable=True, index=True)
    # GitHub's permanent numeric account id (stored as text), the GitHub
    # counterpart of google_sub: a GitHub login or email can change, the id
    # never does.
    github_id = Column(String(64), unique=True, nullable=True, index=True)
    animal_id = Column(Integer, ForeignKey("animals.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    # Grants access to /api/admin/*. Never set from a request payload — the
    # only writers are a one-off migration (see
    # alembic/versions/*_add_user_is_admin.py) and direct DB access, so a
    # user can never self-promote through the app itself (see deps.require_admin).
    is_admin = Column(Boolean, nullable=False, server_default="false", default=False)
    total_xp = Column(Integer, nullable=False, server_default="0", default=0)
    coins = Column(Integer, nullable=False, server_default="0", default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    # The UI language the learner last used ("en" | "ru" | "tg" | "zh"),
    # learned from the X-Locale header the frontend sends. Only used for
    # things sent while they're away (notification emails); null until the
    # app has seen them once, which means English.
    locale = Column(String(5), nullable=True)

    animal = relationship("Animal", back_populates="users")
    profile = relationship(
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    streak = relationship(
        "UserStreak", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    user_animal = relationship(
        "UserAnimal", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    user_skills = relationship("UserSkill", back_populates="user", cascade="all, delete-orphan")
    user_vocabulary = relationship("UserVocabulary", back_populates="user", cascade="all, delete-orphan")
    user_hanzi = relationship("UserHanzi", back_populates="user", cascade="all, delete-orphan")
    user_grammar = relationship("UserGrammar", back_populates="user", cascade="all, delete-orphan")
    voice_attempts = relationship("VoiceAttempt", back_populates="user", cascade="all, delete-orphan")
    learning_mistakes = relationship("LearningMistake", back_populates="user", cascade="all, delete-orphan")
    taught_facts = relationship("UserTaughtFact", back_populates="user", cascade="all, delete-orphan")
    user_missions = relationship("UserMission", back_populates="user", cascade="all, delete-orphan")
    user_achievements = relationship("UserAchievement", back_populates="user", cascade="all, delete-orphan")
    daily_quests = relationship("DailyQuest", back_populates="user", cascade="all, delete-orphan")
    participants = relationship("DuelParticipant", back_populates="user", cascade="all, delete-orphan")
    progress = relationship("Progress", back_populates="user", cascade="all, delete-orphan")
    practice_sessions = relationship("PracticeSession", back_populates="user", cascade="all, delete-orphan")
    exam_attempts = relationship("HSKExamAttempt", back_populates="user", cascade="all, delete-orphan")
    trace_attempts = relationship("HanziTraceAttempt", back_populates="user", cascade="all, delete-orphan")
    story_progress = relationship("StoryProgress", back_populates="user", cascade="all, delete-orphan")

    @property
    def onboarding_completed(self) -> bool:
        """The profile's flag, carried on the user every auth and /me response
        returns (schemas.UserResponse), so the frontend's route guard reads it
        from the same stored `user` it already gates sign-in on. The profile
        column stays the one source of truth; this only exposes it."""
        return bool(self.profile is not None and self.profile.onboarding_completed)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    native_language = Column(String(50), default="English")
    goal_text = Column(String(300), nullable=True)
    daily_goal_minutes = Column(Integer, default=10)
    avatar_color = Column(String(20), default="#6366f1")
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    level_test_score = Column(Integer, nullable=True)
    learning_motivation = Column(String(30), nullable=True)
    learning_motivation_other = Column(String(200), nullable=True)
    discovery_source = Column(String(30), nullable=True)
    discovery_source_other = Column(String(200), nullable=True)
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="profile")


class PlacementAttempt(Base):
    """Onboarding placement test. Mirrors Duel's question_data pattern: the
    full generated question set (including answers) lives server-side only
    and is never sent back to the client as-is."""

    __tablename__ = "placement_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="active")  # active|finished|skipped
    question_data = Column(JSON, nullable=True)
    correct_count = Column(Integer, nullable=True)
    total_count = Column(Integer, nullable=True)
    placed_level = Column(Integer, nullable=True)
    overall_mastery = Column(Float, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)


class UserStreak(Base):
    __tablename__ = "user_streaks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    total_active_days = Column(Integer, default=0)
    last_active_date = Column(Date, nullable=True)

    user = relationship("User", back_populates="streak")


class ActivityEvent(Base):
    """One real, timestamped user action — the ground truth the Progress
    page's "Learning Rhythm" stats, streak-by-section breakdown and activity
    heatmap are all computed from (see services/activity.py). `minutes` is
    an estimated duration weight per action type (there's no active-focus
    timer in this app), not a fabricated number: it's assigned once, up
    front, per action type, the same way for every user."""

    __tablename__ = "activity_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    section = Column(String(30), nullable=False)
    action_type = Column(String(40), nullable=False)
    minutes = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = (
        UniqueConstraint("follower_id", "following_id", name="uq_follow_pair"),
    )

    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    following_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    """A persistent in-app notification for one recipient (e.g. "Zarina
    followed you"). Stored as ids + a type rather than rendered text, so the
    actor's CURRENT username and the reader's CURRENT language are used
    whenever it is shown. The row outlives the recipient being offline: it
    is what they see when they come back.

    email_* track the optional email copy (services/notifications.py) --
    private delivery bookkeeping, never returned by the API. Deleting either
    user removes the row (crud.delete_user_cascade_safe)."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    type = Column(String(30), nullable=False)  # follow|duel_challenge|duel_accepted|duel_declined|duel_completed
    duel_id = Column(Integer, ForeignKey("duels.id", ondelete="CASCADE"), nullable=True, index=True)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    email_status = Column(String(12), nullable=False, server_default="pending", default="pending")
    email_attempts = Column(Integer, nullable=False, server_default="0", default=0)
    emailed_at = Column(DateTime, nullable=True)
    # Why the last attempt failed (exception class + SMTP code/text, with
    # credentials and addresses masked), so admins can diagnose delivery
    # from the app instead of from container logs.
    email_error = Column(String(200), nullable=True)
    # When the last attempt ran; the retry sweep backs off from it.
    email_last_attempt_at = Column(DateTime, nullable=True)

    recipient = relationship("User", foreign_keys=[recipient_id])
    actor = relationship("User", foreign_keys=[actor_id])
