from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

PROGRESS_STATUSES = ("not_started", "in_progress", "completed")
MISTAKE_TYPES = ("word", "tone", "grammar", "character", "pinyin")
QUIZ_STATUSES = ("new", "learning", "reviewing", "mastered")
SCENARIO_TYPES = ("conversation", "mission", "case", "practice")


# --------------------------------------------------------------------------- Auth
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    native_language: str = Field(default="English", max_length=50)
    daily_goal_minutes: int = Field(default=10, ge=5, le=240)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


# --------------------------------------------------------------------------- User
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    animal_id: Optional[int] = None


class UserUpdate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    animal_id: Optional[int] = None


class UserPatch(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)
    animal_id: Optional[int] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    animal_id: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(BaseModel):
    native_language: str
    goal_text: Optional[str] = None
    daily_goal_minutes: int
    avatar_color: str
    bio: Optional[str] = None
    level_test_score: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class StreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    total_active_days: int
    last_active_date: Optional[date]

    model_config = ConfigDict(from_attributes=True)


class MeResponse(BaseModel):
    user: UserResponse
    profile: UserProfileResponse
    streak: StreakResponse


# --------------------------------------------------------------------------- Token
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# --------------------------------------------------------------------------- Animal
class AnimalCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    species: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    image_url: Optional[str] = None
    accent_color: Optional[str] = None
    personality: Optional[str] = None
    tone_style: Optional[str] = None
    preferred_mechanics: Optional[str] = None
    special_ability: Optional[str] = None


class AnimalUpdate(BaseModel):
    slug: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    species: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    image_url: Optional[str] = None
    accent_color: Optional[str] = None
    personality: Optional[str] = None
    tone_style: Optional[str] = None
    preferred_mechanics: Optional[str] = None
    special_ability: Optional[str] = None


class AnimalPatch(BaseModel):
    slug: Optional[str] = Field(default=None, min_length=1, max_length=50)
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    species: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    image_url: Optional[str] = None
    accent_color: Optional[str] = None
    personality: Optional[str] = None
    tone_style: Optional[str] = None
    preferred_mechanics: Optional[str] = None
    special_ability: Optional[str] = None


class AnimalPersonalityResponse(BaseModel):
    traits: Optional[str]
    energy: int
    humor: int
    patience: int
    strictness: int
    catchphrase: Optional[str]
    chat_style: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class AnimalResponse(BaseModel):
    id: int
    slug: str
    name: str
    species: str
    description: Optional[str]
    image_url: Optional[str]
    accent_color: Optional[str]
    personality: Optional[str]
    tone_style: Optional[str]
    preferred_mechanics: Optional[str]
    special_ability: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class AnimalDetailResponse(AnimalResponse):
    personality_row: Optional[AnimalPersonalityResponse] = None


class UserAnimalResponse(BaseModel):
    animal_id: int
    bond_level: int
    bond_points: int
    interactions: int

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- HSK / Skills
class SkillResponse(BaseModel):
    id: int
    code: str
    name: str
    category: str
    description: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class HSKLevelResponse(BaseModel):
    id: int
    level: int
    title: str
    description: Optional[str]
    total_vocab_target: int
    mastery_to_unlock_next: float

    model_config = ConfigDict(from_attributes=True)


class SkillMasteryResponse(BaseModel):
    code: str
    name: str
    mastery: float
    xp: int
    status: str  # strong | developing | weak

    model_config = ConfigDict(from_attributes=True)


class DNASummaryResponse(BaseModel):
    overall: float
    skills: list[SkillMasteryResponse]
    weak_areas: list[str]
    strong_areas: list[str]


class HSKLevelProgress(BaseModel):
    level: int
    status: str  # locked | current | unlocked
    vocab_mastered: int
    vocab_total: int
    mastery: float
    lessons_completed: int
    ready_for_next: bool
    reason: Optional[str] = None


class HSKRoadmapResponse(BaseModel):
    levels: list[HSKLevelProgress]
    current_level: int
    overall_mastery: float
    note: str = (
        "Estimates your HSK preparation readiness. LinguaVerse is not affiliated "
        "with the official HSK exam."
    )


