"""Chinese Sound World: immersive listening rounds in real places.

The learner stands in a place (night market, station, school ...) and
hears several people speak. Lines are sentence frames filled with real
curriculum words (services/story_slots.py) -- or, for "respond to a
person", a real exchange from the matching Real Chinese scene at the
learner's tier -- so every answer is about a real word that goes through
apply_srs, mistakes and review.

Interactions: identify what someone said, pick out information
(platform, price, time, floor ...), respond to a person, find something,
follow a two-person conversation, and remember who said what.

Speed is a real progression, four stages:
  1 slow · 2 normal · 3 faster natural · 4 native speed
A stage opens when the learner has passed the stage below it in Sound
World (a completed round at >= PASS_SCORE), or from their Learning DNA
listening skill (a head start); stages 3 and 4 also need an HSK level
where natural-speed material is appropriate. Nothing here is guessed --
stage_status reads the learner's own stored rounds and DNA.
"""

from __future__ import annotations

import random

from sqlalchemy.orm import Session

from app import models
from app.services import story_slots as ss
from app.services.story_slots import clock, fill, number, word_slot

STAGE_RATE = {1: 0.7, 2: 0.9, 3: 1.08, 4: 1.25}
STAGE_MIN_LEVEL = {1: 1, 2: 1, 3: 2, 4: 4}
PASS_SCORE = 80.0

# speaker key -> (Chinese label, pitch, rate factor). Different pitch/rate
# per speaker is what makes several voices out of one Chinese TTS voice.
SPEAKERS = {
    "vendor": ("摊主", 0.85, 1.0), "customer": ("顾客", 1.2, 1.0), "friend": ("朋友", 1.05, 1.05),
    "waiter": ("服务员", 1.15, 1.05), "cook": ("厨师", 0.8, 0.95), "announcer": ("广播", 1.0, 0.95),
    "passenger": ("乘客", 1.1, 1.0), "staff": ("工作人员", 0.95, 1.0), "teacher": ("老师", 1.0, 0.95),
    "student": ("学生", 1.25, 1.05), "local": ("路人", 0.9, 1.05), "clerk": ("店员", 1.15, 1.0),
}

ENVS = {
    "night_market": {"icon": "🏮", "zh": "夜市", "items": "food", "speakers": ("vendor", "customer", "friend"),
                     "scene": "shopping", "info": "price"},
    "restaurant": {"icon": "🍜", "zh": "饭馆", "items": "food", "speakers": ("waiter", "customer", "cook"),
                   "scene": "restaurant", "info": "total"},
    "train_station": {"icon": "🚉", "zh": "火车站", "items": "station_place", "speakers": ("announcer", "passenger", "staff"),
                      "scene": "train-station", "info": "platform"},
    "school": {"icon": "🏫", "zh": "学校", "items": "school_place", "speakers": ("teacher", "student", "friend"),
               "scene": "university", "info": "room"},
    "street": {"icon": "🚦", "zh": "街上", "items": "street_place", "speakers": ("local", "friend", "passenger"),
               "scene": "travel", "info": "bus"},
    "airport": {"icon": "✈️", "zh": "机场", "items": "travel_object", "speakers": ("announcer", "staff", "passenger"),
                "scene": "airport", "info": "takeoff"},
    "shopping": {"icon": "🛍️", "zh": "商场", "items": "clothes", "speakers": ("clerk", "customer", "friend"),
                 "scene": "shopping", "info": "floor"},
}

