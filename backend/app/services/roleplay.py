"""AI roleplay: a real-life scenario played in the learner's own words.

The learner talks -- typed, or spoken through the browser's recognizer --
with an AI partner (a waiter, a shop assistant, a taxi driver...) inside a
hand-written scenario: its setting, the partner's role, an opening line,
the learner's goals and key words are authored here, at a minimum HSK
level, the way Duolingo Max's Roleplay scenarios are written by people and
only the conversation is generated. Each learner message is answered in
character AND corrected: the model returns, as JSON, its reply (with pinyin
and a translation the learner can reveal), whether the message was right,
a minimally corrected version and a short explanation in the learner's
language, the goals reached, and useful words. All of it is validated
before anything is stored or shown.

What it changes, from real turns only: a corrected message goes to the
mistake notebook; Learning DNA (grammar, vocabulary) moves by the verdict;
XP for each message accepted and for a finished scenario; activity. Words
the partner used that are curriculum words can be saved to review (the
existing POST /api/vocab/{id}/track). The end summary counts the real
turns, corrections and goals, lists every correction, and adds the
model's short feedback when it is available.

No AI, no roleplay: a conversation partner can't be faked with canned
lines. Without a configured provider (or past the learner's hourly AI
budget) the scenarios say so and point to the scripted Real Chinese
scenes; a call that fails mid-conversation stores nothing and asks the
learner to send again. Hints fall back to the scenario's own goals and key
words.
"""

from __future__ import annotations

import json
import re
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app import models
from app.services import ai_budget, ai_client
from app.services.activity import log_activity
from app.services.dna import bump_skill
from app.services.gamification import ensure_user_skills, record_mistake, user_rank
from app.services.localization import load_translations, tr

MAX_LEARNER_TURNS = 12
MAX_MESSAGE = 200
XP_PER_GOOD_TURN = 3
XP_FINISH = 10
FINISH_MIN_TURNS = 3  # a scenario counts as played after this many messages
LANG = {"en": "English", "ru": "Russian", "tg": "Tajik (Cyrillic script only)", "zh": "very simple Simplified Chinese"}
KINDS = ("grammar", "word", "natural", "meaning", "language")
_CJK = re.compile(r"[㐀-鿿]")


class RoleplayError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