# --------------------------------------------------------------------------- Lesson / Progress
class LessonCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: Optional[str] = None
    hsk_level: int = Field(default=1, ge=1, le=6)
    order_index: int = Field(default=0, ge=0)
    lesson_type: str = Field(default="lesson", max_length=30)


class LessonUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: Optional[str] = None
    hsk_level: int = Field(ge=1, le=6)
    order_index: int = Field(ge=0)
    lesson_type: str = Field(max_length=30)


class LessonPatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    content: Optional[str] = None
    hsk_level: Optional[int] = Field(default=None, ge=1, le=6)
    order_index: Optional[int] = Field(default=None, ge=0)
    lesson_type: Optional[str] = Field(default=None, max_length=30)


class LessonResponse(BaseModel):
    id: int
    hsk_level: Optional[int]
    title: str
    summary: Optional[str]
    content: Optional[str]
    lesson_type: str
    order_index: int

    model_config = ConfigDict(from_attributes=True)


class ProgressCreate(BaseModel):
    user_id: int
    lesson_id: int
    status: str = Field(default="not_started", max_length=20)
    score: Optional[int] = Field(default=None, ge=0, le=100)

    @field_validator("status")
    @classmethod
    def check_status(cls, v: str) -> str:
        if v not in PROGRESS_STATUSES:
            raise ValueError(f"status must be one of {', '.join(PROGRESS_STATUSES)}")
        return v


class ProgressUpdate(BaseModel):
    status: str = Field(max_length=20)
    score: Optional[int] = Field(default=None, ge=0, le=100)

    @field_validator("status")
    @classmethod
    def check_status(cls, v: str) -> str:
        if v not in PROGRESS_STATUSES:
            raise ValueError(f"status must be one of {', '.join(PROGRESS_STATUSES)}")
        return v


class ProgressPatch(BaseModel):
    status: Optional[str] = Field(default=None, max_length=20)
    score: Optional[int] = Field(default=None, ge=0, le=100)

    @field_validator("status")
    @classmethod
    def check_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in PROGRESS_STATUSES:
            raise ValueError(f"status must be one of {', '.join(PROGRESS_STATUSES)}")
        return v


class ProgressResponse(BaseModel):
    id: int
    user_id: int
    lesson_id: int
    status: str
    score: Optional[int]
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- Vocabulary / Grammar
class WordResponse(BaseModel):
    id: int
    hsk_level_id: int
    simplified: str
    traditional: Optional[str]
    pinyin: str
    meanings: Optional[str]
    word_type: str
    example: Optional[str]
    example_pinyin: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class WordWithStatus(WordResponse):
    status: Optional[str] = None
    mastery: Optional[float] = None


class GrammarTopicResponse(BaseModel):
    id: int
    hsk_level_id: int
    title: str
    pattern: Optional[str]
    explanation: Optional[str]
    examples: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- World
class LocationResponse(BaseModel):
    id: int
    slug: str
    name: str
    kind: str
    description: Optional[str]
    unlock_level: int
    unlock_skill_mastery: float
    position_x: int
    position_y: int
    icon: str
    accent: str
    status: Optional[str] = None  # unlocked | locked (computed)

    model_config = ConfigDict(from_attributes=True)


class NPCBrief(BaseModel):
    id: int
    name: str
    role: Optional[str]
    title: Optional[str]
    description: Optional[str]
    avatar_url: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class DialogueChoiceResponse(BaseModel):
    id: int
    label: str
    response_text: Optional[str]
    is_best: bool
    feedback: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class DialogueResponse(BaseModel):
    id: int
    turn_index: int
    speaker: str
    text: str
    pinyin: Optional[str]
    english: Optional[str]
    prompt: Optional[str]
    expected_keywords: Optional[list]
    requires_voice: bool
    reactions: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class ScenarioResponse(BaseModel):
    id: int
    slug: str
    title: str
    scenario_type: str
    description: Optional[str]
    min_hsk_level: int
    difficulty: int
    is_case: bool
    requires_voice: bool
    order_index: int
    dialogues: list[DialogueResponse] = []
    status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LocationDetailResponse(LocationResponse):
    npcs: list[NPCBrief] = []
    scenarios: list[ScenarioResponse] = []

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- Missions
class MissionResponse(BaseModel):
    id: int
    slug: str
    title: str
    objective: Optional[str]
    kind: str
    min_hsk_level: int
    reward_xp: int
    reward_coins: int
    target_count: int
    scenario_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class UserMissionResponse(BaseModel):
    id: int
    mission: MissionResponse
    status: str
    progress: int
    completed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class MissionProgressUpdate(BaseModel):
    status: Optional[str] = Field(default=None, max_length=20)
    delta: int = Field(default=0, ge=0, le=100)