T = dict
IDENTIFY = {
    "food": T(beginner=("我要{item}。", "wǒ yào {item}."),
              intermediate=("今天的{item}特别好，来一点儿吧？", "jīntiān de {item} tèbié hǎo, lái yìdiǎnr ba?"),
              advanced=("要说这儿最有名的，还得是我们家的{item}，别的地方吃不到。",
                        "yào shuō zhèr zuì yǒumíng de, hái děi shì wǒmen jiā de {item}, bié de dìfang chī bu dào.")),
    "place": T(beginner=("我去{item}。", "wǒ qù {item}."),
               intermediate=("你知道{item}怎么走吗？", "nǐ zhīdào {item} zěnme zǒu ma?"),
               advanced=("麻烦问一下，从这儿到{item}，走路大概要多长时间？",
                         "máfan wèn yíxià, cóng zhèr dào {item}, zǒu lù dàgài yào duō cháng shíjiān?")),
    "object": T(beginner=("我的{item}在这儿。", "wǒ de {item} zài zhèr."),
                intermediate=("请把你的{item}放在这里。", "qǐng bǎ nǐ de {item} fàng zài zhèlǐ."),
                advanced=("您的{item}需要单独拿出来检查一下，谢谢配合。",
                          "nín de {item} xūyào dāndú ná chūlai jiǎnchá yíxià, xièxie pèihé.")),
    "clothes": T(beginner=("我想买{item}。", "wǒ xiǎng mǎi {item}."),
                 intermediate=("这种颜色的{item}还有大一点儿的吗？", "zhè zhǒng yánsè de {item} hái yǒu dà yìdiǎnr de ma?"),
                 advanced=("这款{item}是今年的新款，现在买还能打八折。",
                           "zhè kuǎn {item} shì jīnnián de xīn kuǎn, xiànzài mǎi hái néng dǎ bā zhé.")),
}

# Information frames: {value} is the answer (a number or a clock time).
INFO = {
    "price": T(beginner=("{item}{value}一斤。", "{item} {value} yì jīn."),
               intermediate=("{item}今天便宜，{value}钱一斤。", "{item} jīntiān piányi, {value} qián yì jīn."),
               advanced=("{item}本来不便宜，今天收摊前给你算{value}一斤，要不要？",
                         "{item} běnlái bù piányi, jīntiān shōu tān qián gěi nǐ suàn {value} yì jīn, yào bu yào?")),
    "total": T(beginner=("一共{value}。", "yígòng {value}."),
               intermediate=("您好，{item}和饮料，一共{value}。", "nín hǎo, {item} hé yǐnliào, yígòng {value}."),
               advanced=("您点的{item}加上服务费，一共是{value}，可以扫码付款。",
                         "nín diǎn de {item} jiā shàng fúwù fèi, yígòng shì {value}, kěyǐ sǎo mǎ fùkuǎn.")),
    "platform": T(beginner=("火车在{value}号站台。", "huǒchē zài {value} hào zhàntái."),
                  intermediate=("开往北京的火车，在{value}号站台上车。", "kāiwǎng Běijīng de huǒchē, zài {value} hào zhàntái shàng chē."),
                  advanced=("各位旅客请注意，开往北京的列车现在开始检票，请到{value}号站台上车。",
                            "gèwèi lǚkè qǐng zhùyì, kāiwǎng Běijīng de lièchē xiànzài kāishǐ jiǎnpiào, qǐng dào {value} hào zhàntái shàng chē.")),
    "room": T(beginner=("我们在{value}号教室上课。", "wǒmen zài {value} hào jiàoshì shàng kè."),
              intermediate=("同学们，明天的考试在{value}号教室，别走错了。", "tóngxuémen, míngtiān de kǎoshì zài {value} hào jiàoshì, bié zǒu cuò le."),
              advanced=("请注意，因为原来的教室在维修，下午的讲座改到{value}号教室举行。",
                        "qǐng zhùyì, yīnwèi yuánlái de jiàoshì zài wéixiū, xiàwǔ de jiǎngzuò gǎi dào {value} hào jiàoshì jǔxíng.")),
    "bus": T(beginner=("去{item}，坐{value}路车。", "qù {item}, zuò {value} lù chē."),
             intermediate=("你要去{item}的话，在这儿坐{value}路公共汽车就行。", "nǐ yào qù {item} de huà, zài zhèr zuò {value} lù gōnggòng qìchē jiù xíng."),
             advanced=("去{item}最方便的是{value}路，不过这个时间堵车，你最好坐地铁。",
                       "qù {item} zuì fāngbiàn de shì {value} lù, búguò zhège shíjiān dǔ chē, nǐ zuìhǎo zuò dìtiě.")),
    "takeoff": T(beginner=("飞机{value}起飞。", "fēijī {value} qǐfēi."),
                 intermediate=("去北京的飞机{value}起飞，请大家早一点儿去登机。", "qù Běijīng de fēijī {value} qǐfēi, qǐng dàjiā zǎo yìdiǎnr qù dēngjī."),
                 advanced=("各位旅客，由于天气原因，飞往北京的航班推迟到{value}起飞，请耐心等候。",
                           "gèwèi lǚkè, yóuyú tiānqì yuányīn, fēi wǎng Běijīng de hángbān tuīchí dào {value} qǐfēi, qǐng nàixīn děnghòu.")),
    "floor": T(beginner=("{item}在{value}楼。", "{item} zài {value} lóu."),
               intermediate=("您要买{item}的话，请到{value}楼。", "nín yào mǎi {item} de huà, qǐng dào {value} lóu."),
               advanced=("{item}专柜搬到{value}楼了，坐电梯上去，出来往右走就是。",
                         "{item} zhuānguì bān dào {value} lóu le, zuò diàntī shàngqu, chūlai wǎng yòu zǒu jiù shì.")),
}
INFO_KIND = {"price": "money", "total": "money", "platform": "number", "room": "number", "bus": "number",
             "takeoff": "time", "floor": "number"}

