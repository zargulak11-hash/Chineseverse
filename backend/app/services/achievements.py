"""Achievements: milestones read from the learner's own records.

Every rule here is judged on the same ground truth the rest of the app
already stores for real learning events -- completed practice rounds by
source (lessons, review, stories, Real Chinese, Detective, Sound World,
Chinese Internet, sentence, tones), graded answers by what the question
tests (the Passport's READING/LISTENING sets), word and character mastery,
counted stroke-tracing quizzes, voice turns, passed HSK exams and the
streak. Nothing is unlocked for opening a page, and no progress number is
invented: `value` is always a count (or a percentage) of stored rows.

Why the rules live in code and not in `achievements.criteria`: the old
criteria dispatcher drifted from the data it claimed to read --
"locations_unlocked" was a hardcoded 1, "mission_count" counted missions
that were merely *active*, "duel_wins" counted any duel with a score above
zero (lost ones too) and "case_count" counted voice turns in a case scene.
A condition is logic, so it is owned by code next to the facts it reads;
the `achievements` table stays the persistence anchor (UserAchievement's
FK) and the seed inserts a row for every code below. Existing unlocks are
never removed, whatever a rule now says.

Unlocking is idempotent: only rules not yet unlocked are evaluated, and a
concurrent request that already inserted the same (user, achievement) pair
hits uq_user_achievement and is rolled back instead of failing the request.
No XP is attached: XP is already earned by the learning itself, and paying
it again for a milestone (retroactively, for everyone who already had the
progress) would double-count it on the leaderboards.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
from typing import Callable

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models


@dataclass(frozen=True)
class Rule:
    code: str
    category: str   # start | words | characters | listening | speaking | reading | stories | review
                    # | places | hsk | habit | companion | world
    icon: str       # stored on the row; the UI draws its own line icon per category
    metric: Callable[["Facts"], float]
    target: int
    unit: str       # what is counted: words, chars, lessons, rounds, answers, ... (UI wording only)
    to: str         # where to go to work on it
    title: str      # English fallback; the UI translates by code. For codes that
                    # predate this module it stays the originally seeded text, which
                    # the curriculum snapshot's ru/tg/zh translations belong to.
    description: str


class Facts:
    """Lazy, per-request view of the learner's records. Each fact runs its
    query only when a still-locked rule asks for it, so once the first steps
    are behind a learner, checking them costs nothing."""

    def __init__(self, db: Session, user: models.User):
        self.db = db
        self.user = user

    @cached_property
    def _rounds(self) -> list[tuple[str, datetime, float | None, list, list]]:
        rows = (self.db.query(models.PracticeSession.source, models.PracticeSession.completed_at,
                              models.PracticeSession.score, models.PracticeSession.questions,
                              models.PracticeSession.answers)
                .filter(models.PracticeSession.user_id == self.user.id,
                        models.PracticeSession.completed_at.isnot(None))
                .all())
        return [tuple(r) for r in rows]

    def rounds(self, source: str) -> int:
        return sum(1 for r in self._rounds if r[0] == source)

    @cached_property
    def review_days(self) -> int:
        return len({r[1].date() for r in self._rounds if r[0] == "review"})

    @cached_property
    def detective_solved(self) -> int:
        # Same "solved" the Passport uses: the case's final deduction was right.
        return sum(1 for r in self._rounds if r[0] == "detective" and r[4] and r[4][-1] and r[4][-1].get("correct"))

    @cached_property
    def _correct_by_kind(self) -> dict[str, int]:
        from app.services.passport import LISTENING, READING

        out = {"reading": 0, "listening": 0}
        # Answers of unfinished rounds count too: each one was graded by the server.
        rows = (self.db.query(models.PracticeSession.questions, models.PracticeSession.answers)
                .filter(models.PracticeSession.user_id == self.user.id).all())
        for questions, answers in rows:
            for q, a in zip(questions or [], answers or []):
                if not a or not a.get("correct"):
                    continue
                qtype = (q or {}).get("type")
                if qtype in READING:
                    out["reading"] += 1
                if qtype in LISTENING:
                    out["listening"] += 1
        return out

    @property
    def reading_correct(self) -> int:
        return self._correct_by_kind["reading"]

    @property
    def listening_correct(self) -> int:
        return self._correct_by_kind["listening"]

    @cached_property
    def lessons(self) -> int:
        return self.db.query(models.Progress).filter_by(user_id=self.user.id, status="completed").count()

    # A word or character counts as learned once it was answered correctly
    # in graded practice and hasn't since slipped back to zero mastery.
    @cached_property
    def words_learned(self) -> int:
        return (self.db.query(models.UserVocabulary)
                .filter(models.UserVocabulary.user_id == self.user.id, models.UserVocabulary.mastery > 0).count())

    @cached_property
    def words_mastered(self) -> int:
        return self.db.query(models.UserVocabulary).filter_by(user_id=self.user.id, status="mastered").count()

    @cached_property
    def hanzi_learned(self) -> int:
        return (self.db.query(models.UserHanzi)
                .filter(models.UserHanzi.user_id == self.user.id, models.UserHanzi.mastery > 0).count())

    @cached_property
    def traces(self) -> int:
        return self.db.query(models.HanziTraceAttempt).filter_by(user_id=self.user.id, status="counted").count()

    @cached_property
    def voice(self) -> int:
        return self.db.query(models.VoiceAttempt).filter_by(user_id=self.user.id).count()

    @cached_property
    def tone_average(self) -> float:
        """Average tone score, only once there are enough attempts for an
        average to mean anything (one lucky turn used to unlock it)."""
        n, avg = (self.db.query(func.count(models.VoiceAttempt.id), func.avg(models.VoiceAttempt.tones))
                  .filter(models.VoiceAttempt.user_id == self.user.id).one())
        return float(avg or 0) if n >= 5 else 0.0

    def scenario_turns(self, slug: str) -> int:
        scenario = self.db.query(models.Scenario).filter_by(slug=slug).first()
        if scenario is None:
            return 0
        return self.db.query(models.VoiceAttempt).filter_by(user_id=self.user.id, scenario_id=scenario.id).count()

    @cached_property
    def stories_read(self) -> int:
        from app.services import stories

        return len(stories.read_slugs(self.db, self.user))

    @cached_property
    def exams_passed(self) -> set[int]:
        return {lvl for (lvl,) in self.db.query(models.HSKExamAttempt.level)
                .filter_by(user_id=self.user.id, status="passed")}

    @cached_property
    def rank(self) -> tuple[int, float]:
        from app.services.gamification import user_rank

        return user_rank(self.db, self.user)

    @cached_property
    def locations_unlocked(self) -> int:
        # The World map's own rule (gamification.location_status).
        level = self.rank[0]
        return self.db.query(models.Location).filter(models.Location.unlock_level <= level).count()

    @cached_property
    def best_streak(self) -> int:
        s = self.user.streak
        return max(s.longest_streak or 0, s.current_streak or 0) if s else 0

    @cached_property
    def active_days(self) -> int:
        return (self.user.streak.total_active_days or 0) if self.user.streak else 0

    @cached_property
    def duel_wins(self) -> int:
        return (self.db.query(models.Duel)
                .filter(models.Duel.winner_id == self.user.id, models.Duel.finished_at.isnot(None)).count())

    @cached_property
    def missions_completed(self) -> int:
        return self.db.query(models.UserMission).filter_by(user_id=self.user.id, status="completed").count()

    @cached_property
    def mistakes_mastered(self) -> int:
        return (self.db.query(models.LearningMistake)
                .filter(models.LearningMistake.user_id == self.user.id,
                        models.LearningMistake.mastered.is_(True)).count())

    @cached_property
    def taught(self) -> int:
        return self.db.query(models.UserTaughtFact).filter_by(user_id=self.user.id).count()

    @property
    def bond_level(self) -> int:
        return self.user.user_animal.bond_level if self.user.user_animal else 0


def _hsk_mastery(level: int):
    def metric(f: Facts) -> float:
        current, overall = f.rank
        return overall if current >= level else 0.0
    return metric


def _exam(level: int):
    return lambda f: 1 if level in f.exams_passed else 0


R = Rule
# Order = how the page lists them inside each group (first steps first).
CATALOG: tuple[Rule, ...] = (
    # --- first steps: the beginner journey, one real action each
    R("first_lesson", "start", "📘", lambda f: f.lessons, 1, "lessons", "/lessons",
      "First Lesson", "Complete your first lesson."),
    R("first_word", "start", "🌱", lambda f: f.words_learned, 1, "words", "/practice?source=vocab&level=1",
      "First Word", "Learn your first Chinese word."),
    R("first_hanzi", "start", "字", lambda f: f.hanzi_learned, 1, "chars", "/practice?source=hanzi&level=1",
      "First Character", "Learn your first Chinese character."),
    R("first_trace", "start", "🖌️", lambda f: f.traces, 1, "traces", "/hanzi",
      "First Strokes", "Trace your first character stroke by stroke."),
    R("first_tones", "start", "🎶", lambda f: f.rounds("tones"), 1, "rounds", "/foundation",
      "Four Tones", "Finish your first tones round."),
    R("first_sentence", "start", "🧩", lambda f: f.rounds("sentence"), 1, "rounds", "/sentence",
      "First Sentence", "Finish your first sentence lesson."),
    R("first_listening", "start", "👂", lambda f: f.listening_correct, 1, "answers", "/sound-world",
      "First Listen", "Understand Chinese by ear for the first time."),
    R("first_voice", "start", "🎙️", lambda f: f.voice, 1, "turns", "/real-chinese/talk/greet-grandma",
      "First Spoken Conversation", "Complete your first voice turn."),
    R("first_story", "start", "📖", lambda f: f.rounds("story"), 1, "stories", "/stories",
      "First Story", "Read your first Chinese story."),
    R("first_review", "start", "🔁", lambda f: f.rounds("review"), 1, "rounds", "/review",
      "First Review", "Finish your first review round."),
    R("first_real_chinese", "places", "🏙️", lambda f: f.rounds("scene"), 1, "rounds", "/real-chinese",
      "Into Real Chinese", "Finish your first Real Chinese scene."),
    R("case_solver", "places", "🕵️", lambda f: f.rounds("detective"), 1, "cases", "/detective",
      "Case Solver", "Solve your first Chinese case."),
    R("first_sound_world", "places", "🔊", lambda f: f.rounds("sound"), 1, "rounds", "/sound-world",
      "Sound Explorer", "Finish your first Sound World round."),
    R("first_internet", "places", "🌐", lambda f: f.rounds("internet"), 1, "rounds", "/internet",
      "Online in Chinese", "Finish your first Chinese Internet round."),
    # --- milestones
    R("words_10", "words", "🌿", lambda f: f.words_learned, 10, "words", "/vocabulary",
      "10 Words", "Learn 10 Chinese words."),
    R("words_50", "words", "🌳", lambda f: f.words_learned, 50, "words", "/vocabulary",
      "50 Words", "Learn 50 Chinese words."),
    R("words_150", "words", "🏞️", lambda f: f.words_learned, 150, "words", "/vocabulary",
      "150 Words", "Learn 150 Chinese words."),
    R("words_100", "words", "💯", lambda f: f.words_mastered, 100, "words", "/review",
      "100 Words Mastered", "Master 100 vocabulary words."),
    R("hanzi_25", "characters", "🀄", lambda f: f.hanzi_learned, 25, "chars", "/hanzi",
      "25 Characters", "Learn 25 Chinese characters."),
    R("hanzi_100", "characters", "🏯", lambda f: f.hanzi_learned, 100, "chars", "/hanzi",
      "100 Characters", "Learn 100 Chinese characters."),
    R("traces_10", "characters", "✍️", lambda f: f.traces, 10, "traces", "/hanzi",
      "Steady Hand", "Trace 10 characters stroke by stroke."),
    R("listening_50", "listening", "🎧", lambda f: f.listening_correct, 50, "answers", "/sound-world",
      "Good Ears", "Answer 50 listening questions correctly."),
    R("listening_200", "listening", "📻", lambda f: f.listening_correct, 200, "answers", "/sound-world",
      "Sharp Ears", "Answer 200 listening questions correctly."),
    R("speaking_10", "speaking", "🗣️", lambda f: f.voice, 10, "turns", "/real-chinese",
      "Finding Your Voice", "Speak Chinese out loud 10 times."),
    R("speaking_50", "speaking", "📣", lambda f: f.voice, 50, "turns", "/real-chinese",
      "Confident Speaker", "Speak Chinese out loud 50 times."),
    R("tone_master", "speaking", "🎵", lambda f: f.tone_average, 80, "percent", "/foundation",
      "Tone Master", "Reach 80 tone accuracy across voice attempts."),
    R("restaurant_survivor", "speaking", "🍜", lambda f: f.scenario_turns("ordering-noodles"), 1, "turns", "/world",
      "Restaurant Survivor", "Complete the ordering-noodles scenario."),
    R("reading_50", "reading", "📰", lambda f: f.reading_correct, 50, "answers", "/practice?source=vocab&level=1",
      "Reader", "Answer 50 reading questions correctly."),
    R("reading_200", "reading", "📚", lambda f: f.reading_correct, 200, "answers", "/internet",
      "Bookworm", "Answer 200 reading questions correctly."),
    R("stories_3", "stories", "📗", lambda f: f.stories_read, 3, "stories", "/stories",
      "Story Lover", "Read 3 different Chinese stories."),
    R("stories_10", "stories", "📚", lambda f: f.stories_read, 10, "stories", "/stories",
      "Library Card", "Read 10 different Chinese stories."),
    R("detective_5", "places", "🔎", lambda f: f.detective_solved, 5, "cases", "/detective",
      "Master Detective", "Solve 5 Detective cases correctly."),
    R("lessons_5", "hsk", "📙", lambda f: f.lessons, 5, "lessons", "/lessons",
      "Five Lessons", "Complete 5 lessons."),
    R("lessons_20", "hsk", "🎓", lambda f: f.lessons, 20, "lessons", "/lessons",
      "Twenty Lessons", "Complete 20 lessons."),
    R("hsk1_exam", "hsk", "🥉", _exam(1), 1, "exams", "/roadmap",
      "HSK 1 Passed", "Pass the HSK 1 exam."),
    R("hsk2_mastery", "hsk", "🏮", _hsk_mastery(2), 80, "percent", "/roadmap",
      "HSK 2 Mastery", "Reach 80% mastery on HSK 2 skills."),
    R("hsk3_exam", "hsk", "🥈", _exam(3), 1, "exams", "/roadmap",
      "HSK 3 Passed", "Pass the HSK 3 exam."),
    R("hsk6_exam", "hsk", "🥇", _exam(6), 1, "exams", "/roadmap",
      "HSK 6 Passed", "Pass the HSK 6 exam."),
    R("reviews_10", "review", "🔄", lambda f: f.rounds("review"), 10, "rounds", "/review",
      "Review Habit", "Finish 10 review rounds."),
    R("review_days_7", "review", "🗓️", lambda f: f.review_days, 7, "days", "/review",
      "Never Forget", "Review on 7 different days."),
    R("mistakes_10", "review", "🎯", lambda f: f.mistakes_mastered, 10, "mistakes", "/mistakes",
      "Mistake Hunter", "Master 10 recorded mistakes."),
    R("streak_3", "habit", "✨", lambda f: f.best_streak, 3, "days", "/dashboard",
      "3-Day Streak", "Learn 3 days in a row."),
    R("streak_7", "habit", "🔥", lambda f: f.best_streak, 7, "days", "/dashboard",
      "7-Day Streak", "Keep a 7-day learning streak."),
    R("streak_30", "habit", "🌕", lambda f: f.best_streak, 30, "days", "/dashboard",
      "30-Day Streak", "Learn 30 days in a row."),
    R("active_30", "habit", "📅", lambda f: f.active_days, 30, "days", "/dashboard",
      "Thirty Days of Chinese", "Learn on 30 different days."),
    R("xp_500", "habit", "⭐", lambda f: f.user.total_xp or 0, 500, "xp", "/dashboard",
      "Rising Star", "Earn 500 total XP from quests and missions."),
    R("bond_3", "companion", "🪻", lambda f: f.bond_level, 3, "level", "/companion",
      "Bonded Companion", "Reach bond level 3 with your animal."),
    R("pet_teacher_5", "companion", "🧑‍🏫", lambda f: f.taught, 5, "rules", "/pet-teacher",
      "Patient Teacher", "Teach your companion 5 grammar rules."),
    R("world_4", "world", "🗺️", lambda f: f.locations_unlocked, 4, "places", "/world",
      "City Explorer", "Unlock 4 locations."),
    R("first_mission", "world", "📜", lambda f: f.missions_completed, 1, "missions", "/missions",
      "First Mission", "Complete your first mission."),
    R("duel_win", "world", "⚔️", lambda f: f.duel_wins, 1, "duels", "/duels",
      "First Duel Victory", "Win your first Duel."),
)
BY_CODE = {r.code: r for r in CATALOG}
ORDER = {r.code: i for i, r in enumerate(CATALOG)}


def _value(rule: Rule, facts: Facts) -> float:
    return float(rule.metric(facts) or 0)


def check(db: Session, user: models.User) -> list[models.Achievement]:
    """Unlock every rule the learner's records now satisfy. Returns the
    newly unlocked rows (empty on a lost race -- the other request won)."""
    rows = {a.code: a for a in db.query(models.Achievement).filter(models.Achievement.code.in_(BY_CODE))}
    have = {aid for (aid,) in db.query(models.UserAchievement.achievement_id).filter_by(user_id=user.id)}
    facts = Facts(db, user)
    # Judge every rule before adding anything: some facts (user_rank ->
    # ensure_user_skills) commit, which would otherwise flush a half-built
    # set of unlocks outside the race guard below.
    newly = [rows[r.code] for r in CATALOG
             if r.code in rows and rows[r.code].id not in have and _value(r, facts) >= r.target]
    for row in newly:
        user.user_achievements.append(models.UserAchievement(achievement_id=row.id))
    if newly:
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            db.refresh(user)
            return []
    return newly


def overview(db: Session, user: models.User) -> list[dict]:
    """Every achievement with the learner's real progress, in catalog order.
    Run after check(), so anything already earned is reported unlocked."""
    rows = {a.code: a for a in db.query(models.Achievement).filter(models.Achievement.code.in_(BY_CODE))}
    links = {ua.achievement_id: ua for ua in db.query(models.UserAchievement).filter_by(user_id=user.id)}
    facts = Facts(db, user)
    out = []
    for rule in CATALOG:
        row = rows.get(rule.code)
        if row is None:
            continue
        link = links.get(row.id)
        value = rule.target if link else min(_value(rule, facts), rule.target)
        out.append({"row": row, "rule": rule, "link": link, "progress": int(value)})
    return out


def responses(db: Session, entries: list[dict], locale: str) -> list:
    """overview() entries as AchievementResponse, title/description in the
    learner's language where a translation exists (the UI prefers its own
    strings by code and falls back to these)."""
    from app import schemas
    from app.services.localization import load_translations, tr

    translations = load_translations(db, "achievement", [str(e["row"].id) for e in entries], locale)
    out = []
    for e in entries:
        row, rule, link = e["row"], e["rule"], e["link"]
        item = schemas.AchievementResponse.model_validate(row)
        item.title = tr(translations, row.id, "title", rule.title)
        item.description = tr(translations, row.id, "description", rule.description)
        item.category = rule.category
        item.unlocked = link is not None
        item.unlocked_at = link.unlocked_at if link else None
        item.progress, item.target, item.unit, item.to = e["progress"], rule.target, rule.unit, rule.to
        item.order = ORDER[rule.code]
        out.append(item)
    return out


def closest(entries: list[dict], n: int = 3) -> list[dict]:
    """Locked achievements nearest to done; ties go to the earlier (more
    beginner) one. Untouched ones only count as "close" when they are a
    single step away (a first-time action)."""
    locked = [e for e in entries if e["link"] is None and (e["progress"] > 0 or e["rule"].target == 1)]
    locked.sort(key=lambda e: (-(e["progress"] / e["rule"].target), ORDER[e["rule"].code]))
    return locked[:n]


def mark_seen(db: Session, user: models.User, achievement_ids: list[int]) -> int:
    """Record that the unlock note for these (own, unlocked) achievements was
    shown. Ids that aren't the caller's unlocks are simply ignored."""
    if not achievement_ids:
        return 0
    rows = (db.query(models.UserAchievement)
            .filter(models.UserAchievement.user_id == user.id,
                    models.UserAchievement.achievement_id.in_(achievement_ids),
                    models.UserAchievement.notified_at.is_(None)).all())
    now = datetime.utcnow()
    for r in rows:
        r.notified_at = now
    db.commit()
    return len(rows)


def seed(db: Session) -> None:
    """Insert-only: a row per code. Existing rows (and their translations)
    are left exactly as they are."""
    existing = {code for (code,) in db.query(models.Achievement.code)}
    for rule in CATALOG:
        if rule.code in existing:
            continue
        db.add(models.Achievement(code=rule.code, title=rule.title, description=rule.description,
                                  icon=rule.icon, category=rule.category,
                                  criteria={"rule": rule.code, "target": rule.target}))
