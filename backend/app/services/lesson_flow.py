"""A lesson as a guided sequence: Learn -> Listen -> Build -> Recall -> Apply,
then the lesson's own check (practice source "lesson", >= 70%) that
completes it.

A lesson used to be its text on one page and one round of word questions:
a beginner could read 很高兴认识你 but was never asked to hear it, put it
together, recall it or use it. Everything here is built from the lesson's
OWN material -- nothing is invented:

  phrases   the lesson text's lines "中文 (pinyin) = meaning" (also
            "中文 pinyin = meaning" and "中文。 = meaning"), with the meaning
            in every language the lesson's translations carry; a "— Answer:
            中文" after a line is a real reply (你好吗？ -> 我很好，谢谢。).
            A grammar lesson's example sentences come with the grammar point
            they illustrate and its pattern, but without a translation: they
            are explained word by word from the curriculum's own meanings.
  pinyin    the lesson's own; else joined from the curriculum words' pinyin
            -- only when no piece is a character whose reading depends on
            context (POLYPHONES), so no reading is guessed.
  words     practice.lesson_items (the words the lesson's practice uses).
  grammar   the same, with the localized title, pattern and explanation.

Stages (each a server-graded round, practice source "lesson_step", the
lesson and stage in the round's ctx -- never session.lesson_id, which is
what completes a lesson):

  listen  heard tones of the lesson's characters, its words by ear, and its
          phrases by ear
  build   fill the missing word; arrange the pieces into the phrase -- the
          first with pinyin and word meanings on the pieces, then fewer
          hints (how many depends on the learner's level, `hints`)
  recall  a word typed from memory, a word's meaning, the phrase for a
          meaning
  apply   answer what someone says (the lesson's real replies), say what a
          situation needs, and build a phrase with no hints at all

Wrong answers say what differed -- the word picked and its meaning, the
phrase heard, the piece out of place when a rule can be read off the two
orders (吗 at the end, 不 before the verb ...) -- and nothing more than the
stored question shows (see explain()).

Grading goes through practice.answer_question like every round: the
phrase's lesson word ("focus") moves in SRS and a miss goes to the mistake
notebook (practice._record_virtual). A stage's record is read back from the
learner's completed rounds -- no table of its own.
"""

from __future__ import annotations

import random
import re

from sqlalchemy.orm import Session

from app import models
from app.services.localization import load_translations, tr

STAGES = ("listen", "build", "recall", "apply")
PASS = 70.0          # a stage counts as done at this score (percent), like a lesson
MIN_QUESTIONS = 3    # a stage the lesson cannot fill this far is not offered
LOCALES = ("en", "ru", "tg", "zh")

_CJK = r"㐀-鿿"
_PY = "a-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜüA-ZĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙ'’"
# "中文 (pinyin) = meaning" / "中文 pinyin = meaning" / "中文。 = meaning",
# several per line, each meaning running until the next Chinese phrase.
_ENTRY = re.compile(
    rf"([{_CJK}][{_CJK}，。？！、…·]*)\s*(?:[(（]([^)）]*)[)）]|([{_PY}][{_PY} ]*?))?\s*=\s*"
    rf"(.+?)(?=(?:[,，.。;；]\s*[{_CJK}][^=]*=)|$)"
)
_REPLY = re.compile(rf"\s+—\s+[^:：]+[:：]\s*([{_CJK}][{_CJK}，。？！、]*)\s*$")
# A character whose reading depends on the word/sentence it is in: pinyin
# joined from single characters is not trusted when one of these stands alone.
POLYPHONES = set("得长重行觉乐干便调发教数场种只差地着少为")
SUPPLEMENT_UNDER = 4   # fewer usable phrases than this: add the lesson words' own example sentences
MAX_EXAMPLE_CHARS = 14
PRONOUNS = ("我们", "你们", "他们", "她们", "我", "你", "您", "他", "她", "它")
TIME_WORDS = ("今天", "明天", "昨天", "现在", "早上", "晚上", "上午", "下午", "中午", "今年", "明年")


# --------------------------------------------------------------------------- reading the lesson

def _clean_gloss(text: str) -> str:
    return text.strip().rstrip(".。,，;；").strip()


def parse_entries(content: str | None) -> list[dict]:
    """Every "中文 ... = meaning" entry of a lesson text, in order:
    {zh, py, gloss, reply}."""
    out = []
    for raw in (content or "").split("\n"):
        line = raw.strip()
        if "=" not in line or not re.search(f"[{_CJK}]", line):
            continue
        for m in _ENTRY.finditer(line):
            zh, py, py2, gloss = m.group(1), m.group(2), m.group(3), m.group(4)
            reply = None
            r = _REPLY.search(gloss)
            if r:
                reply = r.group(1)
                gloss = gloss[: r.start()]
            out.append({"zh": zh.strip(), "py": (py or py2 or "").strip() or None,
                        "gloss": _clean_gloss(gloss), "reply": reply})
    return out