# Hand-written scenarios. `setting` and `role` brief the model (English
# instructions, Chinese role); `opening` is the partner's first line, with
# its pinyin and translations; `words` are curriculum words the scenario is
# about (their pinyin and meanings are read from the curriculum).
SCENARIOS: dict[str, dict] = {
    "restaurant": {
        "level": 1, "icon": "restaurant", "role": "服务员",
        "setting": "a small Chinese restaurant; you are the waiter taking the learner's order",
        "title": L("At a restaurant", "В ресторане", "Дар тарабхона", "在饭馆"),
        "goals": [L("Order a dish", "Закажите блюдо", "Таом фармоиш диҳед", "点一个菜"),
                  L("Order a drink", "Закажите напиток", "Нӯшокӣ фармоиш диҳед", "点一杯喝的"),
                  L("Ask how much it costs and pay", "Спросите, сколько стоит, и заплатите",
                    "Пурсед, ки чанд пул аст, ва пардохт кунед", "问多少钱，然后付钱")],
        "opening": {"zh": "你好！欢迎光临。你想吃什么？", "py": "Nǐ hǎo! Huānyíng guānglín. Nǐ xiǎng chī shénme?",
                    "tr": L("Hello! Welcome. What would you like to eat?", "Здравствуйте! Добро пожаловать. Что вы хотите съесть?",
                            "Салом! Хуш омадед. Шумо чӣ хӯрдан мехоҳед?", "")},
        "words": ["菜", "米饭", "茶", "水", "多少", "钱", "好吃"],
    },
    "shop": {
        "level": 1, "icon": "shop", "role": "售货员",
        "setting": "a clothes and gifts shop; you are the shop assistant",
        "title": L("In a shop", "В магазине", "Дар мағоза", "在商店"),
        "goals": [L("Say what you want to buy", "Скажите, что хотите купить", "Гӯед, ки чӣ харидан мехоҳед", "说你想买什么"),
                  L("Ask the price", "Спросите цену", "Нархро пурсед", "问价钱"),
                  L("Ask for a cheaper one, then buy", "Попросите подешевле и купите", "Арзонтарашро пурсед ва харед",
                    "问有没有便宜一点的，然后买")],
        "opening": {"zh": "你好，你要买什么？", "py": "Nǐ hǎo, nǐ yào mǎi shénme?",
                    "tr": L("Hi, what would you like to buy?", "Здравствуйте, что вы хотите купить?",
                            "Салом, шумо чӣ харидан мехоҳед?", "")},
        "words": ["买", "衣服", "多少", "钱", "贵", "便宜", "块"],
    },
    "taxi": {
        "level": 1, "icon": "street", "role": "出租车司机",
        "setting": "a taxi in a Chinese city; you are the driver",
        "title": L("Taking a taxi", "В такси", "Дар такси", "坐出租车"),
        "goals": [L("Say where you are going", "Скажите, куда вам нужно", "Гӯед, ки ба куҷо меравед", "说你去哪儿"),
                  L("Ask how long it takes", "Спросите, сколько ехать", "Пурсед, ки чанд вақт мегирад", "问要多长时间"),
                  L("Pay and say thank you", "Заплатите и поблагодарите", "Пардохт кунед ва ташаккур гӯед", "付钱，说谢谢")],
        "opening": {"zh": "你好！你去哪儿？", "py": "Nǐ hǎo! Nǐ qù nǎr?",
                    "tr": L("Hello! Where are you going?", "Здравствуйте! Куда едем?", "Салом! Ба куҷо меравед?", "")},
        "words": ["去", "哪儿", "火车站", "学校", "多长时间", "钱", "谢谢"],
    },
    "friend": {
        "level": 1, "icon": "university", "role": "新同学小明",
        "setting": "the first day of class; you are Xiao Ming, a friendly new classmate",
        "title": L("Meeting a classmate", "Знакомство с одноклассником", "Шиносоӣ бо ҳамсинф", "认识新同学"),
        "goals": [L("Introduce yourself", "Представьтесь", "Худро муаррифӣ кунед", "介绍你自己"),
                  L("Say where you are from", "Скажите, откуда вы", "Гӯед, ки аз куҷо ҳастед", "说你是哪国人"),
                  L("Talk about something you like", "Расскажите, что вам нравится", "Дар бораи чизе, ки дӯст медоред, гап занед",
                    "说说你喜欢什么")],
        "opening": {"zh": "你好！我叫小明。你叫什么名字？", "py": "Nǐ hǎo! Wǒ jiào Xiǎo Míng. Nǐ jiào shénme míngzi?",
                    "tr": L("Hi! I'm Xiao Ming. What's your name?", "Привет! Меня зовут Сяо Мин. Как тебя зовут?",
                            "Салом! Номи ман Сяо Мин. Номи ту чист?", "")},
        "words": ["叫", "名字", "国", "人", "喜欢", "学习", "朋友"],
    },
    "hotel": {
        "level": 2, "icon": "hotel", "role": "酒店前台",
        "setting": "a hotel reception desk; you are the receptionist checking the learner in",
        "title": L("At a hotel", "В отеле", "Дар меҳмонхона", "在酒店"),
        "goals": [L("Check in or ask for a room", "Заселитесь или попросите номер", "Ҷойгир шавед ё ҳуҷра пурсед", "办入住或者要一个房间"),
                  L("Ask when breakfast is", "Спросите, когда завтрак", "Пурсед, ки наҳорӣ кай аст", "问早饭几点"),
                  L("Ask for the Wi-Fi password", "Спросите пароль от Wi-Fi", "Пароли Wi-Fi-ро пурсед", "问无线网密码")],
        "opening": {"zh": "您好，欢迎来到我们酒店。您有预订吗？", "py": "Nín hǎo, huānyíng láidào wǒmen jiǔdiàn. Nín yǒu yùdìng ma?",
                    "tr": L("Hello, welcome to our hotel. Do you have a reservation?",
                            "Здравствуйте, добро пожаловать в наш отель. У вас есть бронь?",
                            "Салом, ба меҳмонхонаи мо хуш омадед. Шумо брон доред?", "")},
        "words": ["房间", "晚上", "早饭", "几点", "护照", "钥匙"],
    },
    "directions": {
        "level": 2, "icon": "street", "role": "路人",
        "setting": "a busy street; you are a local passer-by the learner asks for directions",
        "title": L("Asking the way", "Как пройти?", "Роҳпурсӣ", "问路"),
        "goals": [L("Ask where a place is", "Спросите, где находится место", "Пурсед, ки ҷое дар куҷост", "问一个地方在哪儿"),
                  L("Ask if it is far", "Спросите, далеко ли это", "Пурсед, ки дур аст ё не", "问远不远"),
                  L("Repeat the way and say thank you", "Повторите дорогу и поблагодарите",
                    "Роҳро такрор кунед ва ташаккур гӯед", "重复一下怎么走，然后说谢谢")],
        "opening": {"zh": "你好，你需要帮忙吗？", "py": "Nǐ hǎo, nǐ xūyào bāngmáng ma?",
                    "tr": L("Hi, do you need help?", "Здравствуйте, вам помочь?", "Салом, ба шумо ёрӣ лозим аст?", "")},
        "words": ["在", "哪儿", "远", "近", "左边", "右边", "走"],
    },
    "pharmacy": {
        "level": 2, "icon": "hospital", "role": "药店店员",
        "setting": "a pharmacy; you are the pharmacist asking what is wrong",
        "title": L("At a pharmacy", "В аптеке", "Дар дорухона", "在药店"),
        "goals": [L("Say what hurts or how you feel", "Скажите, что болит или как вы себя чувствуете",
                    "Гӯед, ки чӣ дард мекунад ё худро чӣ гуна ҳис мекунед", "说哪儿不舒服"),
                  L("Ask how to take the medicine", "Спросите, как принимать лекарство", "Пурсед, ки доруро чӣ тавр бояд хӯрд",
                    "问药怎么吃"),
                  L("Ask the price and pay", "Спросите цену и заплатите", "Нархро пурсед ва пардохт кунед", "问多少钱，然后付钱")],
        "opening": {"zh": "你好，哪儿不舒服？", "py": "Nǐ hǎo, nǎr bù shūfu?",
                    "tr": L("Hello, what's bothering you?", "Здравствуйте, что вас беспокоит?",
                            "Салом, шумо аз чӣ шикоят доред?", "")},
        "words": ["药", "头", "疼", "舒服", "一天", "次", "吃"],
    },
    "bank": {
        "level": 3, "icon": "bank", "role": "银行职员",
        "setting": "a bank counter; you are the clerk helping the learner",
        "title": L("At a bank", "В банке", "Дар бонк", "在银行"),
        "goals": [L("Say what you need (open an account or change money)",
                    "Скажите, что вам нужно (открыть счёт или обменять деньги)",
                    "Гӯед, ки ба шумо чӣ лозим аст (ҳисоб кушодан ё пул иваз кардан)", "说你要办什么（开户或者换钱）"),
                  L("Give the information they ask for", "Ответьте на вопросы сотрудника", "Ба саволҳои корманд ҷавоб диҳед",
                    "回答职员的问题"),
                  L("Ask about the fee", "Спросите о комиссии", "Дар бораи ҳаққи хизмат пурсед", "问手续费")],
        "opening": {"zh": "您好，请问您要办什么业务？", "py": "Nín hǎo, qǐngwèn nín yào bàn shénme yèwù?",
                    "tr": L("Hello, how can I help you today?", "Здравствуйте, чем могу помочь?",
                            "Салом, ба шумо чӣ хизмат лозим аст?", "")},
        "words": ["银行", "换", "钱", "护照", "需要", "填"],
    },
}


