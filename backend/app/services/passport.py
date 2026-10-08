"""Chinese Passport: what the learner can DO in Chinese, with the evidence.

Everything is read from rows the app already stores for real learning
events -- nothing is converted from XP and nothing is written here:

  graded answers     PracticeSession questions/answers (every round type:
                     practice, review, lessons, Real Chinese, sentence,
                     Detective, Sound World, Chinese Internet), classified
                     by what the question type really tests
  mastery            UserVocabulary / UserHanzi / UserGrammar status
  writing            UserHanzi writing fields, HanziTraceAttempt
  speaking           VoiceAttempt
  places             completed Real Chinese / Sound World / Internet rounds
  HSK                user_rank + the lesson path (lessons, exams)
  Learning DNA       UserSkill, shown next to the evidence it summarises

A capability's band comes from demonstrated accuracy over enough answers
(never from points): with fewer than MIN_EVIDENCE answers it is "none" --
the passport says there isn't enough evidence yet instead of guessing.

The progress story (timeline) uses real timestamps only. Count milestones
("by <date> you had mastered 50 words") use the review that settled each
record: a record's status only changes when it is reviewed, so at the
N-th settled record's last review all N were mastered -- an exact "by",
never an invented "on".
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app import models
from app.services.localization import load_translations, tr

MIN_EVIDENCE = 8
RECENT_DAYS = 60

READING = {"word_to_meaning", "char_to_meaning", "example_to_point", "scene_reply", "sentence_word", "sentence_order",
           "case_deduce", "net_comprehension"}
LISTENING = {"listen_to_word", "scene_listen", "sentence_listen", "net_listen", "sound_identify", "sound_info",
             "sound_find", "sound_respond", "sound_conversation", "sound_memory"}
GRAMMAR = {"example_to_point", "sentence_order"}
CHARACTER = {"char_to_meaning", "char_to_pinyin"}
VOCAB = {"meaning_to_word", "word_to_meaning", "listen_to_word"}

# Real-world capability -> the rounds that demonstrate it.
WORLD = {
    "restaurant": {"scenes": ("restaurant",), "sound": ("restaurant", "night_market"), "net": ("review", "comments")},
    "shopping": {"scenes": ("shopping", "convenience-store"), "sound": ("shopping", "night_market"), "net": ("product", "shopping")},
    "travel": {"scenes": ("train-station", "airport", "hotel", "travel", "taxi"), "sound": ("train_station", "airport", "street"),
               "net": ("travel", "news")},
    "university": {"scenes": ("university",), "sound": ("school",), "net": ("messages",)},
    "health": {"scenes": ("hospital", "pharmacy"), "sound": (), "net": ()},
    "work": {"scenes": ("job-interview",), "sound": (), "net": ("notice",)},
    "daily": {"scenes": ("bank",), "sound": ("street",), "net": ("chat", "social", "messages")},
}
CAN_DO = 80.0


def _band(n: int, acc: float | None) -> str:
    if n < MIN_EVIDENCE or acc is None:
        return "none"
    if acc >= 85 and n >= 20:
        return "strong"
    if acc >= 65:
        return "developing"
    return "emerging"


class _Answers:
    """One pass over the learner's graded answers."""

    def __init__(self, sessions: list[models.PracticeSession]):
        self.buckets: dict[str, list[tuple[datetime, bool]]] = {k: [] for k in ("reading", "listening", "grammar",
                                                                                  "character", "vocab", "all")}
        for s in sessions:
            for q, a in zip(s.questions or [], s.answers or []):
                if not a:
                    continue
                at = datetime.fromisoformat(a["answered_at"]) if a.get("answered_at") else s.created_at
                ok = bool(a.get("correct"))
                t = q.get("type")
                self.buckets["all"].append((at, ok))
                if t in READING or (t == "case_clue" and q.get("mode") == "read"):
                    self.buckets["reading"].append((at, ok))
                if t in LISTENING or (t == "case_clue" and q.get("mode") == "listen"):
                    self.buckets["listening"].append((at, ok))
                if t in GRAMMAR:
                    self.buckets["grammar"].append((at, ok))
                if t in CHARACTER:
                    self.buckets["character"].append((at, ok))
                if t in VOCAB or q.get("item_type") == "vocab":
                    self.buckets["vocab"].append((at, ok))

    def stats(self, key: str) -> dict:
        rows = self.buckets[key]
        cut = datetime.utcnow() - timedelta(days=RECENT_DAYS)
        recent = [ok for at, ok in rows if at and at >= cut]
        acc = round(100 * sum(ok for _a, ok in rows) / len(rows)) if rows else None
        racc = round(100 * sum(recent) / len(recent)) if recent else None
        basis = (len(recent), racc) if len(recent) >= MIN_EVIDENCE else (len(rows), acc)
        return {"answers": len(rows), "accuracy": acc, "recent_answers": len(recent), "recent_accuracy": racc,
                "band": _band(*basis), "last_at": max((a for a, _o in rows if a), default=None)}


