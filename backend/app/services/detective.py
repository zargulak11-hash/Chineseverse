"""Detective Mode: generated Chinese mystery cases, played as graded rounds.

A case is one of a few reusable STRUCTURES (who took it / where was it lost
/ who is lying), written as sentence frames at three tiers and filled with
real curriculum words (services/story_slots.py). What a learner gets is
built from their own data:

  tier            HSK level (user_rank): sentence frames, suspects, clues,
                  red herrings, how precise the times are
  words           the people, places and objects are real rows within
                  reach of their level, preferring words they're learning,
                  plus a new one or two -- the case teaches as it's played
  listening share Learning DNA: a learner whose listening is ahead of their
                  reading hears more clues; one whose listening lags hears
                  fewer (but always at least one)
  evidence notes  words from their own unresolved mistakes come back as
                  evidence to read (Review items, met in the story)
  grammar clue    a curriculum grammar point one of the clues really uses

Every clue is a graded question (reading or listening comprehension) whose
answer is a real word: a miss shows the clue with pinyin and a
word-by-word gloss, records the mistake on that word and schedules it for
review; the final deduction is reasoning over the clues. All grading is the
practice engine's (services/practice.py); nothing here writes progress.
"""

from __future__ import annotations

import random

from sqlalchemy.orm import Session

from app import models
from app.services import story_slots as ss
from app.services.story_slots import clock, fill, word_slot

TIERS = ("beginner", "intermediate", "advanced")
SUSPECTS = {"beginner": 3, "intermediate": 4, "advanced": 5}
EVIDENCE_NOTES = {"beginner": 1, "intermediate": 1, "advanced": 2}
BASE_LISTEN_SHARE = {"beginner": 0.25, "intermediate": 0.4, "advanced": 0.5}
NOT_SUSPECTS = {"同学", "朋友"}  # used by the frames themselves ("我的同学说…")


class CaseError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


F = dict  # tier -> (zh, py)

WHO_TOOK = {
    "title": ("谁拿走了我的{obj}？", "shéi ná zǒu le wǒ de {obj}?"),
    "intro": F(
        beginner=("我的{obj}不见了！{when}，{obj}在{place}。", "wǒ de {obj} bú jiàn le! {when}, {obj} zài {place}."),
        intermediate=("{when}左右，我把{obj}放在{place}，回来以后就找不到了。",
                      "{when} zuǒyòu, wǒ bǎ {obj} fàng zài {place}, huílái yǐhòu jiù zhǎo bu dào le."),
        advanced=("{when}左右，我把{obj}忘在了{place}，等我回去找的时候，它已经被人拿走了。",
                  "{when} zuǒyòu, wǒ bǎ {obj} wàng zài le {place}, děng wǒ huíqu zhǎo de shíhou, tā yǐjīng bèi rén ná zǒu le."),
    ),
    "alibi": F(
        beginner=("{when}，{who}在{place}。", "{when}, {who} zài {place}."),
        intermediate=("{who}说：“{when}的时候，我在{place}。”", "{who} shuō: “{when} de shíhou, wǒ zài {place}.”"),
        advanced=("好几个人都看见{who}{when}一直在{place}，没有离开过。",
                  "hǎo jǐ ge rén dōu kànjiàn {who} {when} yìzhí zài {place}, méiyǒu líkāi guo."),
    ),
    "culprit": F(
        beginner=("{when}，{who}在{place}。", "{when}, {who} zài {place}."),
        intermediate=("我的同学说，{when}的时候，他看见{who}在{place}。",
                      "wǒ de tóngxué shuō, {when} de shíhou, tā kànjiàn {who} zài {place}."),
        advanced=("监控显示，{when}的时候，只有{who}进过{place}。",
                  "jiānkòng xiǎnshì, {when} de shíhou, zhǐyǒu {who} jìn guo {place}."),
    ),
    "herring": F(
        intermediate=("{who}{when}去过{place}，可是很快就走了。", "{who} {when} qù guo {place}, kěshì hěn kuài jiù zǒu le."),
        advanced=("{who}{when}在{place}待了一会儿，不过离开的时候，{obj}还在。",
                  "{who} {when} zài {place} dāi le yíhuìr, búguò líkāi de shíhou, {obj} hái zài."),
    ),
}