def parse_examples(content: str | None, topics: list[models.GrammarTopic]) -> list[dict]:
    """A grammar lesson's example sentences: Chinese-only lines (several
    separated by "/") under a grammar point's title, with its pattern."""
    by_title = {t.title: t for t in topics}
    out, topic = [], None
    for raw in (content or "").split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line in by_title:
            topic = by_title[line]
            continue
        if line.lower().startswith("new vocabulary"):
            topic = None
            continue
        if topic is None or "=" in line or "+" in line or re.search(r"[A-Za-z]", line):
            continue
        if topic.pattern and line == topic.pattern.strip():
            continue
        for part in line.split("/"):
            zh = part.strip()
            if len(re.findall(f"[{_CJK}]", zh)) >= 2 and "…" not in zh:
                out.append({"zh": zh, "topic": topic})
    return out


def _word_meaning(w: models.VocabularyWord, trs: dict) -> str:
    label = tr(trs, w.id, "meanings", w.meanings)
    # zh "meanings" mirror the word itself (see practice._labels).
    return w.meanings if (label or "").strip() == w.simplified else (label or "")


def _localized_glosses(db: Session, lesson: models.Lesson) -> dict[str, dict[str, str]]:
    """zh phrase -> {locale: meaning} from the lesson's translated texts."""
    out: dict[str, dict[str, str]] = {}
    for e in parse_entries(lesson.content):
        out.setdefault(e["zh"], {})["en"] = e["gloss"]
    for loc in ("ru", "tg", "zh"):
        trs = load_translations(db, "lesson", [str(lesson.id)], loc)
        text = (trs.get(str(lesson.id)) or {}).get("content")
        for e in parse_entries(text):
            plain = re.sub(f"[^{_CJK}]", "", e["gloss"])
            # The zh "translation" repeats the Chinese: no meaning to show.
            if e["zh"] in out and plain != re.sub(f"[^{_CJK}]", "", e["zh"]):
                out[e["zh"]][loc] = e["gloss"]
    return out


def gloss_for(gloss: dict | None, locale: str) -> str | None:
    """The phrase's meaning in the learner's language; English when the
    lesson has no translation for it (never a Chinese "meaning" that just
    repeats the phrase)."""
    if not gloss:
        return None
    return gloss.get(locale) or gloss.get("en")


def _derived_pinyin(tokens: list[dict]) -> str | None:
    parts = []
    for t in tokens:
        if t["kind"] == "other":
            if parts:
                parts[-1] += t["text"].replace("。", ".").replace("，", ",").replace("？", "?").replace("！", "!")
            continue
        if t["word"] is None or (len(t["text"]) == 1 and t["text"] in POLYPHONES):
            return None
        parts.append(t["word"].pinyin)
    return " ".join(parts) or None


def phrases(db: Session, lesson: models.Lesson) -> list[dict]:
    """The lesson's phrases, each with its words: zh, py, gloss {locale:
    text}, reply, pattern / grammar point, template (a "……" frame), and the
    segmented tokens. A line that is a single curriculum word is a word,
    not a phrase (it is drilled as a word)."""
    from app.services import practice
    from app.services import sentence as sent

    items = practice.lesson_items(db, lesson)
    glosses = _localized_glosses(db, lesson)
    out, seen = [], set()

    def add(zh, py, gloss, reply=None, topic=None):
        key = re.sub(r"\s+", "", zh)
        plain = re.sub(f"[^{_CJK}]", "", key)
        if not plain or plain in seen:
            return
        if len(plain) <= 4 and plain == key and db.query(models.VocabularyWord.id).filter_by(simplified=plain).first():
            return  # a word line ("什么 = what"): it is a word of the lesson
        seen.add(plain)
        template = "…" in key
        tokens = sent.segment(db, key.replace("…", ""))
        out.append({
            "key": len(out), "zh": key, "py": py or _derived_pinyin(tokens), "py_from_lesson": bool(py),
            "gloss": gloss or None, "reply": reply, "template": template, "tokens": tokens,
            "topic_id": topic.id if topic else None, "pattern": topic.pattern if topic else None,
        })

    for e in parse_entries(lesson.content):
        add(e["zh"], e["py"] if e["py"] and "." not in e["py"] else None, glosses.get(e["zh"]), e["reply"])
    for e in parse_examples(lesson.content, items["grammar"]):
        add(e["zh"], None, None, topic=e["topic"])
    # Too few phrases to practise with (a lesson of two lines): the
    # curriculum's own example sentence of each lesson word, with its own
    # pinyin -- real sentences, explained word by word (they carry no
    # translation, so none is shown).
    if sum(1 for p in out if not p["template"]) < SUPPLEMENT_UNDER:
        for w in items["vocab"]:
            ex = sent.clean(w.example or "")
            # A sentence (it ends like one), short enough for the lesson's level.
            if not ex or ex[-1] not in "。！？!?" or len(re.findall(f"[{_CJK}]", ex)) > MAX_EXAMPLE_CHARS:
                continue
            try:
                sent.validate(db, ex)
            except sent.SentenceError:
                continue
            add(ex, w.example_pinyin or None, None)
            if sum(1 for p in out if not p["template"]) >= SUPPLEMENT_UNDER + 2:
                break
    return out


# --------------------------------------------------------------------------- the learner's level

def hints_for(level: int) -> str:
    """How much help the pieces of a phrase come with: a beginner sees pinyin
    and word meanings, HSK 2 the meanings, HSK 3 and above only the phrase's
    meaning (it must be read)."""
    return "full" if level <= 1 else "some" if level == 2 else "none"


def _less(hints: str) -> str:
    return {"full": "some", "some": "none"}.get(hints, "none")


# --------------------------------------------------------------------------- questions