def _iso(d):
    return d.isoformat() if d else None


def _skills(user: models.User) -> dict[str, float]:
    return {s.skill.code: round(s.mastery or 0, 1) for s in user.user_skills if s.skill}


def _sessions(db: Session, user: models.User) -> list[models.PracticeSession]:
    return (db.query(models.PracticeSession).filter(models.PracticeSession.user_id == user.id)
            .order_by(models.PracticeSession.created_at).limit(2000).all())


def _completed_by_ctx(sessions, source: str, key: str) -> dict[str, list[models.PracticeSession]]:
    out: dict[str, list] = {}
    for s in sessions:
        if s.source != source or s.completed_at is None:
            continue
        k = ((s.questions or [{}])[0].get("ctx") or {}).get(key)
        if k:
            out.setdefault(k, []).append(s)
    return out


# --------------------------------------------------------------------------- capabilities

def capabilities(db: Session, user: models.User, sessions, answers: _Answers, skills: dict) -> list[dict]:
    now = datetime.utcnow()
    vocab = db.query(models.UserVocabulary).filter_by(user_id=user.id).all()
    hanzi = db.query(models.UserHanzi).filter_by(user_id=user.id).all()
    grammar = db.query(models.UserGrammar).filter_by(user_id=user.id).all()
    traces = db.query(models.HanziTraceAttempt).filter_by(user_id=user.id, status="counted").count()
    voice = db.query(models.VoiceAttempt).filter_by(user_id=user.id).order_by(models.VoiceAttempt.created_at).all()

    def count(rows, *statuses):
        return sum(1 for r in rows if r.status in statuses)

    v_due = sum(1 for r in vocab if r.next_review_at and r.next_review_at <= now and r.status != "new")
    vs = answers.stats("vocab")
    cs = answers.stats("character")
    rs = answers.stats("reading")
    ls = answers.stats("listening")
    gs = answers.stats("grammar")
    sound = _completed_by_ctx(sessions, "sound", "stage")
    stage_best = {int(k): max(s.score or 0 for s in v) for k, v in sound.items()}
    net = [s for s in sessions if s.source == "internet" and s.completed_at]
    recent_voice = voice[-20:]
    voice_avg = round(sum(v.overall or 0 for v in recent_voice) / len(recent_voice)) if recent_voice else None

    out = [
        {"code": "vocabulary", "dna": "vocabulary", "band": vs["band"], "stats": vs,
         "facts": {"known": count(vocab, "reviewing", "mastered"), "mastered": count(vocab, "mastered"),
                   "active": count(vocab, "learning", "reviewing"), "due": v_due, "tracked": len(vocab)},
         "action": "/review" if v_due else "/vocabulary"},
        {"code": "characters", "dna": "reading", "band": cs["band"], "stats": cs,
         "facts": {"learned": sum(1 for r in hanzi if r.status != "new"), "mastered": count(hanzi, "mastered"),
                   "writing_mastered": sum(1 for r in hanzi if r.writing_status == "mastered"),
                   "written": sum(1 for r in hanzi if (r.times_written or 0) > 0), "traces": traces,
                   "weak": sum(1 for r in hanzi if (r.times_missed or 0) >= 2 and r.status != "mastered")},
         "action": "/hanzi"},
        {"code": "reading", "dna": "reading", "band": rs["band"], "stats": rs,
         "facts": {"internet_reads": len(net), "internet_best": max((s.score or 0 for s in net), default=0)},
         "action": "/internet"},
        {"code": "listening", "dna": "listening", "band": ls["band"], "stats": ls,
         "facts": {"sound_stage": max([k for k, b in stage_best.items() if b >= 80] or [0]),
                   "sound_rounds": sum(len(v) for v in sound.values())},
         "action": "/sound-world"},
        {"code": "grammar", "dna": "grammar", "band": gs["band"], "stats": gs,
         "facts": {"mastered": count(grammar, "mastered"), "active": count(grammar, "learning", "reviewing")},
         "action": "/grammar"},
        {"code": "speaking", "dna": "speaking",
         "band": _band(len(voice), voice_avg), "stats": {"answers": len(voice), "accuracy": voice_avg,
                                                         "recent_answers": len(recent_voice), "recent_accuracy": voice_avg,
                                                         "last_at": voice[-1].created_at if voice else None},
         "facts": {"attempts": len(voice), "average": voice_avg},
         "action": "/voice-companion"},
    ]
    for c in out:
        c["dna_value"] = skills.get(c["dna"], 0.0)
        c["stats"] = {**c["stats"], "last_at": _iso(c["stats"].get("last_at"))}
    return out