# --------------------------------------------------------------------------- Voice
class VoiceAttemptCreate(BaseModel):
    spoken_text: str = Field(min_length=1, max_length=1000)
    prompt_text: Optional[str] = None
    scenario_id: Optional[int] = None
    dialogue_id: Optional[int] = None
    expected_keywords: Optional[list] = None
    response_time_ms: int = Field(default=0, ge=0)

    @field_validator("spoken_text")
    @classmethod
    def strip_spoken(cls, v: str) -> str:
        return v.strip()


class VoiceAttemptResponse(BaseModel):
    id: int
    prompt_text: Optional[str]
    spoken_text: Optional[str]
    pronunciation: float
    tones: float
    fluency: float
    grammar: float
    relevance: float
    response_time_ms: int
    overall: float
    feedback: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VoiceResultResponse(BaseModel):
    attempt: VoiceAttemptResponse
    reaction: str
    skill_delta: dict[str, float]
    improvement: Optional[str] = None


# --------------------------------------------------------------------------- Mistakes
class MistakeResponse(BaseModel):
    id: int
    mistake_type: str
    reference: str
    question_text: Optional[str]
    answer_given: Optional[str]
    correct_answer: Optional[str]
    priority: int
    occurrences: int
    mastered: bool
    mastered_at: Optional[datetime]
    last_seen_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class MistakePatch(BaseModel):
    mastered: Optional[bool] = None


# --------------------------------------------------------------------------- DNA / HSK derived
class DuelCreate(BaseModel):
    opponent_username: str = Field(min_length=1, max_length=50)
    challenge_type: Optional[str] = None  # None = pick weakest


class DuelAnswer(BaseModel):
    index: int = Field(ge=0)
    answer: str = Field(min_length=1, max_length=200)
    response_time_ms: int = Field(default=1000, ge=0)


class DuelQuestion(BaseModel):
    index: int
    type: str
    prompt: str
    options: Optional[list] = None


class DuelResponse(BaseModel):
    id: int
    status: str
    challenge_type: Optional[str]
    questions: list[DuelQuestion] = []
    opponent: Optional[str] = None
    my_score: Optional[int] = None
    opp_score: Optional[int] = None
    finished: bool = False
    winner: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AchievementResponse(BaseModel):
    id: int
    code: str
    title: str
    description: Optional[str]
    icon: str
    category: str
    unlocked: bool = False
    unlocked_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class QuestResponse(BaseModel):
    id: int
    quest_date: date
    quest_type: str
    title: str
    description: Optional[str]
    target: int
    progress: int
    completed: bool
    reward_xp: int
    reward_coins: int
    flavor: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class CaseSolveRequest(BaseModel):
    conclusion: str = Field(min_length=1, max_length=500)


class CaseSummary(BaseModel):
    scenario_id: int
    title: str
    description: str
    case_data: Optional[dict] = None


class DashboardResponse(BaseModel):
    user: UserResponse
    animal: Optional[AnimalResponse] = None
    hsk_level: int
    mastery: float
    dna: DNASummaryResponse
    streak: StreakResponse
    daily_goal: dict
    recommended_mission: Optional[MissionResponse] = None
    recent_mistakes: list[MistakeResponse] = []
    next_location: Optional[LocationResponse] = None
    quests_today: list[QuestResponse] = []
    achievements: list[AchievementResponse] = []