FIND_PLACE = T(beginner=("{a}在{pa}，{b}在{pb}。", "{a} zài {pa}, {b} zài {pb}."),
               intermediate=("你要找的{a}就在{pa}，{b}在{pb}。", "nǐ yào zhǎo de {a} jiù zài {pa}, {b} zài {pb}."),
               advanced=("{a}不远，就在{pa}；{b}稍微远一点儿，在{pb}。",
                         "{a} bù yuǎn, jiù zài {pa}; {b} shāowēi yuǎn yìdiǎnr, zài {pb}."))
# Things (food, objects, clothes) are put somewhere; places just are.
FIND = T(beginner=("{a}在{pa}，{b}在{pb}。", "{a} zài {pa}, {b} zài {pb}."),
         intermediate=("你要的{a}在{pa}，{b}在{pb}，别走错了。", "nǐ yào de {a} zài {pa}, {b} zài {pb}, bié zǒu cuò le."),
         advanced=("{a}放在{pa}了，{b}呢，好像在{pb}，你自己去看看吧。",
                   "{a} fàng zài {pa} le, {b} ne, hǎoxiàng zài {pb}, nǐ zìjǐ qù kànkan ba."))

CONVERSATION = {
    "food": T(beginner=(("老板，{item}来{n}。", "lǎobǎn, {item} lái {n}."),
                        ("好的，一共{price}。", "hǎo de, yígòng {price}.")),
              intermediate=(("你好，我想要{n}{item}，打包带走。", "nǐ hǎo, wǒ xiǎng yào {n} {item}, dǎbāo dài zǒu."),
                            ("没问题，{n}一共{price}，请稍等。", "méi wèntí, {n} yígòng {price}, qǐng shāo děng.")),
              advanced=(("麻烦给我来{n}{item}，一份不要辣，其他的正常。", "máfan gěi wǒ lái {n} {item}, yí fèn bú yào là, qítā de zhèngcháng."),
                        ("好嘞，{n}{item}，一共{price}，扫码还是现金？", "hǎo lei, {n} {item}, yígòng {price}, sǎo mǎ háishi xiànjīn?"))),
    # Things you can buy: price, and a cheaper deal for {n}.
    "goods": T(beginner=(("这个{item}多少钱？", "zhège {item} duōshao qián?"), ("{price}，买{n}更便宜。", "{price}, mǎi {n} gèng piányi.")),
               intermediate=(("请问{item}多少钱？", "qǐngwèn {item} duōshao qián?"),
                             ("{price}，要是买{n}，可以便宜一点儿。", "{price}, yàoshi mǎi {n}, kěyǐ piányi yìdiǎnr.")),
               advanced=(("这个{item}能不能再便宜点儿？", "zhège {item} néng bu néng zài piányi diǎnr?"),
                         ("最低{price}，你买{n}的话，我再送你一个小礼物。", "zuì dī {price}, nǐ mǎi {n} de huà, wǒ zài sòng nǐ yí ge xiǎo lǐwù."))),
    # Places: which bus ({n}) and how many minutes ({price} slot unused).
    "place": T(beginner=(("请问，去{item}坐几路车？", "qǐngwèn, qù {item} zuò jǐ lù chē?"), ("坐{n}车。", "zuò {n} chē.")),
               intermediate=(("你好，我想去{item}，坐哪路车方便？", "nǐ hǎo, wǒ xiǎng qù {item}, zuò nǎ lù chē fāngbiàn?"),
                             ("坐{n}车就行，在前边上车。", "zuò {n} chē jiù xíng, zài qiánbian shàng chē.")),
               advanced=(("麻烦问一下，去{item}有没有直达的公交？", "máfan wèn yíxià, qù {item} yǒu méiyǒu zhídá de gōngjiāo?"),
                         ("有，{n}车直达，不过这个时间人多，你得早点儿去排队。", "yǒu, {n} chē zhídá, búguò zhège shíjiān rén duō, nǐ děi zǎo diǎnr qù páiduì."))),
}
CONV_UNIT = {"food": ("份", "fèn"), "goods": ("个", "gè"), "place": ("路", "lù")}
CONV_KIND = {"food": "food", "clothes": "goods", "travel_object": "goods", "object": "goods"}