def world_skills(db: Session, sessions, locale: str = "en") -> list[dict]:
    from app.services.real_life import scene_text
    from app.services.real_life_content import SCENE_BY_SLUG

    scenes = _completed_by_ctx(sessions, "scene", "slug")
    sound = _completed_by_ctx(sessions, "sound", "env")
    net_kind: dict[str, list] = {}
    from app.services.internet_content import ITEM_BY_SLUG

    for slug, rows in _completed_by_ctx(sessions, "internet", "slug").items():
        item = ITEM_BY_SLUG.get(slug)
        if item:
            net_kind.setdefault(item["kind"], []).extend(rows)
    out = []
    for key, src in WORLD.items():
        best_scene = None
        for slug in src["scenes"]:
            for s in scenes.get(slug, []):
                tier = (s.questions[0].get("ctx") or {}).get("tier")
                if best_scene is None or (s.score or 0) > best_scene["score"]:
                    best_scene = {"slug": slug, "score": s.score or 0, "tier": tier, "at": _iso(s.completed_at),
                                  "title": scene_text(SCENE_BY_SLUG[slug]["title"], locale)}
        sound_rows = [s for e in src["sound"] for s in sound.get(e, [])]
        net_rows = [s for k in src["net"] for s in net_kind.get(k, [])]
        best = max([best_scene["score"] if best_scene else 0] + [s.score or 0 for s in sound_rows] + [s.score or 0 for s in net_rows])
        tried = bool(best_scene or sound_rows or net_rows)
        status = "can_do" if best >= CAN_DO else ("trying" if tried else "not_yet")
        first_scene = src["scenes"][0] if src["scenes"] else None
        action = (f"/real-chinese/{best_scene['slug'] if best_scene else first_scene}" if first_scene
                  else "/sound-world" if src["sound"] else "/internet")
        out.append({
            "code": key, "status": status, "best": round(best, 1),
            "scene": best_scene,
            "scene_icon": SCENE_BY_SLUG[first_scene]["icon"] if first_scene else None,
            "sound_rounds": len(sound_rows), "sound_best": round(max((s.score or 0 for s in sound_rows), default=0), 1),
            "net_reads": len(net_rows), "action": action,
        })
    return out