def _usable_phrases(ps: list[dict]) -> list[dict]:
    return [p for p in ps if not p["template"]]


def _chunks(p: dict) -> list[str]:
    """The phrase in movable pieces: one per curriculum word; punctuation and
    a character that is no curriculum word (明 of the name 小明) stay with
    the piece before them, so no piece is a meaningless fragment."""
    out: list[str] = []
    for t in p["tokens"]:
        if out and (t["kind"] == "other" or t["kind"] == "char"):
            out[-1] += t["text"]
        else:
            out.append(t["text"])
    return out


def _focus(p: dict, word_ids: set[int]) -> int | None:
    """The lesson word a phrase question counts for (SRS, mistakes): the
    first word of the phrase the lesson teaches, else its first curriculum word."""
    words = [t["word"] for t in p["tokens"] if t["word"] is not None]
    taught = [w for w in words if w.id in word_ids]
    return (taught or words or [None])[0].id if (taught or words) else None


def _phrase_ref(p: dict) -> dict:
    return {"zh": p["zh"], "py": p["py"], "gloss": p["gloss"], "pattern": p["pattern"], "topic_id": p["topic_id"]}


def _choice(qtype: str, p: dict, options: list[dict], answer: int, rng: random.Random, focus: int | None,
            **extra) -> dict:
    order = list(range(len(options)))
    rng.shuffle(order)
    return {"type": qtype, "item_type": "phrase", "phrase": _phrase_ref(p),
            "options": [options[i] for i in order], "item_id": order.index(answer),
            "option_ids": list(range(len(options))), "focus_id": focus, **extra}


def _distractor_phrases(db: Session, p: dict, pool: list[dict], rng: random.Random, k: int = 2) -> list[dict]:
    """Other phrases of the lesson; else the phrase with one real word swapped
    for another real word of its level (sentence._variants)."""
    from app.services import sentence as sent

    others = [{"zh": o["zh"], "py": o["py"], "gloss": o["gloss"]} for o in pool if o["zh"] != p["zh"]]
    rng.shuffle(others)
    if len(others) < k:
        for v in sent._variants(db, p["tokens"], rng):
            if v != p["zh"] and all(v != o["zh"] for o in others):
                others.append({"zh": v, "py": None, "gloss": None})
    return others[:k]


def _build(p: dict, hints: str, rng: random.Random, focus: int | None) -> dict | None:
    pieces = _chunks(p)
    if len(pieces) < 3:
        return None
    shown = list(range(len(pieces)))
    for _ in range(10):
        rng.shuffle(shown)
        if [pieces[i] for i in shown] != pieces:
            break
    meta = []
    toks = [t for t in p["tokens"] if t["kind"] != "other"]
    for chunk in pieces:
        bare = re.sub(f"[^{_CJK}]", "", chunk)
        w = next((t["word"] for t in toks if t["text"] == bare and t["word"] is not None), None)
        meta.append({"zh": chunk, "word_id": w.id if w else None, "py": w.pinyin if w else None})
    return {"type": "phrase_build", "item_type": "phrase", "phrase": _phrase_ref(p), "item_id": -1,
            "option_ids": [], "pieces": [meta[i] for i in shown], "answer_order": [shown.index(i) for i in range(len(pieces))],
            "hints": hints, "focus_id": focus}


def _gap(db: Session, p: dict, lesson_words: list[models.VocabularyWord], rng: random.Random) -> dict | None:
    toks = [t for t in p["tokens"] if t["word"] is not None and t["word"].id in {w.id for w in lesson_words}]
    if not toks:
        return None
    target = rng.choice(toks)
    w = target["word"]
    pool = [x for x in lesson_words if x.id != w.id and x.simplified not in p["zh"]]
    rng.shuffle(pool)
    if len(pool) < 2:
        return None
    options = [{"zh": w.simplified, "word_id": w.id, "py": w.pinyin}] + [
        {"zh": x.simplified, "word_id": x.id, "py": x.pinyin} for x in pool[:2]]
    shown = p["zh"].replace(target["text"], "＿＿", 1)
    return _choice("phrase_gap", p, options, 0, rng, w.id, shown=shown, word_id=w.id)