WHERE_LOST = {
    "title": ("我的{obj}在哪儿？", "wǒ de {obj} zài nǎr?"),
    "intro": F(
        beginner=("我的{obj}找不到了。今天我去了很多地方。", "wǒ de {obj} zhǎo bu dào le. jīntiān wǒ qù le hěn duō dìfang."),
        intermediate=("今天我去了好几个地方，晚上才发现{obj}找不到了。",
                      "jīntiān wǒ qù le hǎo jǐ ge dìfang, wǎnshang cái fāxiàn {obj} zhǎo bu dào le."),
        advanced=("今天跑了一整天，直到晚上回家，我才发现{obj}不知道丢在哪儿了。",
                  "jīntiān pǎo le yì zhěng tiān, zhídào wǎnshang huí jiā, wǒ cái fāxiàn {obj} bù zhīdào diū zài nǎr le."),
    ),
    "have": F(
        beginner=("{when}，我在{place}，{obj}还在我这儿。", "{when}, wǒ zài {place}, {obj} hái zài wǒ zhèr."),
        intermediate=("{when}我到了{place}，那时候{obj}还在包里。", "{when} wǒ dào le {place}, nà shíhou {obj} hái zài bāo li."),
        advanced=("{when}到{place}的时候，我还确认过{obj}在包里。", "{when} dào {place} de shíhou, wǒ hái quèrèn guo {obj} zài bāo li."),
    ),
    "used": F(
        beginner=("{when}，我在{place}用了{obj}。", "{when}, wǒ zài {place} yòng le {obj}."),
        intermediate=("{when}在{place}，我把{obj}拿出来用了一下。", "{when} zài {place}, wǒ bǎ {obj} ná chūlai yòng le yíxià."),
        advanced=("{when}在{place}的时候，我把{obj}拿出来放在桌子上，后来就忘了。",
                  "{when} zài {place} de shíhou, wǒ bǎ {obj} ná chūlai fàng zài zhuōzi shang, hòulái jiù wàng le."),
    ),
    "missing": F(
        beginner=("{when}，我到了{place}，可是{obj}没有了！", "{when}, wǒ dào le {place}, kěshì {obj} méiyǒu le!"),
        intermediate=("{when}到{place}以后，我想用{obj}，可是怎么也找不到。",
                      "{when} dào {place} yǐhòu, wǒ xiǎng yòng {obj}, kěshì zěnme yě zhǎo bu dào."),
        advanced=("{when}到了{place}，我一摸包，{obj}已经不在了。", "{when} dào le {place}, wǒ yì mō bāo, {obj} yǐjīng bú zài le."),
    ),
    "recheck": F(
        advanced=("{when}我又回到{place}找了找，也没有。", "{when} wǒ yòu huí dào {place} zhǎo le zhǎo, yě méiyǒu."),
    ),
}

WHO_LIES = {
    "title": ("谁在说谎？", "shéi zài shuō huǎng?"),
    "intro": F(
        beginner=("昨天{when}，{place}的{obj}坏了。大家都说不是自己。",
                  "zuótiān {when}, {place} de {obj} huài le. dàjiā dōu shuō bú shì zìjǐ."),
        intermediate=("昨天{when}左右，有人把{place}的{obj}弄坏了。每个人都说自己当时不在那儿。",
                      "zuótiān {when} zuǒyòu, yǒu rén bǎ {place} de {obj} nòng huài le. měi ge rén dōu shuō zìjǐ dāngshí bú zài nàr."),
        advanced=("昨天{when}前后，{place}的{obj}被人弄坏了，可是没有一个人承认。",
                  "zuótiān {when} qiánhòu, {place} de {obj} bèi rén nòng huài le, kěshì méiyǒu yí ge rén chéngrèn."),
    ),
    "claim": F(
        beginner=("{who}：“我{when}在{place}。”", "{who}: “wǒ {when} zài {place}.”"),
        intermediate=("{who}说：“{when}我在{place}，一直没出去。”", "{who} shuō: “{when} wǒ zài {place}, yìzhí méi chūqu.”"),
        advanced=("{who}坚持说：“{when}的时候，我明明在{place}，好多人都能证明。”",
                  "{who} jiānchí shuō: “{when} de shíhou, wǒ míngmíng zài {place}, hǎo duō rén dōu néng zhèngmíng.”"),
    ),
    "witness": F(
        beginner=("可是，{when}我在{place}看见了{who}。", "kěshì, {when} wǒ zài {place} kànjiàn le {who}."),
        intermediate=("可是有人说，{when}的时候，在{place}看见了{who}。",
                      "kěshì yǒu rén shuō, {when} de shíhou, zài {place} kànjiàn le {who}."),
        advanced=("但是监控显示，{when}的时候，{who}正在{place}门口。",
                  "dànshì jiānkòng xiǎnshì, {when} de shíhou, {who} zhèng zài {place} ménkǒu."),
    ),
}