def hsk_progress(db: Session, user: models.User) -> dict:
    from app.services import lesson_path
    from app.services.gamification import user_rank
    from app.services.hsk_band import resolve_level_filter

    level, overall = user_rank(db, user)
    state = lesson_path.path_state(db, user)
    summary = next((s for s in lesson_path.level_summaries(state) if s["level"] == level), None)

    def share(model, id_field, rec_model, fk):
        level_id, subset = resolve_level_filter(db, model, id_field, level)
        q = db.query(model.id).filter(id_field == (level_id or 0))
        if subset is not None:
            q = q.filter(model.id.in_(subset or [0]))
        ids = [r[0] for r in q]
        mastered = db.query(rec_model).filter(rec_model.user_id == user.id, getattr(rec_model, fk).in_(ids or [0]),
                                              rec_model.status == "mastered").count()
        return {"mastered": mastered, "total": len(ids)}

    return {
        "level": level, "next": level + 1 if level < 9 else None, "dna_overall": overall,
        "lessons": {"completed": summary["completed"], "total": summary["total"]} if summary else None,
        "exam": summary["exam"] if summary else None,
        "exams_passed": sorted(state.exams_passed),
        "vocab": share(models.VocabularyWord, models.VocabularyWord.hsk_level_id, models.UserVocabulary, "word_id"),
        "hanzi": share(models.Hanzi, models.Hanzi.hsk_level_id, models.UserHanzi, "hanzi_id"),
        "grammar": share(models.GrammarTopic, models.GrammarTopic.hsk_level_id, models.UserGrammar, "topic_id"),
    }


# --------------------------------------------------------------------------- the story

WORD_MILESTONES = (1, 10, 50, 100, 250, 500, 1000, 2000)
CHAR_MILESTONES = (1, 10, 50, 100, 300)