def ai_available() -> bool:
    return ai_client._active_provider() == "gemini"


def _level(db: Session, user: models.User) -> int:
    level, _ = user_rank(db, user)
    return max(1, min(level, 7))


def _words(db: Session, slug: str, locale: str) -> list[dict]:
    """The scenario's key words as the curriculum has them (pinyin, the
    meaning in the learner's language, an id that can be saved to review)."""
    wanted = SCENARIOS[slug]["words"]
    rows = db.query(models.VocabularyWord).filter(models.VocabularyWord.simplified.in_(wanted)).order_by(
        models.VocabularyWord.hsk_level_id, models.VocabularyWord.id).all()
    best: dict[str, models.VocabularyWord] = {}
    for r in rows:
        best.setdefault(r.simplified, r)
    return _cards(db, [best[w] for w in wanted if w in best], locale)


def _cards(db: Session, rows: list, locale: str) -> list[dict]:
    trs = load_translations(db, "vocab_word", [str(r.id) for r in rows], locale)
    out = []
    for r in rows:
        meaning = tr(trs, r.id, "meanings", r.meanings)
        if locale == "zh" and (meaning or "").strip() == r.simplified:
            meaning = ""
        out.append({"word_id": r.id, "zh": r.simplified, "pinyin": r.pinyin, "meaning": meaning or ""})
    return out