STRUCTURES = {"who_took": WHO_TOOK, "where_lost": WHERE_LOST, "who_lies": WHO_LIES}
ICONS = {"who_took": "🕵️", "where_lost": "🔎", "who_lies": "🎭"}


# --------------------------------------------------------------------------- profile

def _skill(user: models.User, code: str) -> float:
    us = next((s for s in user.user_skills if s.skill and s.skill.code == code), None)
    return round(us.mastery, 1) if us else 0.0


def _evidence_rows(db: Session, user: models.User, reach: int, limit: int) -> list[models.VocabularyWord]:
    """Words from the learner's own unresolved mistakes, within reach."""
    from app.services import practice

    if limit <= 0:
        return []
    refs = [m.reference for m in db.query(models.LearningMistake).filter(
        models.LearningMistake.user_id == user.id, models.LearningMistake.mastered.is_(False),
        models.LearningMistake.mistake_type.in_(("word", "tone", "pinyin")),
    ).order_by(models.LearningMistake.priority.desc(), models.LearningMistake.id).limit(30)]
    if not refs:
        return []
    levels = {lvl.id: lvl.level for lvl in db.query(models.HSKLevel).all()}
    rows = db.query(models.VocabularyWord).filter(models.VocabularyWord.simplified.in_(refs)).all()
    best: dict[str, models.VocabularyWord] = {}
    for r in sorted(rows, key=lambda r: (levels.get(r.hsk_level_id, 99), r.id)):
        best.setdefault(r.simplified, r)
    out = [best[x] for x in refs if x in best and practice._usable("vocab", best[x])
           and levels.get(best[x].hsk_level_id, 1) <= reach]
    return list(dict.fromkeys(out))[:limit]


def profile(db: Session, user: models.User) -> dict:
    """How this learner's cases are built, from their real data."""
    from app.services.gamification import ensure_user_skills, user_rank
    from app.services.sentence import tier_for

    ensure_user_skills(db, user)
    level, _ = user_rank(db, user)
    tier = tier_for(level)
    reading, listening = _skill(user, "reading"), _skill(user, "listening")
    share = BASE_LISTEN_SHARE[tier]
    if listening >= reading + 10:
        share += 0.2   # a strong listener gets more audio clues
    elif listening + 15 < reading:
        share -= 0.1   # a weak listener gets fewer -- but never none
    share = max(0.2, min(0.8, share))
    evidence = _evidence_rows(db, user, level + 1, EVIDENCE_NOTES[tier])
    return {
        "level": level, "tier": tier, "suspects": SUSPECTS[tier], "listen_share": round(share, 2),
        "reading": reading, "listening": listening, "evidence_notes": len(evidence),
        "red_herring": tier != "beginner",
    }


def _times(rng: random.Random, tier: str, n: int, start: int = 8) -> list[dict]:
    """n increasing clock times; precision grows with the tier."""
    minutes = {"beginner": (0,), "intermediate": (0, 30), "advanced": (0, 15, 30, 45)}[tier]
    hour = rng.randint(start, 11)
    out = []
    for _ in range(n):
        out.append(clock(hour, rng.choice(minutes)))
        hour += rng.randint(1, 2)
    return out