IDENTIFY_KIND = {"station_place": "place", "school_place": "place", "street_place": "place", "travel_object": "object"}
TIER_ORDER = ["beginner", "intermediate", "advanced"]

PLAN = {
    "beginner": ["identify", "info", "find", "respond", "conversation", "memory"],
    "intermediate": ["identify", "info", "find", "respond", "conversation", "identify", "info", "memory"],
    "advanced": ["identify", "info", "find", "respond", "conversation", "respond", "info", "identify", "memory"],
}


class SoundError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


# --------------------------------------------------------------------------- progression

def stage_status(db: Session, user: models.User) -> dict:
    """Which speeds this learner has opened, from their real Sound World
    rounds and Learning DNA listening skill."""
    from app.services.gamification import ensure_user_skills, user_rank

    ensure_user_skills(db, user)
    level, _ = user_rank(db, user)
    listening = next((s.mastery for s in user.user_skills if s.skill and s.skill.code == "listening"), 0.0) or 0.0
    best: dict[int, float] = {}
    rounds: dict[int, int] = {}
    for s in db.query(models.PracticeSession).filter(
            models.PracticeSession.user_id == user.id, models.PracticeSession.source == "sound",
            models.PracticeSession.completed_at.isnot(None)):
        stage = ((s.questions or [{}])[0].get("ctx") or {}).get("stage")
        if stage:
            best[stage] = max(best.get(stage, 0.0), s.score or 0.0)
            rounds[stage] = rounds.get(stage, 0) + 1
    unlocked = 1
    if listening >= 40:
        unlocked = 2
    if listening >= 70:
        unlocked = 3
    for stage in (1, 2, 3):
        if best.get(stage, 0.0) >= PASS_SCORE:
            unlocked = max(unlocked, stage + 1)
    level_cap = max(s for s, lvl in STAGE_MIN_LEVEL.items() if level >= lvl)
    unlocked = min(unlocked, level_cap)
    stages = []
    for stage in (1, 2, 3, 4):
        reason = None
        if stage > level_cap:
            reason = "level"
        elif stage > unlocked:
            reason = "pass_previous"
        stages.append({"stage": stage, "rate": STAGE_RATE[stage], "unlocked": stage <= unlocked,
                       "best": best.get(stage, 0.0), "rounds": rounds.get(stage, 0), "locked_reason": reason,
                       "min_level": STAGE_MIN_LEVEL[stage]})
    return {"level": level, "listening": round(listening, 1), "unlocked": unlocked, "recommended": unlocked,
            "pass_score": PASS_SCORE, "stages": stages}