def build_questions(db: Session, user: models.User, lesson: models.Lesson, stage: str, rng: random.Random,
                    locale: str, translated: dict | None) -> list[dict]:
    from app.services import practice
    from app.services.gamification import user_rank

    if stage not in STAGES:
        return []
    level, _ = user_rank(db, user)
    hints = hints_for(level)
    items = practice.lesson_items(db, lesson)
    words = [w for w in items["vocab"] if practice._usable("vocab", w)]
    word_ids = {w.id for w in words}
    ps = _usable_phrases(phrases(db, lesson))
    rng.shuffle(ps)
    qs: list[dict] = []

    def word_q(w, qtype):
        q = practice._question(db, "vocab", w, len(qs), rng, translated, qtype=qtype)
        if q:
            qs.append(q)

    if stage == "listen":
        # Single sounds first (the tone of a character), then words, then phrases.
        chars = []
        for w in words:
            if len(w.simplified) == 1:
                h = db.query(models.Hanzi).filter_by(character=w.simplified).first()
                if h is not None and practice._usable("hanzi", h):
                    chars.append(h)
        for h in chars[:2]:
            q = practice._question(db, "hanzi", h, 1, rng, translated, qtype="char_to_pinyin")
            if q:
                q["speak"] = True
                qs.append(q)
        for w in words[:3]:
            word_q(w, "listen_to_word")
        glossed = [p for p in ps if p["gloss"]]
        for p in ps[:3]:
            focus = _focus(p, word_ids)
            if len(glossed) >= 3 and p["gloss"]:
                # Heard, answered by meaning: Chinese options would be readable in the payload.
                others = [o for o in glossed if o["zh"] != p["zh"]]
                rng.shuffle(others)
                opts = [{"zh": p["zh"], "py": p["py"], "gloss": p["gloss"]}] + [
                    {"zh": o["zh"], "py": o["py"], "gloss": o["gloss"]} for o in others[:2]]
                qs.append(_choice("phrase_listen", p, opts, 0, rng, focus, by="meaning"))
            else:
                opts = [{"zh": p["zh"], "py": p["py"], "gloss": p["gloss"]}] + _distractor_phrases(db, p, ps, rng)
                if len(opts) >= 2:
                    qs.append(_choice("phrase_listen", p, opts, 0, rng, focus, by="phrase"))
    elif stage == "build":
        # Guided first (one level more help than the learner's), then less.
        help_first = {"none": "some", "some": "full"}.get(hints, "full")
        built = 0
        for p in ps:
            gq = _gap(db, p, words, rng)
            if gq:
                qs.append(gq)
            bq = _build(p, help_first if built == 0 else hints, rng, _focus(p, word_ids))
            if bq:
                qs.append(bq)
                built += 1
            if len(qs) >= 7:
                break
    elif stage == "recall":
        typed = practice._recall_ready(db, user, [("vocab", w) for w in words], locale)
        # Typed from memory needs the meaning in the learner's language (as
        # practice._recall_ready); otherwise the word's meaning is chosen.
        meaning_ok = practice._translated_ids(db, "vocab_word", locale) if locale in ("ru", "tg") else None
        for i, w in enumerate(words[:4]):
            if (meaning_ok is None or w.id in meaning_ok) and (i % 2 == 0 or ("vocab", w.id) in typed):
                qs.append({"type": "type_word", "item_type": "vocab", "item_id": w.id, "option_ids": []})
            else:
                word_q(w, "word_to_meaning")
        for p in [p for p in ps if p["gloss"]][:3]:
            opts = [{"zh": p["zh"], "py": p["py"]}] + _distractor_phrases(db, p, ps, rng)
            if len(opts) >= 2:
                qs.append(_choice("phrase_meaning", p, opts, 0, rng, _focus(p, word_ids)))
    else:  # apply
        replies = [p for p in phrases(db, lesson) if p["reply"]]
        for p in replies[:2]:
            reply = next((o for o in ps if o["zh"] == re.sub(r"\s+", "", p["reply"])), None)
            answer = {"zh": re.sub(r"\s+", "", p["reply"]), "py": reply["py"] if reply else None,
                      "gloss": reply["gloss"] if reply else None}
            wrong = [{"zh": o["zh"], "py": o["py"], "gloss": o["gloss"]} for o in ps
                     if o["zh"] not in (p["zh"], answer["zh"]) and not o["reply"]]
            rng.shuffle(wrong)
            if len(wrong) >= 1:
                qs.append(_choice("phrase_reply", p, [answer] + wrong[:2], 0, rng, _focus(p, word_ids)))
        for p in [p for p in ps if p["gloss"]][:3]:
            opts = [{"zh": p["zh"], "py": p["py"], "gloss": p["gloss"]}] + _distractor_phrases(db, p, ps, rng)
            if len(opts) >= 2:
                qs.append(_choice("phrase_situation", p, opts, 0, rng, _focus(p, word_ids)))
        # Sentences without a translation (a grammar lesson's examples, the
        # words' example sentences): applying them is building them with the
        # pattern and the words' meanings in view (fewer hints than Build).
        for p in [p for p in ps if not p["gloss"]][:2]:
            if len(qs) >= 4:
                break
            bq = _build(p, _less(hints), rng, _focus(p, word_ids))
            if bq:
                qs.append(bq)
        # The independent task: one phrase built with no help at all.
        used = {q["phrase"]["zh"] for q in qs}
        for p in sorted(ps, key=lambda p: p["zh"] in used):
            bq = _build(p, "none", rng, _focus(p, word_ids))
            if bq:
                bq["final"] = True
                qs.append(bq)
                break
    if len(qs) < MIN_QUESTIONS:
        return []
    qs[0]["ctx"] = {"kind": "lesson_step", "lesson": lesson.id, "stage": stage, "hints": hints}
    return qs


# --------------------------------------------------------------------------- the lesson, played through

PLAY_UNITS = 3        # phrases taught in one lesson -- a few, each practised right away
PLAY_UNITS_GLOSSED = 4  # ... a lesson's own translated lines are short: one more
PLAY_EXTRA_WORDS = 2  # lesson words no phrase covers, taught one by one
PLAY_MIN_GRADED = 4   # fewer graded exercises than this: no played lesson (the lesson's round stays)


