"""Real Chinese: real-life situations played as dialogues.

The script for each situation is content (services/real_life_content.py);
everything about how the learner meets it comes from their own data:

  tier          from user_rank -- the same HSK level the dashboard, World
                and Roadmap use -- so the dialogue's vocabulary, grammar,
                sentence length, number of exchanges and replies differ
  listening     beginners read the line with pinyin and may peek at the
                translation; intermediate learners get one audio-only
                comprehension question; advanced learners hear every line
                before they see it, plus two comprehension questions
  new words     curriculum words found in the dialogue that this learner
                hasn't mastered, nearest-level first (practice drills them)
  grammar       a curriculum grammar point the dialogue uses, at or below
                the learner's level, asked about its own line

A scene is played as a practice round (practice.build_session, source
"scene"), so every answer is graded on the server and feeds mastery (the
exchange's focus word goes through apply_srs), mistakes, Learning DNA, XP,
quests and the companion's reactions like any other round.
"""

from __future__ import annotations

import random

from sqlalchemy.orm import Session

from app import models
from app.services import sentence as sent
from app.services.real_life_content import SCENE_BY_SLUG, SCENES

TIERS = ("beginner", "intermediate", "advanced")

# How each tier is played. `listen` = exchanges (by index) that open with an
# audio-only "what did they say?" question.
RULES = {
    "beginner": {"show_text": True, "show_pinyin": True, "show_translation": True,
                 "option_pinyin": True, "listen": (), "new_words": 2, "rate": 0.8},
    "intermediate": {"show_text": True, "show_pinyin": False, "show_translation": False,
                     "option_pinyin": False, "listen": (1,), "new_words": 3, "rate": 0.95},
    "advanced": {"show_text": False, "show_pinyin": False, "show_translation": False,
                 "option_pinyin": False, "listen": (1, 3), "new_words": 4, "rate": 1.0},
}


class SceneError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def text_for(d: dict, locale: str) -> str:
    """The translation of a Chinese line in the UI language. A Chinese UI gets
    none -- the line itself is the text -- rather than an English gloss."""
    if locale == "zh":
        return ""
    return d.get(locale) or d.get("en") or ""


def scene_text(d: dict, locale: str) -> str:
    """Titles/descriptions do have a zh version."""
    return d.get(locale) or d.get("en") or ""


def tier_lines(scene: dict, tier: str) -> str:
    return "".join(e["npc"]["zh"] + e["reply"]["zh"] for e in scene["tiers"][tier])


def _focus_rows(db: Session, scene: dict, tier: str) -> dict[str, models.VocabularyWord]:
    return sent.vocab_rows(db, "".join(e["focus"] for e in scene["tiers"][tier]))


def new_words(db: Session, user: models.User, scene: dict, tier: str, level: int, limit: int) -> list[models.VocabularyWord]:
    """Curriculum words in this tier's dialogue that the learner hasn't
    mastered: unseen ones within reach of their level first, then the ones
    they're still learning (lowest mastery first)."""
    from app.services import practice

    text = tier_lines(scene, tier)
    words = [t["word"] for t in sent.segment(db, text) if t["word"] is not None]
    words = list({w.id: w for w in words}.values())
    levels = sent._level_map(db)
    recs = {r.word_id: r for r in db.query(models.UserVocabulary).filter(
        models.UserVocabulary.user_id == user.id, models.UserVocabulary.word_id.in_([w.id for w in words] or [0]))}
    reach = level + (1 if tier == "beginner" else 2)
    pool = [w for w in words if practice._usable("vocab", w) and len(w.simplified) >= 1
            and levels.get(w.hsk_level_id, 1) <= reach
            and (recs.get(w.id) is None or recs[w.id].status != "mastered")]
    pool.sort(key=lambda w: (recs.get(w.id) is not None, recs[w.id].mastery if w.id in recs else 0,
                             -len(w.simplified), -levels.get(w.hsk_level_id, 1), w.id))
    return pool[:limit]


def _history(db: Session, user: models.User) -> dict[str, dict]:
    """Per scene: completed rounds and best score, from the learner's own
    stored scene sessions."""
    out: dict[str, dict] = {}
    rows = (
        db.query(models.PracticeSession)
        .filter(models.PracticeSession.user_id == user.id, models.PracticeSession.source == "scene",
                models.PracticeSession.completed_at.isnot(None))
        .all()
    )
    for s in rows:
        ctx = (s.questions or [{}])[0].get("ctx") or {}
        slug = ctx.get("slug")
        if not slug:
            continue
        h = out.setdefault(slug, {"completed": 0, "best": 0.0, "last_at": None, "tiers": []})
        h["completed"] += 1
        h["best"] = max(h["best"], s.score or 0.0)
        if ctx.get("tier") and ctx["tier"] not in h["tiers"]:
            h["tiers"].append(ctx["tier"])
        if h["last_at"] is None or s.completed_at > h["last_at"]:
            h["last_at"] = s.completed_at
    return out


