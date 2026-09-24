from datetime import date, datetime

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
    Table,
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
    animal_id = Column(Integer, ForeignKey("animals.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    total_xp = Column(Integer, nullable=False, server_default="0", default=0)
    coins = Column(Integer, nullable=False, server_default="0", default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

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
    # stroke path/median vector data (for a future tracing UI); recognition
    # features never depend on this being present.
    stroke_data = Column(JSON, nullable=True)
    order_index = Column(Integer, default=0)

    level = relationship("HSKLevel", back_populates="hanzi")
    user_records = relationship("UserHanzi", back_populates="hanzi")


class UserHanzi(Base):
    """Recognition-mastery tracking only. There is no writing/tracing UI yet
    (see Hanzi.stroke_data), so no writing-mastery field is populated here --
    that would falsely claim "handwriting mastered" for a character the user
    only ever saw, which the project's data-integrity rules forbid."""

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


# ---------------------------------------------------------------------------
# Duels
# ---------------------------------------------------------------------------


class Duel(Base):
    __tablename__ = "duels"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(20), default="open")  # open|active|finished|aborted
    challenge_type = Column(String(30), nullable=True)
    question_data = Column(JSON, nullable=True)
    winner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    participants = relationship(
        "DuelParticipant", back_populates="duel", cascade="all, delete-orphan"
    )


class DuelParticipant(Base):
    __tablename__ = "duel_participants"
    __table_args__ = (UniqueConstraint("duel_id", "user_id", name="uq_duel_user"),)

    id = Column(Integer, primary_key=True, index=True)
    duel_id = Column(Integer, ForeignKey("duels.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(20), default="challenger")
    score = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    answered = Column(Integer, default=0)
    finished = Column(Boolean, default=False)

    duel = relationship("Duel", back_populates="participants")
    user = relationship("User", back_populates="participants")


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


# ---------------------------------------------------------------------------
# Localization — one generic table for every translatable DB-driven string,
# instead of a locale column bolted onto each content table (which would
# mean a migration per table per language) or a duplicate table per
# language (explicitly ruled out). `content_key` is the row's own primary
# key as a string for normal content (lesson id, mission id, ...), or a
# stable code for content that isn't a single DB row (e.g. a quest
# template, keyed by its quest_type). English is never stored here — it's
# always the original column value, which callers use as the fallback.
# ---------------------------------------------------------------------------


class ContentTranslation(Base):
    __tablename__ = "content_translations"
    __table_args__ = (
        UniqueConstraint("content_type", "content_key", "field", "locale", name="uq_content_translation"),
    )

    id = Column(Integer, primary_key=True, index=True)
    content_type = Column(String(40), nullable=False, index=True)  # "lesson", "vocab_word", "quest_template", ...
    content_key = Column(String(40), nullable=False, index=True)   # str(row.id) or a stable code
    field = Column(String(40), nullable=False)                     # "title", "description", "meanings", ...
    locale = Column(String(5), nullable=False)                     # "ru" | "tg" | "zh"
    text = Column(Text, nullable=False)