def _teach_phrase(p: dict) -> dict:
    """A teaching screen: one phrase, its words, its reply. Not graded --
    seeing it is not knowing it (practice.answer_question records it as
    seen, with no mastery, XP or score)."""
    return {"type": "teach", "item_type": "phrase", "kind": "phrase", "phrase": _phrase_ref(p),
            "reply": p["reply"], "template": p["template"],
            "parts": [{"text": t["text"], "word_id": t["word"].id if t["word"] is not None else None}
                      for t in p["tokens"] if t["kind"] != "other"],
            "item_id": 0, "option_ids": [0], "options": [{"zh": p["zh"]}], "focus_id": None}


def _teach_word(w: models.VocabularyWord) -> dict:
    from app.services import sentence as sent

    example = sent.clean(w.example or "")
    return {"type": "teach", "item_type": "phrase", "kind": "word",
            "phrase": {"zh": w.simplified, "py": w.pinyin, "gloss": None, "pattern": None, "topic_id": None},
            "word_id": w.id, "example": {"zh": example, "py": w.example_pinyin} if example else None,
            "parts": [], "item_id": 0, "option_ids": [0], "options": [{"zh": w.simplified}], "focus_id": None}


def build_play(db: Session, user: models.User, lesson: models.Lesson, rng: random.Random, locale: str,
               translated: dict | None) -> list[dict]:
    """The whole lesson as ONE short sequence of screens (practice source
    "lesson_play", which completes the lesson like its round: >= 70% of the
    graded answers). Each phrase is taught on its own screen and practised
    at once -- recognised (by ear or by meaning), then produced (the missing
    word, the pieces in order) -- and an earlier phrase comes back after
    each new one. Words no phrase covers are taught and heard. It ends with
    recall from memory and use: the lesson's real replies, what to say in a
    situation, and one phrase built with no help. Only what the lesson
    really has is asked; a lesson too thin to fill it returns []."""
    from app.services import practice
    from app.services.gamification import user_rank

    level, _ = user_rank(db, user)
    hints = hints_for(level)
    items = practice.lesson_items(db, lesson)
    words = [w for w in items["vocab"] if practice._usable("vocab", w)]
    word_ids = {w.id for w in words}
    every = phrases(db, lesson)
    ps = _usable_phrases(every)            # in the lesson's own order: new material gradually
    glossed = [p for p in ps if p["gloss"]]
    units = ps[:PLAY_UNITS_GLOSSED if len(glossed) >= PLAY_UNITS_GLOSSED else PLAY_UNITS]
    qs: list[dict] = []
    help_first = {"none": "some", "some": "full"}.get(hints, "full")

    def recognise(p):
        focus = _focus(p, word_ids)
        if p["gloss"] and len(glossed) >= 3:
            others = [o for o in glossed if o["zh"] != p["zh"]]
            rng.shuffle(others)
            opts = [{"zh": p["zh"], "py": p["py"], "gloss": p["gloss"]}] + [
                {"zh": o["zh"], "py": o["py"], "gloss": o["gloss"]} for o in others[:2]]
            return _choice("phrase_listen", p, opts, 0, rng, focus, by="meaning")
        opts = [{"zh": p["zh"], "py": p["py"], "gloss": p["gloss"]}] + _distractor_phrases(db, p, ps, rng)
        return _choice("phrase_listen", p, opts, 0, rng, focus, by="phrase") if len(opts) >= 2 else None

    for i, p in enumerate(units):
        qs.append(_teach_phrase(p))
        q = recognise(p)
        if q:
            qs.append(q)
        if i % 2 == 0:
            g = _gap(db, p, words, rng)
            if g:
                qs.append(g)
        b = _build(p, help_first if i == 0 else hints, rng, _focus(p, word_ids))
        if b:
            qs.append(b)
        if i >= 1:
            # An earlier phrase comes back: remembered by its meaning, or heard again.
            prev = units[i - 1]
            if prev["gloss"]:
                opts = [{"zh": prev["zh"], "py": prev["py"]}] + _distractor_phrases(db, prev, ps, rng)
                if len(opts) >= 2:
                    qs.append(_choice("phrase_meaning", prev, opts, 0, rng, _focus(prev, word_ids)))
            else:
                q = recognise(prev)
                if q:
                    qs.append(q)

    # The lesson's words that no taught phrase contains: taught, then heard.
    covered = {t["word"].id for p in units for t in p["tokens"] if t["word"] is not None}
    extra = [w for w in words if w.id not in covered][:PLAY_EXTRA_WORDS]
    for w in extra:
        qs.append(_teach_word(w))
        q = practice._question(db, "vocab", w, len(qs), rng, translated, qtype="listen_to_word")
        if q:
            qs.append(q)

    # A first lesson's sounds: one of its characters by ear, its tone.
    if (lesson.hsk_level or 1) == 1 and level <= 2:
        for w in words:
            if len(w.simplified) != 1:
                continue
            h = db.query(models.Hanzi).filter_by(character=w.simplified).first()
            q = practice._question(db, "hanzi", h, 1, rng, translated, qtype="char_to_pinyin") if (
                h is not None and practice._usable("hanzi", h)) else None
            if q:
                q["speak"] = True
                qs.append(q)
                break

    # Recall: lesson words typed from memory (their meaning must exist in the
    # learner's language, as practice._recall_ready), else recognised.
    meaning_ok = practice._translated_ids(db, "vocab_word", locale) if locale in ("ru", "tg") else None
    for w in [w for w in words if w.id in covered or w in extra][:2]:
        if meaning_ok is None or w.id in meaning_ok:
            qs.append({"type": "type_word", "item_type": "vocab", "item_id": w.id, "option_ids": []})
        else:
            q = practice._question(db, "vocab", w, len(qs), rng, translated, qtype="word_to_meaning")
            if q:
                qs.append(q)

    # Use: the lesson's real reply, what to say, one phrase with no help.
    for p in [p for p in every if p["reply"]][:1]:
        answer = {"zh": re.sub(r"\s+", "", p["reply"]), "py": None, "gloss": None}
        known = next((o for o in ps if o["zh"] == answer["zh"]), None)
        if known:
            answer.update(py=known["py"], gloss=known["gloss"])
        wrong = [{"zh": o["zh"], "py": o["py"], "gloss": o["gloss"]} for o in ps
                 if o["zh"] not in (p["zh"], answer["zh"]) and not o["reply"]]
        rng.shuffle(wrong)
        if wrong:
            qs.append(_choice("phrase_reply", p, [answer] + wrong[:2], 0, rng, _focus(p, word_ids)))
    situ = [p for p in units if p["gloss"]]
    if situ:
        p = situ[-1]
        opts = [{"zh": p["zh"], "py": p["py"], "gloss": p["gloss"]}] + _distractor_phrases(db, p, ps, rng)
        if len(opts) >= 2:
            qs.append(_choice("phrase_situation", p, opts, 0, rng, _focus(p, word_ids)))
    for p in units:
        b = _build(p, "none", rng, _focus(p, word_ids))
        if b:
            b["final"] = True
            qs.append(b)
            break

    if not qs or sum(1 for q in qs if q["type"] != "teach") < PLAY_MIN_GRADED:
        return []
    qs[0]["ctx"] = {"kind": "lesson_play", "lesson": lesson.id, "hints": hints,
                    "taught": sum(1 for q in qs if q["type"] == "teach")}
    return qs


