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


class GoogleAuthRequest(BaseModel):
    credential: str = Field(min_length=10)


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
    total_xp: int = 0
    coins: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(BaseModel):
    native_language: str
    goal_text: Optional[str] = None
    daily_goal_minutes: int
    avatar_color: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    level_test_score: Optional[int] = None
    learning_motivation: Optional[str] = None
    learning_motivation_other: Optional[str] = None
    discovery_source: Optional[str] = None
    discovery_source_other: Optional[str] = None
    onboarding_completed: bool = False

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


class PublicUserResponse(BaseModel):
    id: int
    username: str
    animal_id: Optional[int]
    total_xp: int = 0
    avatar_url: Optional[str] = None
    created_at: datetime
    followers_count: int = 0
    following_count: int = 0
    is_following: bool = False
    is_self: bool = False

    model_config = ConfigDict(from_attributes=True)


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
    hanzi_mastered: int = 0
    hanzi_total: int = 0
    grammar_mastered: int = 0
    grammar_total: int = 0
    mastery: float
    lessons_completed: int
    ready_for_next: bool
    reason: Optional[str] = None
    # True for the 3 synthetic HSK 7/8/9 rows: they subdivide ONE shared
    # advanced pool by mastery thirds rather than being independent official
    # levels with their own vocab/hanzi/grammar lists (see HSKLevel.is_advanced_band).
    is_advanced_stage: bool = False


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
    due_for_review: bool = False


class GrammarTopicResponse(BaseModel):
    id: int
    hsk_level_id: int
    title: str
    pattern: Optional[str]
    explanation: Optional[str]
    examples: Optional[str]
    category: Optional[str] = None
    difficulty: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class GrammarTopicWithStatus(GrammarTopicResponse):
    status: Optional[str] = None
    mastery: Optional[float] = None
    due_for_review: bool = False


# --------------------------------------------------------------------------- Hanzi
class HanziResponse(BaseModel):
    id: int
    hsk_level_id: int
    character: str
    pinyin: Optional[str]
    meaning: Optional[str]
    radical: Optional[str]
    decomposition: Optional[str]
    stroke_count: Optional[int]
    handwriting_tier: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class HanziWithStatus(HanziResponse):
    status: Optional[str] = None
    mastery: Optional[float] = None
    due_for_review: bool = False


# --------------------------------------------------------------------------- Pet Teacher
class PetTeacherCaseResponse(BaseModel):
    id: int
    wrong_sentence: str
    hint: Optional[str] = None
    hsk_level: Optional[int] = None
    already_taught: bool = False

    model_config = ConfigDict(from_attributes=True)


class PetTeacherAnswerRequest(BaseModel):
    correction: str = Field(min_length=1, max_length=300)
    explanation: str = Field(min_length=1, max_length=500)


class PetTeacherResultResponse(BaseModel):
    correct_fix: bool
    understood: bool
    success: bool
    correct_sentence: str
    mistake_summary: Optional[str] = None
    feedback: str
    taught_count: int


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
    next_turn: Optional[int]

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
    choices: list[DialogueChoiceResponse] = []

    model_config = ConfigDict(from_attributes=True)


class CaseDataResponse(BaseModel):
    # Deliberately excludes solution_kws/hint from Scenario.case_data —
    # those are the answer, not evidence, and stay server-side until
    # /world/scenarios/{slug}/solve reveals a hint on an actual attempt.
    clues: list[str] = []
    contradiction_text: Optional[str] = None


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
    case_data: Optional[CaseDataResponse] = None
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
    next_review_at: Optional[datetime] = None
    due_for_review: bool = False

    model_config = ConfigDict(from_attributes=True)


class MistakePatch(BaseModel):
    # No client-settable `mastered` — mastery is only ever earned by
    # reinforce_mistake() (answering correctly again via voice/vocab/duel/
    # case), never by a direct PATCH. This just lets the learner bump an
    # item to the front of their review queue.
    request_retest: Optional[bool] = None


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
    tts_text: Optional[str] = None


class PlacementQuestion(BaseModel):
    index: int
    level: int
    type: str
    prompt: str
    options: Optional[list] = None
    tts_text: Optional[str] = None


class PlacementStartResponse(BaseModel):
    attempt_id: int
    questions: list[PlacementQuestion] = []


class PlacementAnswer(BaseModel):
    index: int = Field(ge=0)
    answer: str = Field(min_length=1, max_length=200)


class PlacementSubmitRequest(BaseModel):
    answers: list[PlacementAnswer]


class PlacementResultResponse(BaseModel):
    attempt_id: int
    correct_count: int
    total_count: int
    placed_level: int
    overall_mastery: float


class DuelResponse(BaseModel):
    id: int
    status: str
    challenge_type: Optional[str]
    questions: list[DuelQuestion] = []
    opponent: Optional[str] = None
    is_ai_opponent: bool = True
    my_score: Optional[int] = None
    opp_score: Optional[int] = None
    finished: bool = False
    # True once you've finished your side but a REAL (non-AI) opponent
    # hasn't played yet — the duel stays "active" and unscored for them
    # rather than inventing a result. See duels.py:finish_duel.
    awaiting_opponent: bool = False
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
    claimed: bool = False
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


# --------------------------------------------------------------------------- Activity analytics
class ActivityDayResponse(BaseModel):
    date: date
    minutes: float
    actions: int


class SectionBreakdownResponse(BaseModel):
    section: str
    label: str
    minutes: float
    percent: float


class ActivityAnalyticsResponse(BaseModel):
    total_minutes: float
    today_minutes: float
    today_actions: int
    week_minutes: float
    week_actions: int
    last_week_minutes: float
    last_week_actions: int
    streak: StreakResponse
    best_streak_past_year: int
    total_actions_past_year: int
    sections: list[SectionBreakdownResponse]
    days: list[ActivityDayResponse]


class DashboardResponse(BaseModel):
    user: UserResponse
    avatar_url: Optional[str] = None
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