def env_list(db: Session, user: models.User) -> dict:
    from app.services.sentence import tier_for

    status = stage_status(db, user)
    played: dict[str, dict] = {k: {"rounds": 0, "best": 0.0} for k in ENVS}
    for s in db.query(models.PracticeSession).filter(
            models.PracticeSession.user_id == user.id, models.PracticeSession.source == "sound",
            models.PracticeSession.completed_at.isnot(None)):
        env = ((s.questions or [{}])[0].get("ctx") or {}).get("env")
        if env in played:
            played[env]["rounds"] += 1
            played[env]["best"] = max(played[env]["best"], s.score or 0.0)
    return {**status, "tier": tier_for(status["level"]),
            "envs": [{"key": k, "icon": e["icon"], "zh": e["zh"], "speakers": list(e["speakers"]), **played[k]}
                     for k, e in ENVS.items()]}


# --------------------------------------------------------------------------- building

def _line(speaker: str, text: dict, stage: int, label: str | None = None) -> dict:
    """One spoken line. speaker "npc" is the person of a Real Chinese scene
    (their own Chinese title, e.g. 导游), with a neutral voice."""
    base_label, pitch, rate = SPEAKERS.get(speaker, ("", 1.0, 1.0))
    label = label or base_label
    return {"speaker": speaker, "speaker_zh": label, "zh": text["zh"], "py": text["py"],
            "pitch": pitch, "rate": round(STAGE_RATE[stage] * rate, 2)}


def _value(kind: str, rng: random.Random, tier: str) -> dict:
    if kind == "money":
        n = rng.choice((5, 8, 10, 12, 15, 18, 20, 25, 30, 35, 45)) if tier != "advanced" else rng.randint(12, 98)
        return number(n, "块", "kuài")
    if kind == "time":
        return clock(rng.randint(8, 21), rng.choice((0, 30) if tier != "advanced" else (0, 15, 30, 45)))
    return number(rng.randint(1, 9) if tier == "beginner" else rng.randint(2, 30))


def _values_like(answer: dict, kind: str, rng: random.Random, tier: str) -> list[dict]:
    out = {answer["label"]: answer}
    for _ in range(40):
        v = _value(kind, rng, tier)
        out.setdefault(v["label"], v)
        if len(out) >= 4:
            break
    vals = list(out.values())
    rng.shuffle(vals)
    return vals


def _word_options(answer: models.VocabularyWord, pool: list[models.VocabularyWord], rng: random.Random, k: int) -> list:
    opts = [answer] + [w for w in pool if w.id != answer.id][: k - 1]
    rng.shuffle(opts)
    return opts