# --------------------------------------------------------------------------- rendering and grading

def _words_of(db: Session, ids: list[int], locale: str) -> dict[int, str]:
    rows = db.query(models.VocabularyWord).filter(models.VocabularyWord.id.in_(ids or [0])).all()
    trs = load_translations(db, "vocab_word", [str(r.id) for r in rows], locale)
    return {r.id: _word_meaning(r, trs) for r in rows}


def render(db: Session, q: dict, answered: bool, locale: str) -> tuple[dict, list[dict]]:
    """What the browser may see: never the right option before the answer
    (a build's pieces come shuffled, without their order)."""
    p = q["phrase"]
    qtype = q["type"]
    gloss = gloss_for(p.get("gloss"), locale)
    prompt: dict = {"kind": qtype, "pattern": p.get("pattern")}
    if qtype == "teach":
        return _teach_prompt(db, q, locale), []
    if qtype == "phrase_build":
        hints = q.get("hints", "none")
        meanings = _words_of(db, [x["word_id"] for x in q["pieces"] if x.get("word_id")], locale) if hints != "none" else {}
        prompt.update(gloss=gloss, hints=hints, final=bool(q.get("final")), pieces=[
            {"id": i, "zh": x["zh"], "py": x.get("py") if hints == "full" else None,
             "meaning": meanings.get(x.get("word_id")) if hints != "none" else None}
            for i, x in enumerate(q["pieces"])])
        if not gloss and hints == "none":
            # An untranslated example: its words' meanings are the only fair prompt.
            prompt["words"] = list(_words_of(db, [x["word_id"] for x in q["pieces"] if x.get("word_id")], locale).values())
        options = []
    else:
        if qtype == "phrase_listen":
            prompt.update(speak=p["zh"], pinyin=p.get("py"), by=q.get("by"))
        elif qtype == "phrase_gap":
            prompt.update(text=q["shown"], gloss=gloss,
                          hint=None if gloss else _words_of(db, [q["word_id"]], locale).get(q["word_id"]))
        elif qtype in ("phrase_meaning", "phrase_situation"):
            prompt.update(gloss=gloss)
        elif qtype == "phrase_reply":
            prompt.update(text=p["zh"], speak=p["zh"], pinyin=p.get("py"), gloss=gloss)
        options = []
        for i, o in enumerate(q["options"]):
            if qtype == "phrase_listen" and q.get("by") == "meaning":
                options.append({"id": i, "label": gloss_for(o.get("gloss"), locale) or o["zh"]})
            else:
                options.append({"id": i, "label": o["zh"],
                                "pinyin": o.get("py") if (q.get("by") == "phrase" or qtype == "phrase_gap") else None})
    return prompt, options


def _teach_prompt(db: Session, q: dict, locale: str) -> dict:
    """A teaching screen: the phrase (or word) with its pinyin, its meaning
    in the learner's language and its words one by one."""
    p = q["phrase"]
    ids = [x["word_id"] for x in q.get("parts") or [] if x.get("word_id")]
    if q.get("word_id"):
        ids.append(q["word_id"])
    m = _words_of(db, ids, locale)
    rows = {r.id: r for r in db.query(models.VocabularyWord).filter(models.VocabularyWord.id.in_(ids or [0]))}
    meaning = gloss_for(p.get("gloss"), locale) if q["kind"] == "phrase" else m.get(q.get("word_id"), "")
    return {"kind": "teach", "teach": q["kind"], "zh": p["zh"], "pinyin": p.get("py"), "meaning": meaning,
            "pattern": p.get("pattern"), "reply": q.get("reply"), "template": bool(q.get("template")),
            "example": q.get("example"), "speak": p["zh"].replace("…", ""),
            "words": [{"text": x["text"], "pinyin": rows[x["word_id"]].pinyin if x.get("word_id") in rows else None,
                       "meaning": m.get(x.get("word_id"))} for x in q.get("parts") or []]}


