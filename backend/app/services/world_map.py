"""The living world on /real-chinese: one map that grows with the learner.

The places (services/world_places.py) are gateways into systems that
already exist; this module works out what each place looks like FOR THIS
LEARNER, from their stored records only -- nothing is unlocked, lit or
completed unless the data says so:

  open / locked   their current HSK level (user_rank -- the level the
                  Dashboard and the Roadmap show) reached the place's
                  min_level. Nothing else opens a place: knowing its words
                  lights its topics up once it is open, never earlier.
                  A locked place is sent as a silhouette only (where it is,
                  what it is called, the level it opens at) -- none of its
                  words, sentences, talks, scene or gateway.
  topics          a place's conversation topics light up as their words are
                  really known (half of them; "learning" counts half)
  explored        a completed round there (Real Chinese scene, Sound World
                  place, Chinese Internet item), a World voice turn there,
                  one of its topic sentences learned as a One Sentence
                  lesson, or the gateway's own activity (lessons, Hanzi,
                  cases, review, duels, the Daily Voice Companion...)
  mastered        the scene passed at >= MASTERED and most theme words known
  current         where their most recent activity happened (home at first)
  visited         a round started there and left unfinished (not yet explored)
  new             open and untouched, and opened by their own words or by
                  reaching their current HSK level (above HSK 1)
  recommended     one next stop: an open, unexplored place scored by how many
                  of its words they know, whether it trains their weakest
                  Learning Compass skill, and how far it is from where they are
  talks           the World voice conversations / cases stationed there,
                  locked exactly as the voice endpoints lock them
  greeting        the line its person says first, at the learner's tier,
                  as real curriculum words they can inspect

The Real Chinese scenes are gated by the same rule on the server
(scene_gate), so the map and the practice engine always agree.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app import models
from app.services import sentence as sent
from app.services import story_slots as ss
from app.services.world_places import (
    CANVAS_H,
    CANVAS_W,
    DISTRICTS,
    PATHS,
    PLACE_BY_KEY,
    PLACE_BY_SCENE,
    PLACE_BY_SENTENCE,
    PLACES,
    RIVER,
)

MASTERED = 80.0
KNOWN = ("reviewing", "mastered")


def _word_rows(db: Session, words: set[str]) -> dict[str, models.VocabularyWord]:
    levels = {lvl.id: lvl.level for lvl in db.query(models.HSKLevel).all()}
    rows = db.query(models.VocabularyWord).filter(models.VocabularyWord.simplified.in_(words or [""])).all()
    best: dict[str, models.VocabularyWord] = {}
    for r in sorted(rows, key=lambda r: (levels.get(r.hsk_level_id, 99), r.id)):
        best.setdefault(r.simplified, r)
    return best


def _statuses(db: Session, user: models.User, rows: dict[str, models.VocabularyWord]) -> dict[str, str]:
    """word text -> the learner's status for it (any HSK row of that word
    counts: knowing 茶 at HSK 1 is knowing 茶)."""
    texts = list(rows)
    recs = (db.query(models.VocabularyWord.simplified, models.UserVocabulary.status)
            .join(models.UserVocabulary, models.UserVocabulary.word_id == models.VocabularyWord.id)
            .filter(models.UserVocabulary.user_id == user.id, models.VocabularyWord.simplified.in_(texts or [""])).all())
    rank = {"new": 0, "learning": 1, "reviewing": 2, "mastered": 3}
    out: dict[str, str] = {}
    for text, status in recs:
        if rank.get(status, 0) > rank.get(out.get(text, "new"), 0):
            out[text] = status
    return out


def _known(statuses: dict[str, str], words) -> int:
    return sum(1 for w in words if statuses.get(w) in KNOWN)


def place_open(place: dict, level: int) -> bool:
    """The world's one progression rule: the learner's current HSK level."""
    return level >= place["min_level"]


def scene_gate(db: Session, user: models.User, scene_slug: str) -> None:
    """Raise if the place holding this scene isn't open for the learner yet
    (the same rule the map shows)."""
    from app.services.gamification import user_rank
    from app.services.real_life import SceneError

    key = PLACE_BY_SCENE.get(scene_slug)
    if key is None:
        return
    place = PLACE_BY_KEY[key]
    level, _ = user_rank(db, user)
    if not place_open(place, level):
        raise SceneError(403, f"This place opens at HSK {place['min_level']}")


def _greeting(db: Session, place: dict, tier: str, locale: str) -> dict | None:
    from app.services.real_life import scene_text
    from app.services.real_life_content import SCENE_BY_SLUG

    zh = py = role = None
    if place["scene"]:
        scene = SCENE_BY_SLUG[place["scene"]]
        npc = scene["tiers"][tier][0]["npc"]
        zh, py = npc["zh"], npc["py"]
        role = {"zh": scene["npc"]["zh"], "role": scene_text(scene["npc"]["role"], locale)}
    elif place["location"]:
        d = (db.query(models.Dialogue).join(models.Scenario, models.Dialogue.scenario_id == models.Scenario.id)
             .join(models.Location, models.Scenario.location_id == models.Location.id)
             .filter(models.Location.slug == place["location"], models.Dialogue.speaker == "npc")
             .order_by(models.Scenario.order_index, models.Dialogue.turn_index).first())
        if d is not None:
            zh, py = d.text, d.pinyin
            npc = d.npc or db.query(models.NPC).join(models.Location).filter(models.Location.slug == place["location"]).first()
            role = {"zh": npc.name if npc else "", "role": ""}
    if not zh:
        return None
    tokens = sent.segment(db, zh)
    m = ss.meanings(db, [t["word"].id for t in tokens if t["word"] is not None], locale)
    return {"zh": zh, "py": py, "speaker": role,
            "tokens": [{"text": t["text"], "word_id": t["word"].id, "meaning": m.get(t["word"].id, "")}
                       if t["word"] is not None else {"text": t["text"]} for t in tokens]}


def _talks(db: Session, user: models.User, place: dict, level: int, locale: str) -> list[dict]:
    from app.services.gamification import location_status
    from app.services.localization import load_translations, tr

    if not place["location"]:
        return []
    loc = db.query(models.Location).filter_by(slug=place["location"]).first()
    if loc is None:
        return []
    status = location_status(loc, level)
    str_ = load_translations(db, "scenario", [str(s.id) for s in loc.scenarios], locale)
    tried = {sid for (sid,) in db.query(models.VoiceAttempt.scenario_id).filter(
        models.VoiceAttempt.user_id == user.id, models.VoiceAttempt.scenario_id.in_([s.id for s in loc.scenarios] or [0]))}
    out = []
    for s in sorted(loc.scenarios, key=lambda s: s.order_index):
        out.append({"slug": s.slug, "case": bool(s.is_case), "title": tr(str_, s.id, "title", s.title),
                    "locked": status != "unlocked", "min_level": loc.unlock_level, "voice": bool(s.requires_voice),
                    "tried": s.id in tried})
    return out


def _gateway_activity(db: Session, user: models.User, sessions_by_source: dict) -> dict[str, bool]:
    lessons = db.query(models.Progress.id).filter_by(user_id=user.id, status="completed").first() is not None
    hanzi = db.query(models.UserHanzi.id).filter(models.UserHanzi.user_id == user.id,
                                                 models.UserHanzi.status != "new").first() is not None
    words = db.query(models.UserVocabulary.id).filter(models.UserVocabulary.user_id == user.id,
                                                      models.UserVocabulary.status.in_(KNOWN)).first() is not None
    duels = (db.query(models.DuelParticipant.id).join(models.Duel, models.Duel.id == models.DuelParticipant.duel_id)
             .filter(models.DuelParticipant.user_id == user.id, models.Duel.finished_at.isnot(None)).first() is not None)
    # The Daily Voice Companion's turns are the voice attempts with no World scenario.
    voice = db.query(models.VoiceAttempt.id).filter(models.VoiceAttempt.user_id == user.id,
                                                    models.VoiceAttempt.scenario_id.is_(None)).first() is not None
    return {
        "/lessons": lessons or bool(sessions_by_source.get("sentence")) or bool(sessions_by_source.get("lesson")),
        "/hanzi": hanzi, "/ecosystem": words,
        "/internet": bool(sessions_by_source.get("internet")), "/detective": bool(sessions_by_source.get("detective")),
        "/sound-world": bool(sessions_by_source.get("sound")), "/passport": False,
        "/vocabulary": bool(sessions_by_source.get("vocab")), "/review": bool(sessions_by_source.get("review")),
        "/duels": duels, "/voice-companion": voice,
    }


def _place_of_session(s: models.PracticeSession) -> str | None:
    ctx = (s.questions or [{}])[0].get("ctx") or {}
    if s.source == "scene":
        return PLACE_BY_SCENE.get(ctx.get("slug"))
    if s.source == "sound":
        return "sound_plaza"
    if s.source == "internet":
        return "internet_cafe"
    if s.source == "detective":
        return "detective"
    if s.source == "sentence":
        return PLACE_BY_SENTENCE.get(ctx.get("text")) or "library"
    if s.source == "vocab":
        return "bookstore"
    if s.source == "review":
        return "park"
    if s.source in ("lesson", "grammar"):
        return "library"
    if s.source == "hanzi":
        return "calligraphy"
    return None


# What a place trains, for the "recommended" pick (by its content only).
def _trains(p: dict) -> set[str]:
    out = set()
    if p["sound"] or p["scene"] or "/sound-world" in (p["gateway"], *p["links"]):
        out.add("listening")
    if p["location"] or p["scene"] or "/voice-companion" in (p["gateway"], *p["links"]):
        out.add("speaking")
    if p["internet"] or p["gateway"] == "/internet":
        out.add("reading")
    if p["topics"] or p["gateway"] in ("/vocabulary", "/review", "/ecosystem"):
        out.add("vocabulary")
    if p["gateway"] == "/hanzi" or "/hanzi" in p["links"]:
        out.add("writing")
    return out


def _hops(start: str) -> dict[str, int]:
    dist, todo = {start: 0}, [start]
    while todo:
        k = todo.pop(0)
        for a, b in PATHS:
            for x, y in ((a, b), (b, a)):
                if x == k and y not in dist:
                    dist[y] = dist[k] + 1
                    todo.append(y)
    return dist


def _unfinished_places(sessions) -> set[str]:
    """Places where a round was started and never completed."""
    out = set()
    for s in sessions:
        if s.completed_at is not None:
            continue
        ctx = (s.questions or [{}])[0].get("ctx") or {}
        if s.source == "scene":
            key = PLACE_BY_SCENE.get(ctx.get("slug"))
            if key:
                out.add(key)
        elif s.source == "sentence" and ctx.get("text") in PLACE_BY_SENTENCE:
            out.add(PLACE_BY_SENTENCE[ctx["text"]])
        elif s.source == "sound":
            out |= {p["key"] for p in PLACES if p["sound"] and p["sound"] == ctx.get("env")}
        elif s.source == "internet":
            out |= {p["key"] for p in PLACES if ctx.get("slug") in p["internet"]}
    return out


def _recommend(out: list[dict], current: str, weak: str | None) -> dict | None:
    hops = _hops(current)
    best, best_score = None, None
    for p in out:
        if p["status"] != "open" or p["key"] == current:
            continue
        content = PLACE_BY_KEY[p["key"]]
        ratio = p["theme"]["known"] / p["theme"]["total"] if p["theme"]["total"] else 0.0
        trains = bool(weak and weak in _trains(content))
        score = (3 * ratio + (2 if trains else 0) + (1 if content["scene"] else 0) + (0.5 if p["new"] else 0)
                 - 0.15 * hops.get(p["key"], 12))
        if best_score is None or score > best_score:
            reason = "skill" if trains else "words" if ratio >= 0.34 else "next"
            best, best_score = {"key": p["key"], "reason": reason, "skill": weak if trains else None,
                                "known": p["theme"]["known"]}, score
    return best


def world(db: Session, user: models.User, locale: str) -> dict:
    from app.services import passport as pp
    from app.services import real_life
    from app.services.gamification import ensure_user_skills, user_rank
    from app.services.internet_content import ITEM_BY_SLUG

    ensure_user_skills(db, user)
    level, _ = user_rank(db, user)
    tier = sent.tier_for(level)
    sessions = pp._sessions(db, user)
    done = [s for s in sessions if s.completed_at is not None]
    by_source: dict[str, list] = {}
    for s in done:
        by_source.setdefault(s.source, []).append(s)
    scenes = pp._completed_by_ctx(sessions, "scene", "slug")
    sound = pp._completed_by_ctx(sessions, "sound", "env")
    net = pp._completed_by_ctx(sessions, "internet", "slug")
    sentences = pp._completed_by_ctx(sessions, "sentence", "text")
    unfinished = _unfinished_places(sessions)
    gateway = _gateway_activity(db, user, by_source)

    words = {w for p in PLACES for w in p["theme"]} | {w for p in PLACES for t in p["topics"] for w in t["words"]}
    rows = _word_rows(db, words)
    statuses = _statuses(db, user, rows)
    m = ss.meanings(db, [r.id for r in rows.values()], locale)

    def card(w: str) -> dict:
        r = rows.get(w)
        return {"text": w, "id": r.id if r else None, "pinyin": r.pinyin if r else "", "meaning": m.get(r.id, "") if r else "",
                "status": statuses.get(w, "new")}

    out = []
    for p in PLACES:
        is_open = place_open(p, level)
        if not is_open:
            # A silhouette: where it is, what it is called, the level it opens
            # at. None of its learning content leaves the server.
            out.append({
                "key": p["key"], "icon": p["icon"], "district": p["district"], "x": p["x"], "y": p["y"],
                "status": "locked", "min_level": p["min_level"], "visited": False, "new": False,
                "theme": {"known": 0, "total": 0, "words": []}, "topics": [], "scene": None, "talks": [],
                "sound": None, "internet": [], "gateway": None, "links": [], "greeting": None,
            })
            continue
        known = _known(statuses, p["theme"])
        topics = []
        for t in p["topics"]:
            score = sum(1.0 if statuses.get(w) in KNOWN else 0.5 if statuses.get(w) == "learning" else 0.0 for w in t["words"])
            topics.append({"key": t["key"], "lit": score >= len(t["words"]) / 2, "sentence": t["sentence"],
                           "words": [card(w) for w in t["words"]]})
        scene_info = None
        if p["scene"]:
            rows_ = scenes.get(p["scene"], [])
            best = max((s.score or 0 for s in rows_), default=0.0)
            last = max(rows_, key=lambda s: s.completed_at) if rows_ else None
            sc = real_life.SCENE_BY_SLUG[p["scene"]]
            scene_info = {"slug": p["scene"], "title": real_life.scene_text(sc["title"], locale), "best": round(best, 1),
                          "rounds": len(rows_), "last_at": last.completed_at.isoformat() if last else None,
                          "exchanges": len(sc["tiers"][tier])}
        talks = _talks(db, user, p, level, locale)
        sound_rows = sound.get(p["sound"], []) if p["sound"] else []
        internet = [{"slug": slug, "title": ITEM_BY_SLUG[slug]["title"], "icon": ITEM_BY_SLUG[slug]["icon"],
                     "best": round(max((s.score or 0 for s in net.get(slug, [])), default=0.0), 1),
                     "read": bool(net.get(slug))} for slug in p["internet"]]
        explored = bool((scene_info and scene_info["rounds"]) or any(t["tried"] for t in talks) or sound_rows
                        or any(i["read"] for i in internet) or (p["gateway"] and gateway.get(p["gateway"]))
                        or any(t["sentence"] in sentences for t in p["topics"]))
        mastered = bool(scene_info and scene_info["best"] >= MASTERED and known * 2 >= len(p["theme"]))
        status = "mastered" if mastered else "explored" if explored else "open"
        visited = status == "open" and p["key"] in unfinished
        new = status == "open" and not visited and p["min_level"] == level and level > 1
        out.append({
            "key": p["key"], "icon": p["icon"], "district": p["district"], "x": p["x"], "y": p["y"],
            "status": status, "min_level": p["min_level"], "visited": visited, "new": new,
            "theme": {"known": known, "total": len(p["theme"]), "words": [card(w) for w in p["theme"]]},
            "topics": topics, "scene": scene_info, "talks": talks,
            "sound": {"env": p["sound"], "rounds": len(sound_rows),
                      "best": round(max((s.score or 0 for s in sound_rows), default=0.0), 1)} if p["sound"] else None,
            "internet": internet, "gateway": p["gateway"], "links": list(p["links"]),
            "greeting": _greeting(db, p, tier, locale),
        })

    # Where the learner was last: their most recent completed round, else
    # the last voice turn they took in a World conversation, else home.
    current = "home"
    latest = max(done, key=lambda s: s.completed_at, default=None)
    voice = (db.query(models.VoiceAttempt).filter(models.VoiceAttempt.user_id == user.id,
                                                  models.VoiceAttempt.scenario_id.isnot(None))
             .order_by(models.VoiceAttempt.created_at.desc()).first())
    if voice is not None and (latest is None or voice.created_at > latest.completed_at):
        sc = db.get(models.Scenario, voice.scenario_id)
        loc = sc.location.slug if sc and sc.location else None
        current = next((p["key"] for p in PLACES if p["location"] == loc), current)
    elif latest is not None:
        current = _place_of_session(latest) or current
    # Never stand in a locked place (a round played there before the HSK-only
    # rule, when knowing its words opened it): back home.
    if not place_open(PLACE_BY_KEY.get(current, PLACE_BY_KEY["home"]), level):
        current = "home"

    # The weakest Learning Compass skill a place can train -- only once there
    # is evidence (a new learner has no weakest skill, just an empty profile).
    skills = pp._skills(user)
    trained = {k: v for k, v in skills.items() if k in ("listening", "speaking", "reading", "vocabulary", "writing")}
    weak = min(trained, key=trained.get) if any(v > 0 for v in skills.values()) and trained else None
    recommended = _recommend(out, current, weak)

    open_keys = {p["key"] for p in out if p["status"] != "locked"}
    answers = pp._Answers(sessions)
    caps = pp.capabilities(db, user, sessions, answers, pp._skills(user))
    return {
        "level": level, "tier": tier, "current": current, "recommended": recommended,
        "map": {"w": CANVAS_W, "h": CANVAS_H, "river": [list(pt) for pt in RIVER], "districts": list(DISTRICTS)},
        "adaptation": real_life.dna_adaptation(user),
        "places": out,
        "paths": [{"from": a, "to": b, "open": a in open_keys and b in open_keys} for a, b in PATHS],
        "passport": {
            "explored": sum(1 for p in out if p["status"] in ("explored", "mastered")),
            "open": len(open_keys), "total": len(out),
            "scenes_done": sum(1 for p in out if p["scene"] and p["scene"]["best"] >= 70),
            "scenes_total": sum(1 for p in PLACES if p["scene"]),
            "skills_shown": sum(1 for c in caps if c["band"] in ("developing", "strong")),
            "skills_total": len(caps),
        },
        "generated_at": datetime.utcnow().isoformat(),
    }