def build_questions(db: Session, user: models.User, env: str, stage: int, level: int, rng: random.Random,
                    translated: dict | None) -> list[dict]:
    from app.services import real_life
    from app.services import sentence as sent

    if env not in ENVS:
        raise SoundError(404, "Place not found")
    status = stage_status(db, user)
    if not 1 <= stage <= 4:
        raise SoundError(422, "stage must be 1-4")
    if stage > status["unlocked"]:
        raise SoundError(403, "This speed isn't unlocked yet")
    tier = sent.tier_for(level)
    E = ENVS[env]
    slots = ss.Slots(db, user, level, rng, stretch=1)
    items = slots.pick(E["items"], 6, new_words=2)
    positions = slots.pick("position", 4, new_words=1)
    if len(items) < 4 or len(positions) < 3:
        raise SoundError(422, "Not enough curriculum words to build this place yet")
    speakers = E["speakers"]
    n_opts = 3 if tier == "beginner" else 4
    questions: list[dict] = []
    item_i = 0

    def next_item():
        nonlocal item_i
        w = items[item_i % len(items)]
        item_i += 1
        return w

    scene = real_life.SCENE_BY_SLUG.get(E["scene"])
    exchanges = list(scene["tiers"][tier]) if scene else []
    rng.shuffle(exchanges)

    # People talk to the learner; the announcer only announces.
    talkers = [s for s in speakers if s != "announcer"]
    # In a two-person exchange the visitor asks and the local answers.
    asker = next((s for s in talkers if s in ("customer", "passenger", "student")), talkers[-1])
    answerer = next((s for s in talkers if s != asker), talkers[0])
    for kind in PLAN[tier]:
        sp = talkers[len(questions) % len(talkers)]
        if kind == "identify":
            w = next_item()
            text = fill(IDENTIFY[IDENTIFY_KIND.get(E["items"], E["items"])][tier], item=word_slot(w))
            opts = _word_options(w, items, rng, n_opts)
            questions.append({"type": "sound_identify", "lines": [_line(sp, text, stage)],
                              "options": [{"word_id": o.id, "zh": o.simplified} for o in opts],
                              "item_id": next(i for i, o in enumerate(opts) if o.id == w.id), "focus_id": w.id,
                              "answer_kind": "word"})
        elif kind == "info":
            w = next_item()
            vk = INFO_KIND[E["info"]]
            value = _value(vk, rng, tier)
            text = fill(INFO[E["info"]][tier], item=word_slot(w), value=value)
            vals = _values_like(value, vk, rng, tier)[:n_opts]
            if value not in vals:
                vals[-1] = value
                rng.shuffle(vals)
            questions.append({"type": "sound_info", "info": E["info"], "lines": [_line(speakers[0], text, stage)],
                              "options": [{"label": v["label"], "zh": v["zh"]} for v in vals],
                              "item_id": next(i for i, v in enumerate(vals) if v["label"] == value["label"]),
                              "focus_id": w.id if "{item}" in INFO[E["info"]][tier][0] else None,
                              "answer_kind": "value", "ask_item": w.id})
        elif kind == "find":
            a, b = next_item(), next_item()
            pa, pb = positions[0], positions[1]
            frames = FIND_PLACE if IDENTIFY_KIND.get(E["items"], E["items"]) == "place" else FIND
            text = fill(frames[tier], a=word_slot(a), b=word_slot(b), pa=word_slot(pa), pb=word_slot(pb))
            target, place = (a, pa) if rng.random() < 0.5 else (b, pb)
            opts = _word_options(place, positions, rng, n_opts)
            questions.append({"type": "sound_find", "lines": [_line(sp, text, stage)], "ask_item": target.id,
                              "options": [{"word_id": o.id, "zh": o.simplified} for o in opts],
                              "item_id": next(i for i, o in enumerate(opts) if o.id == place.id), "focus_id": place.id,
                              "answer_kind": "word"})
        elif kind == "respond" and exchanges:
            ex = exchanges.pop()
            replies = [ex["reply"]] + [{"zh": w[0], "py": w[1]} for w in ex["wrong"]]
            replies = replies[:n_opts]
            rng.shuffle(replies)
            focus = sent.vocab_rows(db, ex["focus"]).get(ex["focus"])
            npc_line = _line("npc", {"zh": ex["npc"]["zh"], "py": ex["npc"]["py"]}, stage, label=scene["npc"]["zh"])
            questions.append({"type": "sound_respond", "lines": [npc_line],
                              "options": [{"zh": r["zh"], "py": r.get("py") or ""} for r in replies],
                              "item_id": next(i for i, r in enumerate(replies) if r["zh"] == ex["reply"]["zh"]),
                              "focus_id": focus.id if focus else None, "answer_kind": "reply",
                              "say": {"zh": ex["reply"]["zh"], "keywords": [t["text"] for t in sent.segment(db, ex["reply"]["zh"]) if t["kind"] == "word"]}})
        elif kind == "conversation":
            w = next_item()
            ck = CONV_KIND.get(E["items"], "place")
            frames = CONVERSATION[ck][tier]
            unit = CONV_UNIT[ck]
            k = rng.randint(2, 5) if ck != "place" else rng.randint(3, 99)
            n = number(k, *unit)
            price = _value("money", rng, tier)
            a = fill(frames[0], item=word_slot(w), n=n, price=price)
            b = fill(frames[1], item=word_slot(w), n=n, price=price)
            ask_count = ck == "place" or rng.random() < 0.5
            answer = {**n, "label": str(k)} if ask_count else price
            vals = _values_like(answer, "number" if ask_count else "money", rng, tier)[:n_opts]
            if all(v["label"] != answer["label"] for v in vals):
                vals[-1] = answer
                rng.shuffle(vals)
            ask = ("bus" if ck == "place" else "count") if ask_count else "price"
            questions.append({"type": "sound_conversation", "ask": ask, "ask_item": w.id,
                              "lines": [_line(asker, a, stage), _line(answerer, b, stage)],
                              "options": [{"label": v["label"], "zh": v["zh"]} for v in vals],
                              "item_id": next(i for i, v in enumerate(vals) if v["label"] == answer["label"]),
                              "focus_id": w.id, "answer_kind": "value"})
        elif kind == "memory":
            chatter = [next_item() for _ in range(2 if tier == "beginner" else 3)]
            # Different people, different ways of saying it (this tier's
            # frame and the simpler ones below it).
            frames = [IDENTIFY[IDENTIFY_KIND.get(E["items"], E["items"])][t] for t in reversed(TIER_ORDER[: TIER_ORDER.index(tier) + 1])]
            lines = [_line(talkers[i % len(talkers)], fill(frames[i % len(frames)], item=word_slot(w)), stage)
                     for i, w in enumerate(chatter)]
            ask_i = rng.randrange(len(chatter))
            target = chatter[ask_i]
            opts = _word_options(target, items, rng, n_opts)
            questions.append({"type": "sound_memory", "lines": lines, "ask_speaker": lines[ask_i]["speaker"],
                              "ask_order": ask_i,
                              "options": [{"word_id": o.id, "zh": o.simplified} for o in opts],
                              "item_id": next(i for i, o in enumerate(opts) if o.id == target.id), "focus_id": target.id,
                              "answer_kind": "word"})
    for q in questions:
        q["item_type"] = "sound"
        q["option_ids"] = list(range(len(q["options"])))
        q["tier"] = tier
        q["stage"] = stage
    questions[0]["ctx"] = {"kind": "sound", "env": env, "icon": E["icon"], "zh": E["zh"], "stage": stage,
                           "rate": STAGE_RATE[stage], "tier": tier, "speakers": list(speakers)}
    return questions