def card(db: Session, q: dict, locale: str) -> dict:
    """The phrase, shown after the answer: Chinese, pinyin, meaning (or its
    words' meanings when the lesson gives none)."""
    p = q["phrase"]
    if q["type"] == "teach":
        t = _teach_prompt(db, q, locale)
        return {"hanzi": t["zh"], "pinyin": t["pinyin"] or "", "meaning": t["meaning"] or "", "pattern": t["pattern"]}
    gloss = gloss_for(p.get("gloss"), locale)
    zh = p["zh"]
    if q["type"] == "phrase_reply":
        right = q["options"][q["item_id"]]
        zh, gloss = right["zh"], gloss_for(right.get("gloss"), locale)
        return {"hanzi": zh, "pinyin": right.get("py") or "", "meaning": gloss or "", "pattern": p.get("pattern")}
    if not gloss:
        from app.services import sentence as sent

        toks = sent.segment(db, zh)
        ids = [t["word"].id for t in toks if t["word"] is not None]
        m = _words_of(db, ids, locale)
        gloss = " · ".join(f"{t['text']} {m.get(t['word'].id, '')}".strip() for t in toks if t["word"] is not None)
    return {"hanzi": zh, "pinyin": p.get("py") or "", "meaning": gloss or "", "pattern": p.get("pattern")}


def grade_order(q: dict, order: list[int] | None) -> tuple[bool, str]:
    """A build answer: the pieces in the learner's order. Right when it reads
    as the phrase (two equal pieces may change places)."""
    pieces = [x["zh"] for x in q["pieces"]]
    if not order or sorted(order) != list(range(len(pieces))):
        raise ValueError("Use every piece exactly once")
    given = "".join(pieces[i] for i in order)
    return given == q["phrase"]["zh"], given


def _order_rule(expected: list[str], given: list[str]) -> tuple[str | None, str | None]:
    """A word-order rule the two orders really show -- or nothing. Only
    positions are compared; the learner's reasoning is never guessed."""
    bare = lambda c: re.sub(f"[^{_CJK}]", "", c)  # noqa: E731
    e, g = [bare(c) for c in expected], [bare(c) for c in given]
    if e and e[-1] in ("吗", "呢", "吧") and g[-1] != e[-1]:
        return "particle_end", e[-1]
    if "的" in e:
        i = e.index("的")
        if 0 < i < len(e) - 1 and "的" in g:
            j = g.index("的")
            if not (0 < j < len(g) - 1 and g[j - 1] == e[i - 1] and g[j + 1] == e[i + 1]):
                return "de_between", f"{e[i - 1]}的{e[i + 1]}"
    for marker, rule in (("不", "bu_before"), ("很", "hen_before"), ("没", "bu_before")):
        if marker in e:
            i = e.index(marker)
            if i + 1 < len(e) and marker in g:
                j = g.index(marker)
                if j + 1 >= len(g) or g[j + 1] != e[i + 1]:
                    return rule, f"{marker}{e[i + 1]}"
    if "了" in e:
        i = e.index("了")
        if i > 0 and "了" in g:
            j = g.index("了")
            if j == 0 or g[j - 1] != e[i - 1]:
                return "le_after", f"{e[i - 1]}了"
    for w in TIME_WORDS:
        if w in e and w in g and g.index(w) > e.index(w):
            return "time_early", w
    # A pronoun that starts the phrase as its subject (not an owner: 我的书).
    if e and e[0] in PRONOUNS and (len(e) < 2 or e[1] != "的") and g[0] != e[0] and e[0] in g:
        return "subject_first", e[0]
    return None, None


def explain(db: Session, q: dict, answer: dict, locale: str) -> dict | None:
    """Why a phrase answer was right or wrong -- only what the stored
    question and answer show."""
    qtype = q["type"]
    p = q["phrase"]
    if qtype == "phrase_build":
        expected = [q["pieces"][i]["zh"] for i in q["answer_order"]]
        given = [q["pieces"][i]["zh"] for i in (answer.get("order") or [])]
        out = {"kind": "order", "expected": p["zh"], "given": "".join(given), "pattern": p.get("pattern"),
               "correct": bool(answer.get("correct"))}
        if not answer.get("correct"):
            rule, word = _order_rule(expected, given)
            out.update(rule=rule, word=word)
        return out
    choice = answer.get("choice_id")
    if choice is None or answer.get("correct"):
        return None
    picked, right = q["options"][choice], q["options"][q["item_id"]]
    if qtype == "phrase_gap":
        m = _words_of(db, [picked["word_id"], right["word_id"]], locale)
        return {"kind": "gap", "picked": picked["zh"], "picked_meaning": m.get(picked["word_id"], ""),
                "answer": right["zh"], "answer_meaning": m.get(right["word_id"], ""), "sentence": p["zh"]}
    kind = {"phrase_listen": "heard", "phrase_reply": "reply"}.get(qtype, "means")
    return {"kind": kind, "picked": picked["zh"], "picked_pinyin": picked.get("py"),
            "picked_meaning": gloss_for(picked.get("gloss"), locale),
            "answer": right["zh"], "answer_pinyin": right.get("py") or (p.get("py") if right["zh"] == p["zh"] else None),
            "answer_meaning": gloss_for(right.get("gloss"), locale), "asked": p["zh"] if qtype == "phrase_reply" else None}


