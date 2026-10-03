"""The permanent companion's memory of the learner's journey.

Nothing is stored here and nothing is invented: every memory is read from
rows the app already keeps for real learning events --

  ActivityEvent         days away, last time an area was practised
  UserStreak            the current run of days
  UserVocabulary/Hanzi  items mastered recently, characters missed often
  PracticeSession       confusion pairs (the stored question's target and
                        the option actually picked), listening accuracy over
                        time, reviews completed
  Progress              lessons completed
  LearningMistake       mistakes that keep coming back
  UserAchievement       milestones unlocked
  UserSkill             the weakest Learning DNA skill

A memory is {kind, mood, zh, data, at}: `kind` picks the localized sentence
on the client (companionMemory.kind.*), `data` fills it with the real items
and numbers, and `zh` is the short Chinese line the companion says (never
translated, like a reaction's zh). The companion is always the PERMANENT
one (user.animal_id) -- the Daily Voice Companion has no memory.

Tone rule (same as companion_reaction): struggles are met with support,
never blame.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, time, timedelta

from sqlalchemy.orm import Session

from app import models
from app.services.companion_reaction import companion_of
from app.services.gamification import activity_today, streak_snapshot
from app.services.localization import load_translations, tr

RECENT_DAYS = 7
AWAY_DAYS = 3                   # "welcome back" after this many days without activity
STALE_DAYS = 7                  # an area not practised for this long is "waiting"
CONFUSION_WINDOW_DAYS = 60
WORD_MILESTONES = (10, 25, 50, 100, 200, 300, 500, 1000, 2000)
STREAK_MILESTONES = (3, 7, 14, 30, 60, 100, 200, 365)
# Question types whose options are rows of the same table -- a wrong pick
# there is a real "took A for B" confusion between two curriculum items.
_CONFUSABLE = {"meaning_to_word", "word_to_meaning", "listen_to_word", "char_to_meaning", "char_to_pinyin"}
LISTEN_TYPES = {"listen_to_word", "scene_listen", "sentence_listen"}
_AREA_TYPES = {"vocab": "vocab", "hanzi": "hanzi", "grammar": "grammar"}

ZH = {
    "welcome_back": "欢迎回来！我一直在等你。",
    "new_learner": "我们一起开始学中文吧！",
    "word_milestone": "太棒了！你已经掌握了{n}个词！",
    "streak": "连续{n}天了，真了不起！",
    "achievement": "恭喜你！又有新成就了！",
    "lesson_completed": "这一课你学完了，真棒！",
    "mastered_hard": "这个词以前很难，现在你掌握了！",
    "mastered_recently": "你最近又掌握了新词！",
    "difficult_chars": "这几个字有点难，我们多练习。",
    "confused_pair": "{a}和{b}很像，别着急，慢慢分清楚。",
    "recent_mistakes": "错了没关系，我们一起复习。",
    "improving_listening": "你的听力越来越好了！",
    "reviews_done": "复习做得很好，记忆更牢了！",
    "stale_area": "好久没练{area}了，我们去看看吧。",
    "weak_skill": "我们一起加强这个能力吧。",
    "passport_milestone": "你的中文护照上又多了一页！",
}
_AREA_ZH = {"vocab": "词汇", "hanzi": "汉字", "grammar": "语法"}
PRIORITY = [
    "welcome_back", "passport_milestone", "word_milestone", "achievement", "lesson_completed", "mastered_hard", "streak",
    "improving_listening", "confused_pair", "difficult_chars", "recent_mistakes", "mastered_recently",
    "reviews_done", "stale_area", "weak_skill", "new_learner",
]


def _day_start(d) -> datetime:
    return datetime.combine(d, time.min)


def days_away(db: Session, user: models.User) -> int | None:
    """Whole days between the learner's last activity BEFORE today and today
    (None for someone with no earlier activity at all)."""
    today_start = _day_start(activity_today())
    last = (
        db.query(models.ActivityEvent.created_at)
        .filter(models.ActivityEvent.user_id == user.id, models.ActivityEvent.created_at < today_start)
        .order_by(models.ActivityEvent.created_at.desc())
        .first()
    )
    if last is None:
        return None
    return (activity_today() - last[0].date()).days


def _recent_sessions(db: Session, user: models.User, days: int) -> list[models.PracticeSession]:
    since = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(models.PracticeSession)
        .filter(models.PracticeSession.user_id == user.id, models.PracticeSession.created_at >= since)
        .order_by(models.PracticeSession.created_at)
        .all()
    )


def confusion_pairs(sessions: list[models.PracticeSession], exclude_session: int | None = None) -> Counter:
    """(item_type, smaller_id, larger_id) -> times the learner picked one of
    the two when the other was asked."""
    out: Counter = Counter()
    for s in sessions:
        if s.id == exclude_session:
            continue
        for q, a in zip(s.questions or [], s.answers or []):
            if not a or a.get("correct") or q.get("type") not in _CONFUSABLE:
                continue
            picked, target = a.get("choice_id"), q.get("item_id")
            if picked is None or picked == target:
                continue
            lo, hi = sorted((picked, target))
            out[(q["item_type"], lo, hi)] += 1
    return out


def confusion_count(db: Session, user: models.User, item_type: str, a_id: int, b_id: int,
                    exclude_session: int | None = None) -> int:
    lo, hi = sorted((a_id, b_id))
    return confusion_pairs(_recent_sessions(db, user, CONFUSION_WINDOW_DAYS), exclude_session)[(item_type, lo, hi)]


def _item_label(db: Session, item_type: str, item_id: int) -> dict | None:
    if item_type == "vocab":
        r = db.get(models.VocabularyWord, item_id)
        return {"hanzi": r.simplified, "pinyin": r.pinyin} if r else None
    if item_type == "hanzi":
        r = db.get(models.Hanzi, item_id)
        return {"hanzi": r.character, "pinyin": r.pinyin} if r else None
    return None


def _listening_trend(sessions: list[models.PracticeSession]) -> dict | None:
    """Listening accuracy in the last 7 days vs the 7-30 days before, from
    real graded listening answers. Needs 5+ answers on each side."""
    cut = datetime.utcnow() - timedelta(days=RECENT_DAYS)
    recent, before = [], []
    for s in sessions:
        for q, a in zip(s.questions or [], s.answers or []):
            if a and q.get("type") in LISTEN_TYPES:
                at = datetime.fromisoformat(a["answered_at"]) if a.get("answered_at") else s.created_at
                (recent if at >= cut else before).append(bool(a.get("correct")))
    if len(recent) < 5 or len(before) < 5:
        return None
    r, b = sum(recent) / len(recent) * 100, sum(before) / len(before) * 100
    if r - b < 10:
        return None
    return {"recent": round(r), "before": round(b), "answers": len(recent)}


def _last_answered_by_area(sessions: list[models.PracticeSession]) -> dict[str, datetime]:
    out: dict[str, datetime] = {}
    for s in sessions:
        for q, a in zip(s.questions or [], s.answers or []):
            area = _AREA_TYPES.get(q.get("item_type"))
            if a and area:
                at = datetime.fromisoformat(a["answered_at"]) if a.get("answered_at") else s.created_at
                if area not in out or at > out[area]:
                    out[area] = at
    return out


def _m(kind: str, mood: str, data: dict | None = None, at: datetime | None = None, **fmt) -> dict:
    return {
        "kind": kind, "mood": mood, "zh": ZH[kind].format(**fmt) if fmt else ZH[kind],
        "data": data or {}, "at": at.isoformat() if at else None,
    }


def memories(db: Session, user: models.User, locale: str) -> dict:
    now = datetime.utcnow()
    recent_cut = now - timedelta(days=RECENT_DAYS)
    out: list[dict] = []

    # --- coming back
    away = days_away(db, user)
    active_today = db.query(models.ActivityEvent.id).filter(
        models.ActivityEvent.user_id == user.id,
        models.ActivityEvent.created_at >= _day_start(activity_today())).first() is not None
    if away is not None and away >= AWAY_DAYS:
        out.append(_m("welcome_back", "excited", {"days": away, "active_today": active_today}))

    # --- milestones: words mastered, streak, achievements
    mastered_words = (
        db.query(models.UserVocabulary)
        .filter(models.UserVocabulary.user_id == user.id, models.UserVocabulary.status == "mastered")
        .all()
    )
    total = len(mastered_words)
    before = sum(1 for r in mastered_words if r.last_reviewed_at and r.last_reviewed_at < recent_cut)
    crossed = [m for m in WORD_MILESTONES if before < m <= total]
    if crossed:
        out.append(_m("word_milestone", "celebrating", {"count": crossed[-1], "total": total}, n=crossed[-1]))

    streak = streak_snapshot(user.streak)["current_streak"]
    if streak >= 3:
        hit = max((m for m in STREAK_MILESTONES if m <= streak), default=None)
        out.append(_m("streak", "celebrating" if hit == streak else "excited",
                      {"days": streak, "milestone": hit == streak}, n=streak))

    new_ach = (
        db.query(models.UserAchievement)
        .filter(models.UserAchievement.user_id == user.id, models.UserAchievement.unlocked_at >= recent_cut)
        .order_by(models.UserAchievement.unlocked_at.desc())
        .all()
    )
    if new_ach:
        a = new_ach[0].achievement
        ach_tr = load_translations(db, "achievement", [str(a.id)], locale)
        out.append(_m("achievement", "celebrating",
                      {"title": tr(ach_tr, a.id, "title", a.title), "icon": a.icon, "code": a.code,
                       "count": len(new_ach)},
                      at=new_ach[0].unlocked_at))

    # --- lessons completed
    done = (
        db.query(models.Progress)
        .filter(models.Progress.user_id == user.id, models.Progress.status == "completed",
                models.Progress.completed_at.isnot(None), models.Progress.completed_at >= recent_cut)
        .order_by(models.Progress.completed_at.desc())
        .all()
    )
    if done:
        lesson = done[0].lesson
        ltr = load_translations(db, "lesson", [str(lesson.id)], locale)
        out.append(_m("lesson_completed", "celebrating", {
            "title": tr(ltr, lesson.id, "title", lesson.title), "lesson_id": lesson.id,
            "count": len(done), "days": (now.date() - done[0].completed_at.date()).days,
        }, at=done[0].completed_at))

    # --- items mastered recently (and the hard-won ones)
    recent_mastered = sorted(
        (r for r in mastered_words if r.last_reviewed_at and r.last_reviewed_at >= recent_cut),
        key=lambda r: (-(r.times_missed or 0), -r.last_reviewed_at.timestamp()),
    )
    if recent_mastered:
        vtr = load_translations(db, "vocab_word", [str(r.word_id) for r in recent_mastered[:4]], locale)

        def card(r):
            w = r.word
            meaning = tr(vtr, w.id, "meanings", w.meanings)
            return {"hanzi": w.simplified, "pinyin": w.pinyin, "missed": r.times_missed or 0,
                    "meaning": w.meanings if (meaning or "").strip() == w.simplified else meaning}

        hard = [r for r in recent_mastered if (r.times_missed or 0) >= 2]
        if hard:
            out.append(_m("mastered_hard", "proud", {"item": card(hard[0])}, at=hard[0].last_reviewed_at))
        out.append(_m("mastered_recently", "happy", {
            "items": [card(r) for r in recent_mastered[:4]], "count": len(recent_mastered),
        }))

    # --- characters that keep being missed
    difficult = (
        db.query(models.UserHanzi)
        .filter(models.UserHanzi.user_id == user.id, models.UserHanzi.status != "mastered",
                models.UserHanzi.times_missed >= 2)
        .order_by(models.UserHanzi.times_missed.desc(), models.UserHanzi.id)
        .limit(4)
        .all()
    )
    if difficult:
        out.append(_m("difficult_chars", "encouraging", {
            "items": [{"hanzi": r.hanzi.character, "pinyin": r.hanzi.pinyin, "missed": r.times_missed}
                      for r in difficult if r.hanzi],
        }))

    sessions = _recent_sessions(db, user, CONFUSION_WINDOW_DAYS)

    # --- two items confused more than once
    pairs = [(k, n) for k, n in confusion_pairs(sessions).most_common(3) if n >= 2]
    for (item_type, lo, hi), n in pairs[:1]:
        a, b = _item_label(db, item_type, lo), _item_label(db, item_type, hi)
        if a and b:
            out.append(_m("confused_pair", "encouraging", {"a": a, "b": b, "count": n, "item_type": item_type},
                          a=a["hanzi"], b=b["hanzi"]))

    # --- mistakes that came back this week
    repeated = (
        db.query(models.LearningMistake)
        .filter(models.LearningMistake.user_id == user.id, models.LearningMistake.mastered.is_(False),
                models.LearningMistake.occurrences >= 2, models.LearningMistake.last_seen_at >= recent_cut)
        .order_by(models.LearningMistake.occurrences.desc())
        .limit(3)
        .all()
    )
    if repeated:
        out.append(_m("recent_mistakes", "encouraging", {
            "count": len(repeated),
            "items": [{"reference": m.reference, "type": m.mistake_type, "times": m.occurrences} for m in repeated],
        }))

    # --- listening improving
    trend = _listening_trend(sessions)
    if trend:
        out.append(_m("improving_listening", "proud", trend))

    # --- reviews completed
    reviews = [s for s in sessions if s.source == "review" and s.completed_at and s.completed_at >= recent_cut]
    if reviews:
        out.append(_m("reviews_done", "happy", {"count": len(reviews),
                                                "best": max((s.score or 0) for s in reviews)}))

    # --- an area the learner started but hasn't touched lately
    last_by_area = _last_answered_by_area(sessions)
    started = {
        "vocab": db.query(models.UserVocabulary.id).filter_by(user_id=user.id).first() is not None,
        "hanzi": db.query(models.UserHanzi.id).filter_by(user_id=user.id).first() is not None,
        "grammar": db.query(models.UserGrammar.id).filter_by(user_id=user.id).first() is not None,
    }
    stale = []
    for area, has in started.items():
        if not has:
            continue
        last = last_by_area.get(area)
        if last is None or (now - last).days >= STALE_DAYS:
            stale.append((area, (now - last).days if last else None))
    if stale and not (away is not None and away >= AWAY_DAYS):
        area, days = sorted(stale, key=lambda x: -(x[1] or 999))[0]
        out.append(_m("stale_area", "encouraging", {"area": area, "days": days}, area=_AREA_ZH[area]))

    # --- weakest DNA skill, once there is real activity behind it
    skills = [s for s in user.user_skills if s.skill]
    if skills and any((s.mastery or 0) > 0 for s in skills):
        weak = min(skills, key=lambda s: (s.mastery or 0, s.skill.code))
        if (weak.mastery or 0) < 30:
            out.append(_m("weak_skill", "encouraging", {"skill": weak.skill.code, "value": round(weak.mastery or 0, 1)}))

    # --- the newest page of their Chinese Passport story (this week)
    from app.services.passport import timeline

    fresh = [e for e in timeline(db, user, locale=locale)
             if e["kind"] not in ("joined", "first_practice", "achievement", "words_mastered")
             and e["at"] and datetime.fromisoformat(e["at"]) >= recent_cut]
    if fresh:
        e = fresh[-1]
        out.append(_m("passport_milestone", "celebrating", {"event": e["kind"], "event_data": e["data"], "link": e["link"]},
                      at=datetime.fromisoformat(e["at"])))

    if not out:
        out.append(_m("new_learner", "happy"))

    # The headline is what the companion says first: coming back and real
    # wins before support, support before reminders.
    out.sort(key=lambda m: PRIORITY.index(m["kind"]))
    headline = out[0]
    return {"companion": companion_of(user), "headline": headline, "memories": out}