def scenario_list(db: Session, user: models.User, locale: str) -> dict:
    level = _level(db, user)
    loc = locale if locale in LANG else "en"
    played = {}
    for s in db.query(models.RoleplaySession).filter_by(user_id=user.id, status="finished"):
        played[s.scenario] = played.get(s.scenario, 0) + 1
    return {
        "ai_available": ai_available(),
        "level": level,
        "scenarios": [
            # `role` is the partner's Chinese name (服务员, 新同学小明): the hub
            # shows who the learner will be talking to. Chinese, never translated.
            {"slug": slug, "icon": s["icon"], "title": s["title"][loc], "level": s["level"], "role": s["role"],
             "unlocked": level >= s["level"], "goals": [g[loc] for g in s["goals"]], "played": played.get(slug, 0)}
            for slug, s in SCENARIOS.items()
        ],
    }


def render(db: Session, session: models.RoleplaySession, locale: str) -> dict:
    s = SCENARIOS.get(session.scenario)
    loc = locale if locale in LANG else "en"
    turns = []
    for t in session.turns or []:
        if t["role"] == "partner":
            turns.append({"role": "partner", "zh": t["zh"], "pinyin": t.get("py") or "",
                          # A Chinese screen has nothing to translate the line into.
                          "translation": "" if loc == "zh" else (t.get("tr") or {}).get(loc) or "",
                          "words": t.get("words") or []})
        else:
            turns.append({"role": "learner", "text": t["text"], "feedback": t.get("feedback")})
    learner_turns = sum(1 for t in session.turns or [] if t["role"] == "learner")
    return {
        "id": session.id,
        "scenario": session.scenario,
        "title": s["title"][loc] if s else session.scenario,
        "role": s["role"] if s else "",
        "icon": s["icon"] if s else "street",
        "level": session.hsk_level,
        "goals": [{"text": g[loc], "met": i in (session.goals_met or [])} for i, g in enumerate(s["goals"])] if s else [],
        "words": _words(db, session.scenario, loc) if s else [],
        "turns": turns,
        "status": session.status,
        "learner_turns": learner_turns,
        "turns_left": max(0, MAX_LEARNER_TURNS - learner_turns),
        "summary": session.summary,
        "ai_available": ai_available(),
    }