# --------------------------------------------------------------------------- the lesson page

def records(db: Session, user: models.User, lesson_id: int) -> dict[str, dict]:
    """This learner's completed rounds of each stage of the lesson."""
    out: dict[str, dict] = {}
    rows = db.query(models.PracticeSession).filter(
        models.PracticeSession.user_id == user.id, models.PracticeSession.source == "lesson_step",
        models.PracticeSession.completed_at.isnot(None)).all()
    for s in rows:
        ctx = (s.questions or [{}])[0].get("ctx") or {}
        if ctx.get("lesson") != lesson_id or ctx.get("stage") not in STAGES:
            continue
        r = out.setdefault(ctx["stage"], {"played": 0, "best": 0.0})
        r["played"] += 1
        r["best"] = max(r["best"], s.score or 0.0)
    return out


def flow(db: Session, user: models.User, lesson: models.Lesson, locale: str) -> dict:
    """Everything the lesson page shows, in order, with the learner's own
    record in each stage. Which stages a lesson has depends on its material
    (a stage it cannot fill is left out, never padded)."""
    from app.services import journey, practice
    from app.services import sentence as sent
    from app.services.gamification import user_rank
    from app.services.grammar_names import titles as grammar_titles

    level, _ = user_rank(db, user)
    items = practice.lesson_items(db, lesson)
    ps = phrases(db, lesson)
    word_ids = [w.id for w in items["vocab"]]
    token_ids = [t["word"].id for p in ps for t in p["tokens"] if t["word"] is not None]
    meanings = _words_of(db, word_ids + token_ids, locale)

    learn = []
    for p in ps:
        learn.append({
            "zh": p["zh"], "pinyin": p["py"], "meaning": gloss_for(p["gloss"], locale), "template": p["template"],
            "reply": p["reply"], "pattern": p["pattern"],
            "words": [{"text": t["text"], "pinyin": t["word"].pinyin if t["word"] is not None else None,
                       "meaning": meanings.get(t["word"].id) if t["word"] is not None else None}
                      for t in p["tokens"] if t["kind"] != "other"],
        })
    examples = {}
    for w in items["vocab"]:
        if w.example:
            examples[w.id] = {"zh": sent.clean(w.example), "pinyin": w.example_pinyin}
    grammar = []
    g_titles = grammar_titles(db, items["grammar"], locale)
    g_tr = load_translations(db, "grammar_topic", [str(g.id) for g in items["grammar"]], locale)
    for g in items["grammar"]:
        grammar.append({"id": g.id, "title": g_titles.get(g.id, g.title), "pattern": g.pattern,
                        "explanation": tr(g_tr, g.id, "explanation", g.explanation),
                        "examples": [p["zh"] for p in ps if p["topic_id"] == g.id][:3]})

    recs = records(db, user, lesson.id)
    probe = random.Random(lesson.id)
    stages = []
    for st in STAGES:
        r = recs.get(st, {"played": 0, "best": 0.0})
        # Offered only when the lesson can fill it (built once, deterministically, and thrown away).
        available = bool(build_questions(db, user, lesson, st, probe, locale, None))
        stages.append({"key": st, "available": available, "played": r["played"], "best": round(r["best"], 1),
                       "done": r["best"] >= PASS})
    progress = db.query(models.Progress).filter_by(user_id=user.id, lesson_id=lesson.id).first()
    lesson_level = lesson.hsk_level or 1
    played = [x.score or 0.0 for x in db.query(models.PracticeSession).filter(
        models.PracticeSession.user_id == user.id, models.PracticeSession.source == "lesson_play",
        models.PracticeSession.lesson_id == lesson.id, models.PracticeSession.completed_at.isnot(None))]
    play_qs = build_play(db, user, lesson, random.Random(lesson.id), locale, None)
    ev = journey.evidence(db, user)
    return {
        "lesson_id": lesson.id, "level": lesson_level, "learner_level": level, "hints": hints_for(level),
        # A beginner who hasn't done the sounds yet is pointed at them (not forced).
        "pinyin_first": lesson_level == 1 and level <= 1 and not journey._step_done("tones", ev),
        # Above this lesson's level: the stages are optional, the check is open now.
        "known_level": level > lesson_level,
        "phrases": learn,
        "words": [{"id": w.id, "zh": w.simplified, "pinyin": w.pinyin, "meaning": meanings.get(w.id, ""),
                   "example": examples.get(w.id)} for w in items["vocab"]],
        "grammar": grammar,
        "stages": stages,
        # The lesson played through (build_play): how many screens, how many
        # taught, and this learner's record in it.
        "play": {"available": bool(play_qs), "screens": len(play_qs),
                 "taught": sum(1 for q in play_qs if q["type"] == "teach"),
                 "played": len(played), "best": round(max(played), 1) if played else None},
        "pass_score": PASS,
        "check": {"status": progress.status if progress else "not_started",
                  "score": progress.score if progress else None,
                  "practicable": bool(items["vocab"] or items["grammar"])},
    }