def scene_list(db: Session, user: models.User, locale: str) -> dict:
    from app.services.gamification import user_rank

    level, _ = user_rank(db, user)
    tier = sent.tier_for(level)
    ad = dna_adaptation(user)
    rules = _adapted(tier, ad)
    history = _history(db, user)
    scenes = []
    for s in SCENES:
        h = history.get(s["slug"]) or {"completed": 0, "best": 0.0, "last_at": None, "tiers": []}
        scenes.append({
            "slug": s["slug"], "icon": s["icon"], "title": scene_text(s["title"], locale),
            "description": scene_text(s["description"], locale),
            "npc": {"zh": s["npc"]["zh"], "role": scene_text(s["npc"]["role"], locale)},
            "exchanges": len(s["tiers"][tier]),
            "new_words": len(new_words(db, user, s, tier, level, rules["new_words"])),
            "completed": h["completed"], "best_score": h["best"],
            "last_completed_at": h["last_at"].isoformat() if h["last_at"] else None,
        })
    return {"level": level, "tier": tier, "rules": _public_rules(tier, ad), "scenes": scenes}


# Learning DNA moves a scene inside its tier. A skill counts as strong at
# DNA_STRONG and weak below DNA_WEAK -- but only once the learner has real
# DNA evidence at all (a brand-new learner's zeros mean "unknown", not
# "weak"), so a new learner gets the tier exactly as written.
DNA_STRONG, DNA_WEAK = 60.0, 25.0


def dna_adaptation(user: models.User) -> dict:
    sk = {s.skill.code: s.mastery or 0.0 for s in user.user_skills if s.skill}
    evidence = any(v > 0 for v in sk.values())

    def band(code: str, up: str, down: str) -> str:
        v = sk.get(code, 0.0)
        if v >= DNA_STRONG:
            return up
        if evidence and v < DNA_WEAK:
            return down
        return "standard"

    return {
        "speech": band("listening", "faster", "slower"),
        "words": band("vocabulary", "richer", "familiar"),
        "grammar": band("grammar", "stretch", "controlled"),
        "listening": round(sk.get("listening", 0.0), 1), "vocabulary": round(sk.get("vocabulary", 0.0), 1),
        "grammar_value": round(sk.get("grammar", 0.0), 1), "evidence": evidence,
    }


def _adapted(tier: str, ad: dict) -> dict:
    """The tier's rules, moved by Learning DNA (see dna_adaptation)."""
    r = dict(RULES[tier])
    r["listen"] = tuple(r["listen"])
    if ad["speech"] == "faster":
        r["rate"] = round(min(1.25, r["rate"] * 1.12), 2)
        # One more line heard before it's read: the first exchange (in this
        # order) that isn't a listening one yet -- every tier has >= 3.
        extra = next(i for i in (1, 3, 0, 2) if i not in r["listen"])
        r["listen"] = r["listen"] + (extra,)
    elif ad["speech"] == "slower":
        r["rate"] = round(max(0.65, r["rate"] * 0.85), 2)
    if ad["words"] == "richer":
        r["new_words"] += 1
    elif ad["words"] == "familiar":
        r["new_words"] = max(1, r["new_words"] - 1)
    return r


def _public_rules(tier: str, ad: dict | None = None) -> dict:
    r = _adapted(tier, ad) if ad else RULES[tier]
    exchanges = len(SCENES[0]["tiers"][tier])
    return {
        "show_text": r["show_text"], "show_pinyin": r["show_pinyin"],
        "listening": sum(1 for i in r["listen"] if i < exchanges),
        "options": 4 if tier == "advanced" else 3, "new_words": r["new_words"], "rate": r["rate"],
        "adaptation": {k: ad[k] for k in ("speech", "words", "grammar")} if ad else None,
    }


def scene_preview(db: Session, user: models.User, slug: str, locale: str) -> dict:
    from app.services.gamification import user_rank
    from app.services.localization import load_translations, tr

    scene = SCENE_BY_SLUG.get(slug)
    if scene is None:
        raise SceneError(404, "Scene not found")
    from app.services.world_map import scene_gate

    scene_gate(db, user, slug)
    level, _ = user_rank(db, user)
    tier = sent.tier_for(level)
    ad = dna_adaptation(user)
    words = new_words(db, user, scene, tier, level, _adapted(tier, ad)["new_words"])
    levels = sent._level_map(db)
    trs = load_translations(db, "vocab_word", [str(w.id) for w in words], locale)
    grammar = [g for g in sent.match_grammar(db, tier_lines(scene, tier)) if levels.get(g.hsk_level_id, 1) <= level][:3]
    gtr = load_translations(db, "grammar_topic", [str(g.id) for g in grammar], locale)
    h = _history(db, user).get(slug) or {"completed": 0, "best": 0.0}
    return {
        "slug": slug, "icon": scene["icon"], "title": scene_text(scene["title"], locale),
        "description": scene_text(scene["description"], locale),
        "npc": {"zh": scene["npc"]["zh"], "role": scene_text(scene["npc"]["role"], locale)},
        "level": level, "tier": tier, "rules": _public_rules(tier, ad),
        "exchanges": len(scene["tiers"][tier]),
        "new_words": [
            {"hanzi": w.simplified, "pinyin": w.pinyin, "level": levels.get(w.hsk_level_id),
             "meaning": w.meanings if (tr(trs, w.id, "meanings", w.meanings) or "").strip() == w.simplified
             else tr(trs, w.id, "meanings", w.meanings)}
            for w in words
        ],
        "grammar": [{"title": tr(gtr, g.id, "title", g.title), "pattern": g.pattern, "level": levels.get(g.hsk_level_id)}
                    for g in grammar],
        "completed": h["completed"], "best_score": h["best"],
    }