def start(db: Session, user: models.User, slug: str, locale: str) -> models.RoleplaySession:
    s = SCENARIOS.get(slug)
    if s is None:
        raise RoleplayError(404, "Scenario not found")
    level = _level(db, user)
    if level < s["level"]:
        raise RoleplayError(403, f"This scenario opens at HSK {s['level']}")
    if not ai_available():
        raise RoleplayError(503, "AI conversations are not available on this server right now")
    o = s["opening"]
    session = models.RoleplaySession(
        user_id=user.id, scenario=slug, hsk_level=level, goals_met=[], status="active",
        turns=[{"role": "partner", "zh": o["zh"], "py": o["py"], "tr": o["tr"], "words": []}],
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


# --------------------------------------------------------------------------- the model

def _max_chars(level: int) -> int:
    return 20 if level <= 2 else 35 if level <= 4 else 60


def _transcript(session: models.RoleplaySession) -> str:
    lines = []
    for t in session.turns or []:
        lines.append(f"{'PARTNER' if t['role'] == 'partner' else 'LEARNER'}: {t['zh'] if t['role'] == 'partner' else t['text']}")
    return "\n".join(lines)


def _system(session: models.RoleplaySession, locale: str) -> str:
    s = SCENARIOS[session.scenario]
    goals = "; ".join(f"{i}: {g['en']}" for i, g in enumerate(s["goals"]))
    lang = LANG.get(locale, "English")
    level = session.hsk_level
    return (
        f"You are role-playing {s['role']} in this scene: {s['setting']}. The learner is practising Mandarin "
        f"at HSK {level}. The learner's goals: {goals}.\n"
        "Rules for your reply (reply.zh): Simplified Chinese ONLY, in character, a natural answer to the learner's "
        f"LAST message that moves the scene towards the goals; use mostly HSK 1-{level} words; at most "
        f"{_max_chars(level)} Chinese characters; one or two short sentences; usually end with a question that "
        "invites the learner to continue. Never break character there, never add pinyin or another language "
        "to reply.zh.\n"
        "Also judge the learner's LAST message as a teacher. feedback.ok is true only when it is correct Chinese: "
        "flag real errors such as a wrong measure word (一个米饭 -> 一碗米饭), wrong word order, a wrong or missing "
        "word, or a sentence a Chinese speaker would not say. Do not flag punctuation, a missing 请, or a short "
        "answer that is natural in conversation (多少钱？ is fine). Otherwise give "
        "feedback.corrected: the learner's sentence minimally corrected in Simplified Chinese, and "
        f"feedback.explanation: one or two short, kind sentences in {lang} saying what was wrong and why. "
        f"feedback.kind is one of {', '.join(KINDS)} ('language' when they wrote in another language or in "
        "pinyin: then corrected is how to say it in Chinese). Pinyin with tone marks is fine as learner input.\n"
        f"reply.pinyin: the pinyin of reply.zh with tone marks. reply.translation: reply.zh translated into {lang}"
        f"{' (empty string)' if locale == 'zh' else ''}.\n"
        "words: up to 3 words from your reply or the correction worth learning (zh, pinyin, meaning in "
        f"{lang}).\ngoals_met: indices of goals the learner has achieved so far in the whole conversation.\n"
        "Return JSON only: {\"reply\": {\"zh\": str, \"pinyin\": str, \"translation\": str}, \"feedback\": "
        "{\"ok\": bool, \"corrected\": str, \"explanation\": str, \"kind\": str}, \"words\": [{\"zh\": str, "
        "\"pinyin\": str, \"meaning\": str}], \"goals_met\": [int]}"
    )


def _call(messages: list[dict], max_tokens: int = 700) -> dict:
    try:
        return json.loads(ai_client._gemini_chat(messages, max_tokens=max_tokens, temperature=0.7, json_mode=True))
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise RoleplayError(503, "Your conversation partner didn't answer. Send your message again in a moment.") from exc


def _text(v, limit: int) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:limit]


def _validate_turn(data: dict, goal_count: int) -> dict:
    """The model's JSON, checked field by field; anything unusable is
    refused (as a failed call), never shown or stored."""
    if not isinstance(data, dict):
        raise ValueError("not an object")
    reply = data.get("reply") or {}
    zh = _text(reply.get("zh"), 160)
    if not _CJK.search(zh) or re.search(r"[A-Za-zА-Яа-яЁёӢӣҚқҒғҲҳҶҷӮӯ]", zh):
        raise ValueError("reply is not Chinese")
    fb = data.get("feedback") or {}
    ok = bool(fb.get("ok"))
    corrected = _text(fb.get("corrected"), 160)
    explanation = _text(fb.get("explanation"), 400)
    kind = fb.get("kind") if fb.get("kind") in KINDS else "grammar"
    if not ok and not (_CJK.search(corrected) and explanation):
        # A "wrong" verdict with nothing to learn from would only discourage.
        ok, corrected, explanation = True, "", ""
    words = []
    for w in (data.get("words") or [])[:3]:
        if isinstance(w, dict):
            wz = _text(w.get("zh"), 8)
            if wz and all(_CJK.match(c) for c in wz):
                words.append({"zh": wz, "pinyin": _text(w.get("pinyin"), 40), "meaning": _text(w.get("meaning"), 80)})
    goals = sorted({int(g) for g in (data.get("goals_met") or []) if isinstance(g, (int, float)) and 0 <= int(g) < goal_count})
    return {"zh": zh, "py": _text(reply.get("pinyin"), 240), "tr_text": _text(reply.get("translation"), 300),
            "ok": ok, "corrected": corrected if not ok else "", "explanation": explanation if not ok else "",
            "kind": kind if not ok else None, "words": words, "goals": goals}


_LATIN = re.compile(r"[A-Za-z]")