def timeline(db: Session, user: models.User, sessions=None, locale: str = "en") -> list[dict]:
    sessions = sessions if sessions is not None else _sessions(db, user)
    ev: list[dict] = []

    def add(kind, at, link=None, **data):
        if at is not None:
            ev.append({"kind": kind, "at": _iso(at), "link": link, "data": data})

    add("joined", user.created_at, "/dashboard")

    answered = [s for s in sessions if any(a for a in (s.answers or []))]
    if answered:
        add("first_practice", answered[0].created_at, "/review")

    done = (db.query(models.Progress).filter(models.Progress.user_id == user.id, models.Progress.status == "completed",
                                             models.Progress.completed_at.isnot(None))
            .order_by(models.Progress.completed_at).all())
    if done:
        ltr = load_translations(db, "lesson", [str(done[0].lesson_id)], locale)
        add("first_lesson", done[0].completed_at, f"/lessons/{done[0].lesson_id}",
            title=tr(ltr, done[0].lesson_id, "title", done[0].lesson.title))
        seen_levels = set()
        for p in done:
            lvl = p.lesson.hsk_level if p.lesson else None
            if lvl and lvl >= 2 and lvl not in seen_levels:
                seen_levels.add(lvl)
                add("level_started", p.completed_at, "/roadmap", level=lvl)

    for a in (db.query(models.HSKExamAttempt).filter_by(user_id=user.id, status="passed")
              .order_by(models.HSKExamAttempt.finished_at)):
        add("exam_passed", a.finished_at, "/roadmap", level=a.level, score=a.score)

    mastered_words = sorted((r for r in db.query(models.UserVocabulary).filter_by(user_id=user.id, status="mastered")
                             if r.last_reviewed_at), key=lambda r: r.last_reviewed_at)
    for n in WORD_MILESTONES:
        if len(mastered_words) >= n:
            r = mastered_words[n - 1]
            add("words_mastered", r.last_reviewed_at, "/vocabulary", count=n,
                word=r.word.simplified if n == 1 and r.word else None)
    mastered_chars = sorted((r for r in db.query(models.UserHanzi).filter_by(user_id=user.id, status="mastered")
                             if r.last_reviewed_at), key=lambda r: r.last_reviewed_at)
    for n in CHAR_MILESTONES:
        if len(mastered_chars) >= n:
            r = mastered_chars[n - 1]
            char = r.hanzi.character if r.hanzi else None
            add("chars_mastered", r.last_reviewed_at, f"/hanzi/{char}" if n == 1 and char else "/hanzi",
                count=n, char=char if n == 1 else None)
    first_written = (db.query(models.UserHanzi).filter(models.UserHanzi.user_id == user.id,
                                                       models.UserHanzi.writing_status == "mastered",
                                                       models.UserHanzi.last_written_at.isnot(None))
                     .order_by(models.UserHanzi.last_written_at).first())
    if first_written and first_written.hanzi:
        add("first_written", first_written.last_written_at, f"/hanzi/{first_written.hanzi.character}",
            char=first_written.hanzi.character)

    for m in (db.query(models.LearningMistake).filter(models.LearningMistake.user_id == user.id,
                                                      models.LearningMistake.mastered.is_(True),
                                                      models.LearningMistake.occurrences >= 3,
                                                      models.LearningMistake.mastered_at.isnot(None))
              .order_by(models.LearningMistake.mastered_at.desc()).limit(3)):
        add("mistake_conquered", m.mastered_at, "/mistakes", reference=m.reference, times=m.occurrences)

    big_review = next((s for s in sessions if s.source == "review" and s.completed_at and len(s.questions or []) >= 10
                       and (s.score or 0) >= 80), None)
    if big_review:
        add("review_recovery", big_review.completed_at, "/review", items=len(big_review.questions), score=big_review.score)

    # Coming back after a break (a gap of a week or more between active days).
    days = sorted({d for (d,) in db.query(models.ActivityEvent.created_at).filter_by(user_id=user.id)
                   if d for d in [d.date()]})
    comebacks = [(prev, cur) for prev, cur in zip(days, days[1:]) if (cur - prev).days >= 7]
    for prev, cur in comebacks[-2:]:
        add("comeback", datetime.combine(cur, datetime.min.time()), "/review", days=(cur - prev).days)

    scenes = _completed_by_ctx(sessions, "scene", "slug")
    for slug, rows in scenes.items():
        good = next((s for s in rows if (s.score or 0) >= 70), None)
        if good:
            from app.services.real_life import scene_text
            from app.services.real_life_content import SCENE_BY_SLUG

            title = scene_text(SCENE_BY_SLUG[slug]["title"], locale) if slug in SCENE_BY_SLUG else slug
            add("scene_done", good.completed_at, f"/real-chinese/{slug}", scene=slug, title=title, score=good.score)

    solved = [s for s in sessions if s.source == "detective" and s.completed_at and s.answers and s.answers[-1]
              and s.answers[-1].get("correct")]
    for n in (1, 5, 10):
        if len(solved) >= n:
            add("cases_solved", solved[n - 1].completed_at, "/detective", count=n)

    for stage, rows in sorted(_completed_by_ctx(sessions, "sound", "stage").items()):
        good = next((s for s in rows if (s.score or 0) >= 80), None)
        if good:
            add("sound_stage", good.completed_at, "/sound-world", stage=int(stage))

    # Chinese Stories: the first story (a round or a book read to its end),
    # how many books, and the first book finished at each HSK level.
    from app.services import stories as stories_svc

    story = next((s for s in sessions if s.source == "story" and s.completed_at), None)
    finished = stories_svc.completed_books(db, user)
    firsts = [w for w in ((story.completed_at if story else None), (finished[0][1] if finished else None)) if w]
    if firsts:
        add("first_story", min(firsts), "/stories")
    for n in (5, 10, 25, 50):
        if len(finished) >= n:
            add("books_read", finished[n - 1][1], "/stories", count=n)
    seen_levels: set[int] = set()
    for book, when in finished:
        lvl = book["level"]
        if lvl >= 2 and lvl not in seen_levels:
            seen_levels.add(lvl)
            add("level_book", when, f"/stories/{book['slug']}", level=lvl, title=book["title"]["zh"])
    net = next((s for s in sessions if s.source == "internet" and s.completed_at), None)
    if net:
        add("first_internet", net.completed_at, "/internet")
    sent_l = next((s for s in sessions if s.source == "sentence" and s.completed_at), None)
    if sent_l:
        add("first_sentence", sent_l.completed_at, "/sentence")

    first_voice = db.query(models.VoiceAttempt).filter_by(user_id=user.id).order_by(models.VoiceAttempt.created_at).first()
    if first_voice:
        add("first_voice", first_voice.created_at, "/voice-companion")

    won = (db.query(models.Duel).filter(models.Duel.winner_id == user.id, models.Duel.finished_at.isnot(None))
           .order_by(models.Duel.finished_at).first())
    if won:
        add("first_duel_win", won.finished_at, "/duels")

    achs = (db.query(models.UserAchievement).filter_by(user_id=user.id)
            .order_by(models.UserAchievement.unlocked_at).all())
    atr = load_translations(db, "achievement", [str(a.achievement_id) for a in achs], locale)
    for a in achs:
        add("achievement", a.unlocked_at, "/achievements", title=tr(atr, a.achievement_id, "title", a.achievement.title),
            icon=a.achievement.icon, code=a.achievement.code)

    ev.sort(key=lambda e: e["at"])
    return ev


