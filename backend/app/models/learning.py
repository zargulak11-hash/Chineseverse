"""Curriculum content -- lessons, vocabulary, Hanzi, grammar -- and each
learner's mastery of it, plus lesson progress."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base

# ---------------------------------------------------------------------------
# Learning content: lessons, vocabulary, grammar
# ---------------------------------------------------------------------------

lesson_skills = Table(
    "lesson_skills",
    Base.metadata,
    Column("lesson_id", ForeignKey("lessons.id"), primary_key=True),
    Column("skill_id", ForeignKey("skills.id"), primary_key=True),
)


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    hsk_level_id = Column(Integer, ForeignKey("hsk_levels.id"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    summary = Column(String(300), nullable=True)
    content = Column(Text, nullable=True)
    lesson_type = Column(String(30), default="lesson")
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    level = relationship("HSKLevel", back_populates="lessons")
    skills = relationship(
        "Skill", secondary="lesson_skills", back_populates="lessons"
    )
    progress = relationship("Progress", back_populates="lesson")

    @property
    def hsk_level(self):
        return self.level.level if self.level else None


class VocabularyWord(Base):
    __tablename__ = "vocabulary_words"
    __table_args__ = (
        UniqueConstraint("hsk_level_id", "simplified", name="uq_word_level"),
    )

    id = Column(Integer, primary_key=True, index=True)
    hsk_level_id = Column(Integer, ForeignKey("hsk_levels.id"), nullable=False, index=True)
    simplified = Column(String(50), nullable=False)
    traditional = Column(String(50), nullable=True)
    pinyin = Column(String(100), nullable=False)
    meanings = Column(String(300), nullable=True)
    word_type = Column(String(30), default="word")
    example = Column(Text, nullable=True)
    example_pinyin = Column(String(200), nullable=True)

    level = relationship("HSKLevel", back_populates="vocabulary")
    user_records = relationship("UserVocabulary", back_populates="word")


class UserVocabulary(Base):
    __tablename__ = "user_vocabulary"
    __table_args__ = (UniqueConstraint("user_id", "word_id", name="uq_user_word"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    word_id = Column(Integer, ForeignKey("vocabulary_words.id"), nullable=False, index=True)
    status = Column(String(20), default="new")
    mastery = Column(Float, default=0.0)
    times_seen = Column(Integer, default=0)
    times_missed = Column(Integer, default=0)
    last_reviewed_at = Column(DateTime, nullable=True)
    next_review_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="user_vocabulary")
    word = relationship("VocabularyWord", back_populates="user_records")


class Hanzi(Base):
    """A single Chinese character, distinct from VocabularyWord (which may be
    single- or multi-character words). Recognition data (pinyin/meaning/
    stroke order) is sourced for every row; `handwriting_tier` is only set
    when the real HSK 3.0 syllabus requires the character to be handwritten
    at that stage -- it is never inferred from recognition activity alone."""

    __tablename__ = "hanzi"
    __table_args__ = (
        UniqueConstraint("hsk_level_id", "character", name="uq_hanzi_level"),
    )

    id = Column(Integer, primary_key=True, index=True)
    hsk_level_id = Column(Integer, ForeignKey("hsk_levels.id"), nullable=False, index=True)
    character = Column(String(4), nullable=False, index=True)
    pinyin = Column(String(50), nullable=True)
    meaning = Column(String(300), nullable=True)
    radical = Column(String(10), nullable=True)
    decomposition = Column(String(50), nullable=True)
    stroke_count = Column(Integer, nullable=True)
    # null = recognition-only; "elementary"/"intermediate"/"advanced" = the
    # real HSK 3.0 handwriting-syllabus tier this character belongs to.
    handwriting_tier = Column(String(20), nullable=True)
    # real stroke path/median vector data (skishore/makemeahanzi), consumed
    # directly by the HanziWriter quiz for stroke-order tracing practice;
    # recognition features never depend on this being present.
    stroke_data = Column(JSON, nullable=True)
    order_index = Column(Integer, default=0)

    level = relationship("HSKLevel", back_populates="hanzi")
    user_records = relationship("UserHanzi", back_populates="hanzi")


class UserHanzi(Base):
    """Recognition mastery (`mastery`/`status`) and handwriting mastery
    (`writing_mastery`/`writing_status`) are tracked separately and updated
    by different real events: recognition from /hanzi/{id}/review (did you
    recognize the reading/meaning), writing from /hanzi/{id}/write (did you
    correctly trace the real stroke data via the HanziWriter quiz). Neither
    field is ever bumped by the other action -- viewing a character never
    counts as having written it."""

    __tablename__ = "user_hanzi"
    __table_args__ = (UniqueConstraint("user_id", "hanzi_id", name="uq_user_hanzi"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    hanzi_id = Column(Integer, ForeignKey("hanzi.id"), nullable=False, index=True)
    status = Column(String(20), default="new")
    mastery = Column(Float, default=0.0)
    times_seen = Column(Integer, default=0)
    times_missed = Column(Integer, default=0)
    last_reviewed_at = Column(DateTime, nullable=True)
    next_review_at = Column(DateTime, nullable=True)
    # Populated only by a completed HanziWriter stroke quiz (see hanzi.py's
    # /write endpoint) -- never by a recognition review.
    writing_status = Column(String(20), default="not_practiced")
    writing_mastery = Column(Float, default=0.0)
    times_written = Column(Integer, default=0)
    last_written_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="user_hanzi")
    hanzi = relationship("Hanzi", back_populates="user_records")


class GrammarTopic(Base):
    __tablename__ = "grammar_topics"

    id = Column(Integer, primary_key=True, index=True)
    hsk_level_id = Column(Integer, ForeignKey("hsk_levels.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    pattern = Column(String(200), nullable=True)
    explanation = Column(Text, nullable=True)
    examples = Column(Text, nullable=True)
    # word-class / topic grouping from the official syllabus (e.g. "名词",
    # "动词", "补语"), and a difficulty band derived from the HSK level
    # itself (elementary=1-2, intermediate=3-4, advanced=5-9) -- never a
    # per-item guess.
    category = Column(String(100), nullable=True)
    difficulty = Column(String(20), nullable=True)
    order_index = Column(Integer, default=0)

    level = relationship("HSKLevel", back_populates="grammar")
    user_records = relationship("UserGrammar", back_populates="topic")


class UserGrammar(Base):
    __tablename__ = "user_grammar"
    __table_args__ = (UniqueConstraint("user_id", "topic_id", name="uq_user_grammar"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    topic_id = Column(Integer, ForeignKey("grammar_topics.id"), nullable=False, index=True)
    status = Column(String(20), default="new")
    mastery = Column(Float, default=0.0)
    times_practiced = Column(Integer, default=0)
    times_missed = Column(Integer, default=0)
    last_reviewed_at = Column(DateTime, nullable=True)
    next_review_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="user_grammar")
    topic = relationship("GrammarTopic", back_populates="user_records")


# ---------------------------------------------------------------------------
# Preserved V1 lesson progress
# ---------------------------------------------------------------------------


class Progress(Base):
    __tablename__ = "progress"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="not_started")
    score = Column(Integer, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="progress")
    lesson = relationship("Lesson", back_populates="progress")