def build_questions(db: Session, user: models.User, slug: str, level: int, rng: random.Random,
                    translated: dict | None) -> list[dict]:
    from app.services import practice

    scene = SCENE_BY_SLUG.get(slug)
    if scene is None:
        raise SceneError(404, "Scene not found")
    from app.services.world_map import scene_gate

    scene_gate(db, user, slug)
    tier = sent.tier_for(level)
    ad = dna_adaptation(user)
    rules = _adapted(tier, ad)
    exchanges = scene["tiers"][tier]
    focus = _focus_rows(db, scene, tier)
    npc_pool = [e["npc"] for e in exchanges]
    # Comprehension distractors from the same scene's other tiers too, so
    # every listening question has enough real lines to choose from.
    for other in TIERS:
        if other != tier:
            npc_pool += [e["npc"] for e in scene["tiers"][other]]

    questions: list[dict] = []
    for i, ex in enumerate(exchanges):
        f = focus.get(ex["focus"])
        base = {"scene": slug, "tier": tier, "turn": i, "focus_id": f.id if f else None, "rate": rules["rate"]}
        if i in rules["listen"]:
            others = [n for n in npc_pool if n["zh"] != ex["npc"]["zh"]]
            rng.shuffle(others)
            lines = [ex["npc"]] + others[:3 if tier == "advanced" else 2]
            rng.shuffle(lines)
            questions.append({
                **base, "type": "scene_listen", "item_type": "line",
                "item_id": next(k for k, l in enumerate(lines) if l["zh"] == ex["npc"]["zh"]),
                "option_ids": list(range(len(lines))),
                "options": [{"zh": l["zh"], "tr": l["tr"]} for l in lines],
                "npc": ex["npc"],
            })
        replies = [ex["reply"]] + [{"zh": w[0], "py": w[1]} for w in ex["wrong"]]
        rng.shuffle(replies)
        questions.append({
            **base, "type": "scene_reply", "item_type": "line",
            "item_id": next(k for k, r in enumerate(replies) if r["zh"] == ex["reply"]["zh"]),
            "option_ids": list(range(len(replies))),
            "options": [{"zh": r["zh"], "py": r.get("py") or ""} for r in replies],
            "npc": ex["npc"], "reply": ex["reply"],
            "say": {"zh": ex["reply"]["zh"], "keywords": [t["text"] for t in sent.segment(db, ex["reply"]["zh"])
                                                         if t["kind"] == "word"]},
        })

    # Words met in the conversation, then one grammar point it used.
    for k, w in enumerate(new_words(db, user, scene, tier, level, rules["new_words"])):
        q = practice._question(db, "vocab", w, k, rng, translated)
        if q:
            questions.append(q)
    levels = sent._level_map(db)
    # Grammar DNA: a strong learner may meet the next level's pattern; a weak
    # one gets one from an easier level (controlled, then reinforced).
    g_cap = level + 1 if ad["grammar"] == "stretch" else max(1, level - 1) if ad["grammar"] == "controlled" else level
    for g in sent.match_grammar(db, tier_lines(scene, tier)):
        if levels.get(g.hsk_level_id, 1) > g_cap:
            continue
        line = next((e["reply"]["zh"] for e in exchanges if _uses(g, e["reply"]["zh"])),
                    next((e["npc"]["zh"] for e in exchanges if _uses(g, e["npc"]["zh"])), None))
        q = practice._question(db, "grammar", g, 0, rng, translated)
        if q and line:
            q["prompt"] = line
            questions.append(q)
            break

    questions[0]["ctx"] = {
        "kind": "scene", "slug": slug, "tier": tier, "icon": scene["icon"],
        "rules": _public_rules(tier, ad),
    }
    return questions


def _uses(g: models.GrammarTopic, line: str) -> bool:
    return sent.uses_grammar(g.title, line)


def ctx_render(ctx: dict, locale: str) -> dict:
    scene = SCENE_BY_SLUG.get(ctx.get("slug") or "")
    if scene is None:
        return ctx
    return {
        **ctx, "title": scene_text(scene["title"], locale),
        "npc": {"zh": scene["npc"]["zh"], "role": scene_text(scene["npc"]["role"], locale)},
    }