def _localized(text: str, locale: str, translation: bool = False) -> str:
    """Model text in the learner's language, cleaned the way the assistant's
    is: Tajik words that came back half in Latin letters are repaired
    (ai_client._tg_clean_mixed_script). A Russian or Tajik TRANSLATION that
    still contains Latin letters came back in another script ("yak kosasa
    guruch" -- seen in a live test) and is dropped: no translation is better
    than a wrong one. Explanations may quote pinyin, so they keep Latin."""
    if locale == "tg":
        text = ai_client._tg_clean_mixed_script(text)
    if translation and locale in ("ru", "tg") and _LATIN.search(text):
        return ""
    return text


def _link_words(db: Session, words: list[dict], locale: str) -> list[dict]:
    """Model-suggested words that are curriculum words get the curriculum's
    own pinyin and meaning, and an id to save them to review; others keep
    the model's gloss and can't be saved (there is nothing to review)."""
    if not words:
        return []
    rows = db.query(models.VocabularyWord).filter(models.VocabularyWord.simplified.in_([w["zh"] for w in words])).order_by(
        models.VocabularyWord.hsk_level_id).all()
    best: dict[str, models.VocabularyWord] = {}
    for r in rows:
        best.setdefault(r.simplified, r)
    cards = {c["zh"]: c for c in _cards(db, list(best.values()), locale)}
    return [cards.get(w["zh"]) or {"word_id": None, **w} for w in words]


def _own(db: Session, user: models.User, session_id: int) -> models.RoleplaySession:
    s = db.get(models.RoleplaySession, session_id)
    if s is None or s.user_id != user.id:
        raise RoleplayError(404, "Conversation not found")
    return s


def turn(db: Session, user: models.User, session: models.RoleplaySession, text: str, locale: str) -> dict:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if not text:
        raise RoleplayError(422, "Write something to say")
    if len(text) > MAX_MESSAGE:
        raise RoleplayError(422, f"Keep each message under {MAX_MESSAGE} characters")
    if session.status != "active":
        raise RoleplayError(409, "This conversation is finished")
    learner_turns = sum(1 for t in session.turns or [] if t["role"] == "learner")
    if learner_turns >= MAX_LEARNER_TURNS:
        raise RoleplayError(409, "This conversation is complete -- finish it to see your summary")
    if not ai_available() or not ai_budget.spend(user.id):
        raise RoleplayError(503, "AI conversations are not available right now. Try again later.")

    goal_count = len(SCENARIOS[session.scenario]["goals"])
    messages = [{"role": "system", "content": _system(session, locale)},
                {"role": "user", "content": f"Conversation so far:\n{_transcript(session)}\n\nLEARNER'S NEW MESSAGE: {text}"}]
    try:
        v = _validate_turn(_call(messages), goal_count)
    except ValueError as exc:
        raise RoleplayError(503, "Your conversation partner didn't answer. Send your message again in a moment.") from exc
    v["tr_text"] = _localized(v["tr_text"], locale, translation=True)
    v["explanation"] = _localized(v["explanation"], locale)
    for w in v["words"]:
        w["meaning"] = _localized(w["meaning"], locale, translation=True)

    feedback = None if v["ok"] else {"corrected": v["corrected"], "explanation": v["explanation"], "kind": v["kind"]}
    turns = list(session.turns or [])  # reassign so the JSON column is marked dirty
    turns.append({"role": "learner", "text": text, "feedback": feedback, "at": datetime.utcnow().isoformat()})
    # The translation exists only in the language it was asked in; another
    # UI language shows none rather than the wrong one.
    turns.append({"role": "partner", "zh": v["zh"], "py": v["py"],
                  "tr": {locale: v["tr_text"]} if v["tr_text"] and locale != "zh" else {},
                  "words": _link_words(db, v["words"], locale)})
    session.turns = turns
    session.goals_met = sorted(set(session.goals_met or []) | set(v["goals"]))

    ensure_user_skills(db, user)
    bump_skill(user, "grammar", 1.0 if v["ok"] else -0.3)
    bump_skill(user, "vocabulary", 0.5 if v["ok"] else 0.0)
    if v["ok"]:
        user.total_xp += XP_PER_GOOD_TURN
    elif v["kind"] != "language":
        record_mistake(db, user, "grammar" if v["kind"] in ("grammar", "natural") else "word", v["corrected"],
                       question_text=SCENARIOS[session.scenario]["title"]["en"], answer_given=text,
                       correct_answer=v["corrected"])
    log_activity(db, user, "roleplay_turn")
    db.commit()
    return render(db, session, locale)


