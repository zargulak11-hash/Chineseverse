"""Graded activity: voice attempts, practice rounds, HSK exams, story
progress, cached AI explanations, Hanzi tracing and the mistake bank."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from app.database import Base

# ---------------------------------------------------------------------------
# Voice, mistakes
# ---------------------------------------------------------------------------


class VoiceAttempt(Base):
    __tablename__ = "voice_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=True, index=True)
    dialogue_id = Column(Integer, ForeignKey("dialogues.id"), nullable=True, index=True)
    prompt_text = Column(Text, nullable=True)
    spoken_text = Column(Text, nullable=True)
    transcript = Column(Text, nullable=True)
    pronunciation = Column(Float, default=0.0)
    tones = Column(Float, default=0.0)
    fluency = Column(Float, default=0.0)
    grammar = Column(Float, default=0.0)
    relevance = Column(Float, default=0.0)
    response_time_ms = Column(Integer, default=0)
    overall = Column(Float, default=0.0)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="voice_attempts")


class PracticeSession(Base):
    """A server-generated, server-graded practice or review round. `questions`
    holds what was asked ({type, item_type, item_id, option_ids}); `answers`
    is index-aligned ({choice_id, correct, response_ms} or null)."""

    __tablename__ = "practice_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(20), nullable=False)  # vocab|hanzi|grammar|lesson|review
    hsk_level = Column(Integer, nullable=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True)
    questions = Column(JSON, nullable=False)
    answers = Column(JSON, nullable=False)
    score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="practice_sessions")


class HSKExamAttempt(Base):
    """One attempt at an HSK level's final exam (services/hsk_exam.py).

    The server owns everything about it: the questions it built
    ({type, item_type, item_id, option_ids} -- the browser only ever gets
    option ids and labels), the answers (option ids), the clock
    (expires_at), the status and the score. status:
      in_progress -> passed | failed     (submitted, graded on the server)
      in_progress -> invalidated         (left / hid / reopened the exam: 0)
      in_progress -> expired             (time ran out unsubmitted: 0)
    At most one in_progress attempt per user (partial unique index), so two
    tabs can never hold two live attempts."""

    __tablename__ = "hsk_exam_attempts"
    __table_args__ = (
        Index(
            "uq_exam_one_active_per_user", "user_id", unique=True,
            postgresql_where=text("status = 'in_progress'"), sqlite_where=text("status = 'in_progress'"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    level = Column(Integer, nullable=False, index=True)  # display level 1-9
    status = Column(String(20), nullable=False, default="in_progress")
    questions = Column(JSON, nullable=False)
    answers = Column(JSON, nullable=False)
    total = Column(Integer, nullable=False, default=0)
    correct = Column(Integer, nullable=True)
    score = Column(Float, nullable=True)
    violations = Column(JSON, nullable=False, default=list)  # [{reason, at}]
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    # Last sign of life from the exam page (start, heartbeat, answer). Silence
    # longer than hsk_exam.PRESENCE_TIMEOUT ends the attempt with 0.
    last_seen_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="exam_attempts")


class StoryProgress(Base):
    """One learner's reading of one Chinese Stories book (services/stories.py).

    The book itself is a content file (seed_content/books), keyed by slug;
    this row is only what the learner really did with it: where they are
    (chapter/position -- the bookmark "Continue reading" returns to), which
    chapters they finished, and counters of real help they asked for while
    reading (sentences explained, listening, words looked up). Created by
    the first reading action, never by opening the library."""

    __tablename__ = "story_progress"
    __table_args__ = (UniqueConstraint("user_id", "slug", name="uq_story_progress"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    slug = Column(String(60), nullable=False, index=True)
    chapter = Column(Integer, nullable=False, default=0)      # current chapter, 0-based
    position = Column(Integer, nullable=False, default=0)     # sentence index inside it
    chapters_done = Column(JSON, nullable=False, default=list)  # 0-based chapter indexes
    explained = Column(Integer, nullable=False, default=0)
    listened = Column(Integer, nullable=False, default=0)
    looked_up = Column(JSON, nullable=False, default=dict)    # {word_id: times}
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="story_progress")


class AIExplanation(Base):
    """A cached AI reading explanation of one Chinese text (services/stories.py).

    Keyed by what the explanation depends on -- the text, the kind of help,
    the learner's language and level band -- and nothing about the person,
    so one learner's request can safely answer the next learner's identical
    one without a second paid call."""

    __tablename__ = "ai_explanations"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(64), nullable=False, unique=True, index=True)
    kind = Column(String(20), nullable=False)
    locale = Column(String(5), nullable=False)
    text = Column(Text, nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class HanziTraceAttempt(Base):
    """One stroke-order tracing quiz on one character (routers/hanzi.py).

    Issued by the server when the quiz starts and spent by the single
    POST /hanzi/{id}/write that reports it, whatever its outcome, so a
    recorded trace can't be replayed and a forged one can't be retried on
    the same attempt. The server re-checks every drawn stroke against the
    character's stroke data (services/stroke_match.py) and decides the
    mistake count itself. status: open -> counted | rejected | expired."""

    __tablename__ = "hanzi_trace_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    hanzi_id = Column(Integer, ForeignKey("hanzi.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="open")
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    total_mistakes = Column(Integer, nullable=True)

    user = relationship("User", back_populates="trace_attempts")


class LearningMistake(Base):
    __tablename__ = "learning_mistakes"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "mistake_type", "reference", name="uq_user_mistake"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    mistake_type = Column(String(30), nullable=False)  # word|tone|grammar|character|pinyin
    reference = Column(String(300), nullable=False)
    question_text = Column(Text, nullable=True)
    answer_given = Column(String(300), nullable=True)
    correct_answer = Column(String(300), nullable=True)
    priority = Column(Integer, default=1)
    occurrences = Column(Integer, default=1)
    # Spaced-repetition schedule (mirrors UserVocabulary.next_review_at,
    # which was already written by vocab.py but never had an equivalent
    # here) — set by record_mistake()/reinforce_mistake() in gamification.py.
    next_review_at = Column(DateTime, nullable=True)
    mastered = Column(Boolean, default=False)
    mastered_at = Column(DateTime, nullable=True)
    last_seen_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="learning_mistakes")