def _where_q(clue: dict, mode: str, answer: models.VocabularyWord, places: list[models.VocabularyWord],
             ask: dict, rng: random.Random, tier: str) -> dict:
    opts = [answer] + [p for p in places if p.id != answer.id]
    opts = opts[: (4 if tier != "beginner" else 3)]
    rng.shuffle(opts)
    return {
        "type": "case_clue", "item_type": "case", "mode": mode, "clue": clue, "ask": ask,
        "item_id": next(i for i, o in enumerate(opts) if o.id == answer.id),
        "option_ids": list(range(len(opts))),
        "options": [{"word_id": o.id, "zh": o.simplified, "py": o.pinyin} for o in opts],
        "focus_id": answer.id, "answer_kind": "word",
    }


def _when_q(clue: dict, mode: str, answer: dict, others: list[dict], ask: dict, focus_id: int | None,
            rng: random.Random) -> dict:
    distinct = {t["label"]: t for t in others if t["label"] != answer["label"]}
    opts = [answer] + list(distinct.values())[:3]
    rng.shuffle(opts)
    return {
        "type": "case_clue", "item_type": "case", "mode": mode, "clue": clue, "ask": ask,
        "item_id": next(i for i, o in enumerate(opts) if o["label"] == answer["label"]),
        "option_ids": list(range(len(opts))),
        "options": [{"label": o["label"], "zh": o["zh"], "py": o["py"]} for o in opts],
        "focus_id": focus_id, "answer_kind": "time",
    }


def _modes(n: int, share: float) -> list[str]:
    """Which clues are heard rather than read: evenly spread, at least one."""
    k = max(1, round(n * share))
    picks = {round((i + 1) * n / (k + 1)) for i in range(k)}
    picks = {min(n - 1, max(0, p)) for p in picks}
    return ["listen" if i in picks else "read" for i in range(n)]