def hint(db: Session, user: models.User, session: models.RoleplaySession, locale: str) -> dict:
    """Something the learner could say next: from the model when it can,
    otherwise the next unmet goal and the scenario's key words."""
    s = SCENARIOS[session.scenario]
    loc = locale if locale in LANG else "en"
    pending = [g[loc] for i, g in enumerate(s["goals"]) if i not in (session.goals_met or [])]
    out = {"goal": pending[0] if pending else None, "words": _words(db, session.scenario, loc), "line": None}
    if session.status == "active" and ai_available() and ai_budget.spend(user.id):
        lang = LANG.get(loc, "English")
        messages = [
            {"role": "system", "content": (
                f"You help a Mandarin learner at HSK {session.hsk_level} in this roleplay: {s['setting']}. Suggest ONE "
                f"short thing the learner could say next (at most {_max_chars(session.hsk_level)} characters, mostly "
                f"HSK 1-{session.hsk_level} words) that moves towards their next goal: {(pending or ['finish politely'])[0]}. "
                f"Return JSON only: {{\"zh\": str, \"pinyin\": str, \"translation\": str}} (translation in {lang}"
                f"{', empty string' if loc == 'zh' else ''}).")},
            {"role": "user", "content": _transcript(session)},
        ]
        try:
            data = _call(messages, max_tokens=200)
            zh = _text(data.get("zh"), 80)
            if _CJK.search(zh):
                out["line"] = {"zh": zh, "pinyin": _text(data.get("pinyin"), 160),
                               "translation": "" if loc == "zh" else _localized(
                                   _text(data.get("translation"), 200), loc, translation=True)}
        except (RoleplayError, AttributeError):
            pass  # the goal and the key words are still a real hint
    return out


def finish(db: Session, user: models.User, session: models.RoleplaySession, locale: str) -> dict:
    """Ends the conversation. The summary is built from the stored turns --
    messages sent, corrections, goals reached -- and adds the model's
    feedback on the whole conversation when it is available."""
    if session.status == "finished":
        return render(db, session, locale)
    learner = [t for t in session.turns or [] if t["role"] == "learner"]
    if not learner:
        raise RoleplayError(422, "Say something before finishing")
    loc = locale if locale in LANG else "en"
    corrections = [{"text": t["text"], "corrected": t["feedback"]["corrected"], "explanation": t["feedback"]["explanation"]}
                   for t in learner if t.get("feedback")]
    s = SCENARIOS[session.scenario]
    summary = {
        "messages": len(learner),
        "accepted": len(learner) - len(corrections),
        "goals_met": len(session.goals_met or []),
        "goals_total": len(s["goals"]),
        "corrections": corrections,
        "feedback": None,
        "xp": 0,
    }
    if ai_available() and ai_budget.spend(user.id):
        lang = LANG.get(loc, "English")
        messages = [
            {"role": "system", "content": (
                f"You are a kind Mandarin teacher. Read this roleplay ({s['setting']}) between a learner at HSK "
                f"{session.hsk_level} and their partner. In {lang}, write: summary (2 sentences on how the learner "
                "did, mentioning the accuracy and how complex their sentences were), strengths (up to 2 short "
                "points), next (up to 2 short, concrete tips for next time). Base everything ONLY on the "
                "learner's actual messages. Return JSON only: {\"summary\": str, \"strengths\": [str], \"next\": [str]}")},
            {"role": "user", "content": _transcript(session)},
        ]
        try:
            data = _call(messages, max_tokens=400)
            text = _localized(_text(data.get("summary"), 500), loc)
            if text:
                summary["feedback"] = {
                    "summary": text,
                    "strengths": [_localized(_text(x, 200), loc) for x in (data.get("strengths") or [])[:2] if _text(x, 200)],
                    "next": [_localized(_text(x, 200), loc) for x in (data.get("next") or [])[:2] if _text(x, 200)],
                }
        except (RoleplayError, AttributeError):
            pass  # the counted summary stands on its own
    if len(learner) >= FINISH_MIN_TURNS:
        user.total_xp += XP_FINISH
        summary["xp"] = XP_FINISH
    session.summary = summary
    session.status = "finished"
    session.finished_at = datetime.utcnow()
    log_activity(db, user, "roleplay_finish")
    db.commit()
    return render(db, session, locale)