# --------------------------------------------------------------------------- recommendations

def recommendations(caps: list[dict], world: list[dict], hsk: dict) -> list[dict]:
    """Where to go next, each with the evidence that suggests it."""
    order = {"emerging": 0, "none": 1, "developing": 2, "strong": 3}
    out = []
    for c in sorted(caps, key=lambda c: (order[c["band"]], c["dna_value"])):
        if c["band"] in ("emerging", "none"):
            out.append({"kind": "capability", "code": c["code"], "band": c["band"], "to": c["action"],
                        "accuracy": c["stats"]["recent_accuracy"] or c["stats"]["accuracy"],
                        "answers": c["stats"]["answers"], "dna": c["dna"], "dna_value": c["dna_value"]})
    v = next(c for c in caps if c["code"] == "vocabulary")
    if v["facts"]["due"]:
        out.insert(0, {"kind": "review", "to": "/review", "due": v["facts"]["due"]})
    ch = next(c for c in caps if c["code"] == "characters")
    if ch["facts"]["weak"]:
        out.append({"kind": "weak_chars", "to": "/hanzi", "count": ch["facts"]["weak"]})
    nxt = next((w for w in world if w["status"] == "not_yet"), None)
    if nxt:
        out.append({"kind": "world", "code": nxt["code"], "to": nxt["action"]})
    if hsk.get("exam") == "ready":
        out.insert(0, {"kind": "exam", "to": "/roadmap", "level": hsk["level"]})
    return out[:5]


def weak_characters(db: Session, user: models.User, locale: str) -> list[dict]:
    rows = (db.query(models.UserHanzi).filter(models.UserHanzi.user_id == user.id, models.UserHanzi.status != "mastered",
                                              models.UserHanzi.times_missed >= 2)
            .order_by(models.UserHanzi.times_missed.desc()).limit(6).all())
    return [{"char": r.hanzi.character, "pinyin": r.hanzi.pinyin, "missed": r.times_missed} for r in rows if r.hanzi]


def passport(db: Session, user: models.User, locale: str) -> dict:
    from app.services.gamification import ensure_user_skills

    ensure_user_skills(db, user)
    sessions = _sessions(db, user)
    answers = _Answers(sessions)
    skills = _skills(user)
    caps = capabilities(db, user, sessions, answers, skills)
    world = world_skills(db, sessions, locale)
    hsk = hsk_progress(db, user)
    story = timeline(db, user, sessions, locale)
    return {
        "user": {"username": user.username, "since": _iso(user.created_at)},
        "hsk": hsk,
        "capabilities": caps,
        "world": world,
        "timeline": story,
        "weak_characters": weak_characters(db, user, locale),
        "recommendations": recommendations(caps, world, hsk),
        "totals": {"answers": len(answers.buckets["all"]), "rounds": sum(1 for s in sessions if s.completed_at)},
        "min_evidence": MIN_EVIDENCE,
    }