# --------------------------------------------------------------------------- rendering

def render(db: Session, q: dict, answered: bool, locale: str) -> tuple[dict, list[dict]]:
    ids = [o["word_id"] for o in q["options"] if o.get("word_id")]
    m = ss.meanings(db, [x for x in (q.get("ask_item"), q.get("focus_id")) if x], locale)
    om = ss.meanings(db, ids, locale, uniform=True)
    if q["answer_kind"] == "word":
        options = [{"id": i, "label": om.get(o["word_id"], o["zh"])} for i, o in enumerate(q["options"])]
    elif q["answer_kind"] == "reply":
        options = [{"id": i, "label": o["zh"], "pinyin": (o.get("py") or None) if q.get("tier") == "beginner" else None}
                   for i, o in enumerate(q["options"])]
    else:
        options = [{"id": i, "label": o["label"]} for i, o in enumerate(q["options"])]
    lines = [{"speaker": l["speaker"], "speaker_zh": l["speaker_zh"], "pitch": l["pitch"], "rate": l["rate"],
              "speak": l["zh"], "text": l["zh"] if answered else None,
              "pinyin": l["py"] if answered else None, "fallback": l["py"]} for l in q["lines"]]
    ask = {"kind": q["type"], "info": q.get("info"), "ask": q.get("ask"),
           "item": m.get(q.get("ask_item"), "") if q.get("ask_item") else "",
           "speaker": q.get("ask_speaker"), "order": (q.get("ask_order") or 0) + 1}
    return {"lines": lines, "ask": ask}, options


def card(db: Session, q: dict, locale: str) -> dict:
    o = q["options"][q["item_id"]]
    if q["answer_kind"] == "word":
        meaning = ss.meanings(db, [o["word_id"]], locale).get(o["word_id"], "")
        answer = o["zh"]
    elif q["answer_kind"] == "reply":
        meaning, answer = "", o["zh"]
    else:
        meaning, answer = o["label"], o["zh"]
    text = "".join(l["zh"] for l in q["lines"])
    return {"hanzi": " / ".join(l["zh"] for l in q["lines"]), "pinyin": " / ".join(l["py"] for l in q["lines"]),
            "meaning": meaning, "answer_zh": answer, "gloss": ss.gloss(db, text, locale)}