def build_questions(db: Session, user: models.User, case: str, level: int, rng: random.Random,
                    translated: dict | None) -> list[dict]:
    from app.services import practice
    from app.services import sentence as sent

    if case not in STRUCTURES:
        raise CaseError(404, "Case not found")
    prof = profile(db, user)
    tier = prof["tier"]
    S = STRUCTURES[case]
    slots = ss.Slots(db, user, level, rng, stretch=1)
    n = prof["suspects"]
    obj = slots.pick("object", 1)[0]
    places = slots.pick("place", n + 1)
    if len(places) < 3:
        raise CaseError(422, "Not enough curriculum words to build this case yet")
    clues: list[tuple[dict, str, dict]] = []  # (clue, kind, data)

    if case == "who_took":
        people = [p for p in slots.pick("person", n + 2) if p.simplified not in NOT_SUSPECTS][:n]
        crime_place, others = places[0], places[1:]
        times = _times(rng, tier, 2)
        before, crime = times[0], times[1]
        culprit = rng.choice(people)
        title = fill(S["title"], obj=word_slot(obj))
        intro = fill(S["intro"][tier], obj=word_slot(obj), when=crime, place=word_slot(crime_place))
        herring = None
        if prof["red_herring"]:
            herring = rng.choice([p for p in people if p is not culprit])
        for i, p in enumerate(people):
            if p is culprit:
                clue = fill(S["culprit"][tier], who=word_slot(p), when=crime, place=word_slot(crime_place))
                clues.append((clue, "where", {"who": p, "answer": crime_place, "time": crime}))
            elif p is herring:
                clue = fill(S["herring"][tier], who=word_slot(p), when=before, place=word_slot(crime_place), obj=word_slot(obj))
                clues.append((clue, "when", {"who": p, "answer": before, "others": [crime] + _times(rng, tier, 3, 7),
                                             "place": crime_place}))
            else:
                elsewhere = others[i % len(others)]
                clue = fill(S["alibi"][tier], who=word_slot(p), when=crime, place=word_slot(elsewhere))
                clues.append((clue, "where", {"who": p, "answer": elsewhere, "time": crime}))
        rng.shuffle(clues)
        suspects, answer_idx = people, people.index(culprit)
        final_title = title
    elif case == "where_lost":
        steps = {"beginner": ["have", "used", "missing"], "intermediate": ["have", "have", "used", "missing"],
                 "advanced": ["have", "have", "used", "missing", "recheck"]}[tier]
        visit = places[: len(steps) - (1 if "recheck" in steps else 0)]
        times = _times(rng, tier, len(steps))
        title = fill(S["title"], obj=word_slot(obj))
        intro = fill(S["intro"][tier], obj=word_slot(obj))
        used_place = None
        for i, step in enumerate(steps):
            place = visit[0] if step == "recheck" else visit[i]
            if step == "used":
                used_place = place
            clue = fill(S[step][tier], when=times[i], place=word_slot(place), obj=word_slot(obj))
            if i % 2 == 0:
                clues.append((clue, "where", {"who": None, "answer": place, "time": times[i]}))
            else:
                clues.append((clue, "when", {"who": None, "answer": times[i], "others": times, "place": place}))
        suspects = visit
        answer_idx = visit.index(used_place)
        final_title = fill(("我的{obj}可能在哪儿？", "wǒ de {obj} kěnéng zài nǎr?"), obj=word_slot(obj))
    else:  # who_lies
        people = [p for p in slots.pick("person", n + 2) if p.simplified not in NOT_SUSPECTS][:n]
        crime_place, others = places[0], places[1:]
        crime = _times(rng, tier, 1)[0]
        liar = rng.choice(people)
        # Something that can actually break (not a photo or a scarf).
        obj = slots.pick("breakable", 1)[0]
        title = fill(S["title"])
        intro = fill(S["intro"][tier], when=crime, place=word_slot(crime_place), obj=word_slot(obj))
        for i, p in enumerate(people):
            claimed = others[i % len(others)]
            clue = fill(S["claim"][tier], who=word_slot(p), when=crime, place=word_slot(claimed))
            clues.append((clue, "where_say", {"who": p, "answer": claimed, "time": crime}))
        witness = fill(S["witness"][tier], who=word_slot(liar), when=crime, place=word_slot(crime_place))
        clues.append((witness, "where_seen", {"who": liar, "answer": crime_place, "time": crime}))
        suspects, answer_idx = people, people.index(liar)
        final_title = title

    modes = _modes(len(clues), prof["listen_share"])
    questions: list[dict] = []
    for (clue, kind, data), mode in zip(clues, modes):
        ask = {"kind": kind, "who": data["who"].id if data.get("who") is not None else None,
               "time": data["time"]["label"] if data.get("time") else None,
               "place": data["place"].id if data.get("place") is not None else None}
        if kind == "when":
            q = _when_q(clue, mode, data["answer"], data["others"], ask,
                        data["who"].id if data.get("who") is not None else data["place"].id, rng)
        else:
            q = _where_q(clue, mode, data["answer"], places, ask, rng, tier)
        questions.append(q)

    # Evidence notes: the learner's own unresolved mistakes, met as clues.
    for k, w in enumerate(_evidence_rows(db, user, level + 1, EVIDENCE_NOTES[tier])):
        q = practice._question(db, "vocab", w, k + 1, rng, translated)
        if q:
            q["tag"] = "evidence"
            questions.insert(min(len(questions), 2 + k * 2), q)

    # A grammar point one of the clues really uses.
    levels = {lvl.id: lvl.level for lvl in db.query(models.HSKLevel).all()}
    for clue, _kind, _data in clues:
        g = next((g for g in sent.match_grammar(db, clue["zh"]) if levels.get(g.hsk_level_id, 1) <= level), None)
        if g is None:
            continue
        q = practice._question(db, "grammar", g, 0, rng, translated)
        if q:
            q["prompt"] = clue["zh"]
            q["tag"] = "grammar_clue"
            questions.append(q)
        break

    # The deduction.
    order = list(range(len(suspects)))
    rng.shuffle(order)
    questions.append({
        "type": "case_deduce", "item_type": "case", "question": final_title,
        "item_id": order.index(answer_idx), "option_ids": list(range(len(order))),
        "options": [{"word_id": suspects[i].id, "zh": suspects[i].simplified, "py": suspects[i].pinyin} for i in order],
        "focus_id": suspects[answer_idx].id, "answer_kind": "deduce", "tier": tier,
        "solution": [c["zh"] for c, _k, _d in clues],
    })
    for q in questions:
        if q["item_type"] == "case":
            q["tier"] = tier
    questions[0]["ctx"] = {"kind": "case", "case": case, "tier": tier, "icon": ICONS[case],
                           "title": title, "intro": intro, "profile": prof}
    return questions


# --------------------------------------------------------------------------- rendering

def render(db: Session, q: dict, answered: bool, locale: str) -> tuple[dict, list[dict]]:
    tier = q.get("tier")
    word_ids = [o["word_id"] for o in q["options"] if o.get("word_id")]
    ask = q.get("ask") or {}
    m = ss.meanings(db, [x for x in (ask.get("who"), ask.get("place")) if x], locale)
    om = ss.meanings(db, word_ids, locale, uniform=True)
    if q["type"] == "case_deduce":
        options = [{"id": i, "label": o["zh"], "pinyin": o["py"] if tier == "beginner" else None}
                   for i, o in enumerate(q["options"])]
        return {"text": q["question"]["zh"], "pinyin": q["question"]["py"] if tier != "advanced" else None,
                "speak": q["question"]["zh"]}, options
    if q.get("answer_kind") == "time":
        options = [{"id": i, "label": o["label"]} for i, o in enumerate(q["options"])]
    else:
        options = [{"id": i, "label": om.get(o["word_id"], o["zh"])} for i, o in enumerate(q["options"])]
    clue = q["clue"]
    show = q["mode"] == "read" or answered
    prompt = {
        "mode": q["mode"], "speak": clue["zh"],
        "text": clue["zh"] if show else None,
        # Pinyin while reading at the lower tiers; always after answering.
        "pinyin": clue["py"] if (answered or (q["mode"] == "read" and tier == "beginner")) else None,
        "fallback": clue["py"],  # read on a device with no Chinese voice
        "ask": {"kind": ask.get("kind"), "time": ask.get("time"),
                "who": m.get(ask.get("who"), "") if ask.get("who") else "",
                "place": m.get(ask.get("place"), "") if ask.get("place") else ""},
    }
    return prompt, options


def card(db: Session, q: dict, locale: str) -> dict:
    if q["type"] == "case_deduce":
        o = q["options"][q["item_id"]]
        return {"hanzi": o["zh"], "pinyin": o["py"], "meaning": ss.meanings(db, [o["word_id"]], locale).get(o["word_id"], ""),
                "solution": q.get("solution") or []}
    o = q["options"][q["item_id"]]
    meaning = o.get("label") or ss.meanings(db, [o["word_id"]], locale).get(o.get("word_id"), "")
    return {"hanzi": q["clue"]["zh"], "pinyin": q["clue"]["py"], "meaning": meaning,
            "answer_zh": o["zh"], "gloss": ss.gloss(db, q["clue"]["zh"], locale)}


def case_list(db: Session, user: models.User) -> dict:
    """The case files and this learner's real record with each."""
    prof = profile(db, user)
    history: dict[str, dict] = {k: {"played": 0, "solved": 0, "best": 0.0} for k in STRUCTURES}
    rows = db.query(models.PracticeSession).filter(
        models.PracticeSession.user_id == user.id, models.PracticeSession.source == "detective",
        models.PracticeSession.completed_at.isnot(None)).all()
    for s in rows:
        ctx = (s.questions or [{}])[0].get("ctx") or {}
        h = history.get(ctx.get("case"))
        if h is None:
            continue
        h["played"] += 1
        h["best"] = max(h["best"], s.score or 0.0)
        final = s.answers[-1] if s.answers else None
        if final and final.get("correct"):
            h["solved"] += 1
    return {"profile": prof, "cases": [{"key": k, "icon": ICONS[k], **history[k]} for k in STRUCTURES]}
