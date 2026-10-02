"""One Sentence -> Complete Lesson.

A learner brings one Chinese sentence (or takes one of the curriculum's own
example sentences) and it is turned into a lesson built ONLY from real rows:

  words       the sentence split into curriculum words (longest match
              against VocabularyWord, the same idea lesson_items uses), each
              with its HSK level and the learner's own status for it
  characters  every character, from the Hanzi table (reading, meaning,
              radical, strokes) with the learner's status
  grammar     curriculum grammar points the sentence demonstrably uses,
              found by GRAMMAR_RULES (a pattern -> the topic's real title);
              a point the rules don't know is simply not claimed
  pinyin      joined from the words' / characters' own readings
  translation the AI translation when an AI provider answers, else None --
              the word-by-word gloss (real localized meanings) is always there

The graded practice round itself is built by practice.build_session
(source "sentence") through build_questions below, so every answer goes
through the same server grading, SRS, mistakes, DNA and XP as any round.
"""

from __future__ import annotations

import random
import re
from datetime import datetime

from sqlalchemy.orm import Session

from app import models
from app.services.localization import load_translations, tr

_CJK = re.compile(r"[㐀-鿿]")
MAX_CHARS = 40
_SEGMENT_MAX = 4


class SentenceError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


# (pattern, grammar topic title, unless-pattern). Titles are the curriculum's
# natural keys; a title missing from a database is skipped, never invented.
# Order matters only for display: the more specific pattern of a pair comes
# first and its `unless` keeps the generic one from double-claiming.
GRAMMAR_RULES: list[tuple[str, str, str | None]] = [
    (r"因为.+所以", "因为……所以…… — because/therefore", None),
    (r"虽然.+(但是|可是|但)", "虽然……但是…… — although/but", None),
    (r"不但.+而且", "不但……而且…… — not only/but also", None),
    (r"只要.+就", "只要……就…… — as long as", None),
    (r"无论.+都", "无论……都…… — no matter what", None),
    (r"尽管", "尽管……还是…… — despite/still", None),
    (r"除了.+(以外|之外)", "除了……以外 — besides/except", None),
    (r"一边.+一边", "一边……一边…… — simultaneous actions", None),
    (r"越来越", "越来越 — increasingly", None),
    (r"又.+又", "又⋯⋯又⋯⋯", None),
    (r"如果.+(就|的话)", "假设复句", None),
    (r"(?<![一统])把(?!手)", "把字句 — the 把 construction", None),
    (r"被", "被字句 — the passive with 被", None),
    (r"是.+的[。！？!?]?$", "“是⋯⋯的”句1：强调时间、地点、方式、动作者", None),
    (r"(?<![还但可就总于要只真倒像])是(?!不是)", "是 — to be", r"是.+的[。！？!?]?$"),
    (r"比(?!较|赛|如)", "比 — comparison", None),
    (r"太.+了", "太……了 — excessively", None),
    (r"正在", "正在/在 — progressive aspect", None),
    (r"(?<![正现实存])在", "在 — location / progressive", r"正在"),
    (r"[动跑说写做走吃唱学长讲开].?得(很|非常|太|真|不|好|快|慢|清楚|多)", "状态补语1：动词+得+形容词性词语", None),
    (r"(?<![为除])了", "了 — completed action", r"太.+了"),
    (r"(?<![不难经通])过(?![来去年])", "动态助词：过", None),
    (r"着(?!急)", "动态助词：着", None),
    (r"已经", "时间副词：刚、刚刚、还、忽然、一直、已经", None),
    (r"还是.+[？?]", "用“还是”提问", None),
    (r"吗[？?]?$", "吗 — yes/no question", None),
    (r"呢[？?]", "呢 — follow-up question", None),
    (r"(?<![机社约开聚体学])会(?![议儿])|能(?!力|源)", "会/能 — ability, possibility", None),
    (r"想(?!法)|(?<![需重主只不])要(?!求)", "能愿动词：想、要", None),
    (r"应该", "能愿动词：该、应该", None),
    (r"(?<!不)都", "都 — all", None),
    (r"一下", "一下 — brief action", None),
    (r"一点儿?", "一点儿 — a little", None),
    (r"几|多少", "几/多少 — asking quantity", None),
    (r"[一两三四五六七八九十几这那每]个", "个 — measure word", None),
    (r"(?<![所还])有(?!点|些|时|名|意思|用)", "有 — to have / there is", None),
    (r"(?<![目真别])的(?![。！？!?]?$)", "的 — possession", None),
    (r"不(?!过|但|管|用)", "不 — negation", None),
    (r"(这|那)(?!么|样)", "这/那 — this/that", None),
    (r"(以前|以后)", "（在）⋯⋯以前/以后/前/后", None),
]


def uses_grammar(title: str, text: str) -> bool:
    """Whether `text` uses the grammar point titled `title` by GRAMMAR_RULES."""
    return any(
        t == title and re.search(pattern, text) and not (unless and re.search(unless, text))
        for pattern, t, unless in GRAMMAR_RULES
    )


def clean(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip())


def _level_map(db: Session) -> dict[int, int]:
    return {lvl.id: lvl.level for lvl in db.query(models.HSKLevel).all()}


def _pieces(text: str) -> set[str]:
    out = set()
    for run in re.findall(r"[㐀-鿿]+", text):
        for n in range(1, _SEGMENT_MAX + 1):
            out.update(run[i:i + n] for i in range(len(run) - n + 1))
    return out


def vocab_rows(db: Session, text: str) -> dict[str, models.VocabularyWord]:
    """Every curriculum word that occurs in `text`, one row per spelling
    (lowest HSK level first -- the level a learner meets it at)."""
    pieces = _pieces(text)
    if not pieces:
        return {}
    levels = _level_map(db)
    rows = db.query(models.VocabularyWord).filter(models.VocabularyWord.simplified.in_(pieces)).all()
    best: dict[str, models.VocabularyWord] = {}
    for r in sorted(rows, key=lambda r: (levels.get(r.hsk_level_id, 99), r.id)):
        best.setdefault(r.simplified, r)
    return best


def segment(db: Session, text: str, known: dict[str, models.VocabularyWord] | None = None) -> list[dict]:
    """Forward longest-match split into curriculum words. A Chinese
    character no word covers stays a single "char" token; anything else
    (punctuation, digits, Latin) is "other"."""
    known = vocab_rows(db, text) if known is None else known
    out: list[dict] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if not _CJK.match(ch):
            if out and out[-1]["kind"] == "other":
                out[-1]["text"] += ch
            else:
                out.append({"text": ch, "kind": "other", "word": None})
            i += 1
            continue
        for size in range(min(_SEGMENT_MAX, len(text) - i), 0, -1):
            piece = text[i:i + size]
            if all(_CJK.match(c) for c in piece) and piece in known:
                out.append({"text": piece, "kind": "word", "word": known[piece]})
                i += size
                break
        else:
            out.append({"text": ch, "kind": "char", "word": None})
            i += 1
    return out


def hanzi_rows(db: Session, chars: set[str]) -> dict[str, models.Hanzi]:
    if not chars:
        return {}
    levels = _level_map(db)
    rows = db.query(models.Hanzi).filter(models.Hanzi.character.in_(chars)).all()
    best: dict[str, models.Hanzi] = {}
    for r in sorted(rows, key=lambda r: (levels.get(r.hsk_level_id, 99), r.id)):
        best.setdefault(r.character, r)
    return best


def match_grammar(db: Session, text: str) -> list[models.GrammarTopic]:
    titles = []
    for pattern, title, unless in GRAMMAR_RULES:
        if re.search(pattern, text) and not (unless and re.search(unless, text)):
            titles.append(title)
    if not titles:
        return []
    levels = _level_map(db)
    rows = db.query(models.GrammarTopic).filter(models.GrammarTopic.title.in_(titles)).all()
    best: dict[str, models.GrammarTopic] = {}
    for r in sorted(rows, key=lambda r: (levels.get(r.hsk_level_id, 99), r.id)):
        best.setdefault(r.title, r)
    return [best[t] for t in titles if t in best]


def validate(db: Session, text: str) -> str:
    """The sentence a lesson can honestly be built from, or a 422 that says
    why not."""
    text = clean(text)
    cjk = _CJK.findall(text)
    if len(cjk) < 2:
        raise SentenceError(422, "Enter a Chinese sentence (at least two characters)")
    if len(cjk) > MAX_CHARS:
        raise SentenceError(422, f"Keep the sentence to {MAX_CHARS} Chinese characters or fewer")
    letters = [c for c in text if c.isalpha()]
    if len(cjk) < 0.6 * len(letters):
        raise SentenceError(422, "The sentence should be written in Chinese characters")
    tokens = segment(db, text)
    loose = {t["text"] for t in tokens if t["kind"] == "char"}
    unknown = sorted(loose - set(hanzi_rows(db, loose)))
    if unknown:
        raise SentenceError(422, f"These characters aren't in the HSK curriculum yet: {''.join(unknown)}")
    if not any(t["kind"] == "word" for t in tokens):
        raise SentenceError(422, "No HSK words were found in this sentence")
    return text


def _status(rec) -> str:
    return rec.status if rec is not None else "new"


def tier_for(level: int) -> str:
    return "beginner" if level <= 2 else "intermediate" if level <= 4 else "advanced"


def analyze(db: Session, user: models.User, text: str, locale: str, *, translate: bool = True) -> dict:
    from app.services import ai_client
    from app.services.gamification import user_rank

    text = validate(db, text)
    level, _ = user_rank(db, user)
    levels = _level_map(db)
    tokens = segment(db, text)
    words = [t["word"] for t in tokens if t["word"] is not None]
    chars = {c for c in text if _CJK.match(c)}
    hanzi = hanzi_rows(db, chars)
    grammar = match_grammar(db, text)

    word_ids = [w.id for w in words]
    word_recs = {r.word_id: r for r in db.query(models.UserVocabulary).filter(
        models.UserVocabulary.user_id == user.id, models.UserVocabulary.word_id.in_(word_ids or [0]))}
    hanzi_recs = {r.hanzi_id: r for r in db.query(models.UserHanzi).filter(
        models.UserHanzi.user_id == user.id, models.UserHanzi.hanzi_id.in_([h.id for h in hanzi.values()] or [0]))}
    grammar_recs = {r.topic_id: r for r in db.query(models.UserGrammar).filter(
        models.UserGrammar.user_id == user.id, models.UserGrammar.topic_id.in_([g.id for g in grammar] or [0]))}
    vocab_tr = load_translations(db, "vocab_word", [str(i) for i in word_ids], locale)
    hanzi_tr = load_translations(db, "hanzi", [str(h.id) for h in hanzi.values()], locale)
    grammar_tr = load_translations(db, "grammar_topic", [str(g.id) for g in grammar], locale)

    def word_meaning(w):
        label = tr(vocab_tr, w.id, "meanings", w.meanings)
        # zh "meanings" mirror the word itself (see practice._labels).
        return w.meanings if (label or "").strip() == w.simplified else label

    out_tokens = []
    pinyin_parts = []
    for t in tokens:
        if t["kind"] == "word":
            w = t["word"]
            lvl = levels.get(w.hsk_level_id)
            out_tokens.append({
                "text": t["text"], "kind": "word", "word_id": w.id, "pinyin": w.pinyin,
                "meaning": word_meaning(w), "level": lvl, "status": _status(word_recs.get(w.id)),
                "above_level": bool(lvl and lvl > level),
            })
            pinyin_parts.append(w.pinyin)
        elif t["kind"] == "char":
            h = hanzi.get(t["text"])
            out_tokens.append({
                "text": t["text"], "kind": "char", "pinyin": h.pinyin if h else "",
                "meaning": tr(hanzi_tr, h.id, "meaning", h.meaning) if h else "",
                "level": levels.get(h.hsk_level_id) if h else None, "status": None, "above_level": False,
            })
            pinyin_parts.append(h.pinyin if h else "")
        else:
            out_tokens.append({"text": t["text"], "kind": "other"})
            if pinyin_parts:
                pinyin_parts[-1] += t["text"].replace("。", ".").replace("，", ",").replace("？", "?").replace("！", "!")

    characters = []
    for c in dict.fromkeys(c for c in text if _CJK.match(c)):
        h = hanzi.get(c)
        if h is None:
            continue
        rec = hanzi_recs.get(h.id)
        characters.append({
            "char": c, "hanzi_id": h.id, "pinyin": h.pinyin, "meaning": tr(hanzi_tr, h.id, "meaning", h.meaning),
            "radical": h.radical, "stroke_count": h.stroke_count, "level": levels.get(h.hsk_level_id),
            "status": _status(rec), "times_missed": rec.times_missed if rec else 0,
        })

    grammar_out = []
    for g in grammar:
        lvl = levels.get(g.hsk_level_id)
        grammar_out.append({
            "id": g.id, "title": tr(grammar_tr, g.id, "title", g.title), "pattern": g.pattern,
            "explanation": tr(grammar_tr, g.id, "explanation", g.explanation), "level": lvl,
            "status": _status(grammar_recs.get(g.id)), "above_level": bool(lvl and lvl > level),
        })

    word_levels = [t["level"] for t in out_tokens if t.get("kind") == "word" and t.get("level")]
    sentence_level = max(word_levels) if word_levels else level
    fit = "above" if sentence_level > level + 1 else "below" if sentence_level < level - 1 else "at"
    counts = {"new": 0, "learning": 0, "mastered": 0}
    for t in out_tokens:
        if t.get("kind") == "word":
            key = "mastered" if t["status"] == "mastered" else "new" if t["status"] == "new" else "learning"
            counts[key] += 1

    translation = ai_client.translate_sentence(text, locale) if translate else None
    return {
        "text": text,
        "pinyin": " ".join(p for p in pinyin_parts if p),
        "translation": translation,
        "tokens": out_tokens,
        "characters": characters,
        "grammar": grammar_out,
        "level": {"user": level, "sentence": sentence_level, "fit": fit, "tier": tier_for(level)},
        "counts": counts,
    }


def suggestions(db: Session, user: models.User, locale: str, limit: int = 4) -> list[dict]:
    """Real example sentences from the curriculum at the learner's level:
    first those of words they're learning right now (most review-worthy
    first), then words of their level they haven't started, in curriculum
    order. Every suggestion passes the same validation a typed sentence
    does, so picking one always yields a lesson."""
    from app.services.gamification import user_rank
    from app.services.hsk_band import resolve_level_filter

    level, _ = user_rank(db, user)
    picked: list[models.VocabularyWord] = []
    learning = (
        db.query(models.VocabularyWord)
        .join(models.UserVocabulary, models.UserVocabulary.word_id == models.VocabularyWord.id)
        .filter(models.UserVocabulary.user_id == user.id, models.UserVocabulary.status != "mastered",
                models.VocabularyWord.example.isnot(None))
        .order_by(models.UserVocabulary.mastery, models.VocabularyWord.id)
        .limit(20)
        .all()
    )
    picked.extend(learning)
    level_id, subset = resolve_level_filter(db, models.VocabularyWord, models.VocabularyWord.hsk_level_id, level)
    seen_ids = {r.word_id for r in db.query(models.UserVocabulary.word_id).filter(models.UserVocabulary.user_id == user.id)}
    q = db.query(models.VocabularyWord).filter(
        models.VocabularyWord.hsk_level_id == (level_id or 0), models.VocabularyWord.example.isnot(None))
    if subset is not None:
        q = q.filter(models.VocabularyWord.id.in_(subset or [0]))
    picked.extend(w for w in q.order_by(models.VocabularyWord.id).limit(60) if w.id not in seen_ids)

    trs = load_translations(db, "vocab_word", [str(w.id) for w in picked], locale)
    out, seen = [], set()
    for w in picked:
        sentence = clean(w.example)
        if sentence in seen:
            continue
        try:
            validate(db, sentence)
        except SentenceError:
            continue
        seen.add(sentence)
        meaning = tr(trs, w.id, "meanings", w.meanings)
        out.append({
            "text": sentence, "pinyin": w.example_pinyin,
            "word": {"hanzi": w.simplified, "pinyin": w.pinyin,
                     "meaning": w.meanings if (meaning or "").strip() == w.simplified else meaning},
        })
        if len(out) >= limit:
            break
    return out


# --------------------------------------------------------------------------- practice questions

SIZE = {"beginner": (3, 1), "intermediate": (4, 2), "advanced": (4, 2)}  # (words, characters)


def _chunks(tokens: list[dict]) -> list[str]:
    """The sentence in movable pieces for the word-order question:
    punctuation stays glued to the piece before it."""
    out: list[str] = []
    for t in tokens:
        if t["kind"] == "other" and out:
            out[-1] += t["text"]
        else:
            out.append(t["text"])
    return out


def build_questions(db: Session, user: models.User, text: str, level: int, rng: random.Random,
                    translated: dict | None) -> list[dict]:
    """The graded activities for one sentence (see module docstring)."""
    from app.services import practice

    text = validate(db, text)
    tier = tier_for(level)
    levels = _level_map(db)
    tokens = segment(db, text)
    words = list({t["word"].id: t["word"] for t in tokens if t["word"] is not None}.values())
    now = datetime.utcnow()
    questions: list[dict] = []

    # Vocabulary: the words this learner still needs, easiest stretch first.
    # Far-above-level words stay in the breakdown but aren't drilled.
    recs = {r.word_id: r for r in db.query(models.UserVocabulary).filter(
        models.UserVocabulary.user_id == user.id, models.UserVocabulary.word_id.in_([w.id for w in words] or [0]))}
    drill = [w for w in words if practice._usable("vocab", w)
             and levels.get(w.hsk_level_id, 1) <= level + 2
             and (recs.get(w.id) is None or recs[w.id].status != "mastered")]
    drill.sort(key=lambda w: (recs.get(w.id) is not None and recs[w.id].next_review_at is not None
                              and recs[w.id].next_review_at > now, levels.get(w.hsk_level_id, 1), w.id))
    n_words, n_chars = SIZE[tier]
    for i, w in enumerate(drill[:n_words]):
        q = practice._question(db, "vocab", w, i, rng, translated)
        if q:
            questions.append(q)

    # Characters: reading and tone of the ones not mastered yet.
    hanzi = hanzi_rows(db, {c for c in text if _CJK.match(c)})
    hrecs = {r.hanzi_id: r for r in db.query(models.UserHanzi).filter(
        models.UserHanzi.user_id == user.id, models.UserHanzi.hanzi_id.in_([h.id for h in hanzi.values()] or [0]))}
    chars = [h for h in hanzi.values() if practice._usable("hanzi", h)
             and (hrecs.get(h.id) is None or hrecs[h.id].status != "mastered")]
    chars.sort(key=lambda h: (-(hrecs[h.id].times_missed if h.id in hrecs else 0), levels.get(h.hsk_level_id, 1), h.id))
    for i, h in enumerate(chars[:n_chars]):
        # char_to_pinyin first: pronunciation is one of the lesson's parts.
        q = practice._question(db, "hanzi", h, i + 1, rng, translated)
        if q:
            questions.append(q)

    # Grammar: "which point does THIS sentence use?"
    for g in match_grammar(db, text):
        if levels.get(g.hsk_level_id, 1) > level + 1:
            continue
        q = practice._question(db, "grammar", g, 0, rng, translated)
        if q:
            q["prompt"] = text
            questions.append(q)
            break

    content = [t for t in tokens if t["kind"] == "word"]
    focus_word = drill[0] if drill else (content[0]["word"] if content else None)
    say = {"zh": text, "keywords": [t["text"] for t in content]}

    # Reading comprehension: which word of the sentence means X?
    distinct = list(dict.fromkeys(t["text"] for t in tokens if t["kind"] in ("word", "char")))
    target = next((t for t in content if t["word"] is not None and t["word"].id == (focus_word.id if focus_word else -1)), None)
    if target is not None and len(distinct) >= 3:
        opts = [target["text"]] + [x for x in distinct if x != target["text"]]
        opts = opts[:4]
        rng.shuffle(opts)
        questions.append({
            "type": "sentence_word", "item_type": "sentence", "item_id": opts.index(target["text"]),
            "option_ids": list(range(len(opts))), "options": [{"zh": o} for o in opts],
            "sentence": text, "word_id": target["word"].id, "focus_id": target["word"].id,
        })

    # Listening: hear it, pick the sentence that was said (variants swap one
    # real word for another real word of the same length and level).
    variants = _variants(db, tokens, rng)
    if len(variants) >= 2:
        opts = [text] + variants[: (3 if tier == "advanced" else 2)]
        rng.shuffle(opts)
        questions.append({
            "type": "sentence_listen", "item_type": "sentence", "item_id": opts.index(text),
            "option_ids": list(range(len(opts))), "options": [{"zh": o} for o in opts],
            "sentence": text, "focus_id": focus_word.id if focus_word else None, "say": say,
        })

    # Word order: rebuild the sentence from its pieces.
    pieces = _chunks(tokens)
    if len(pieces) >= 3:
        orders = {tuple(pieces)}
        attempts = 0
        while len(orders) < (4 if tier == "advanced" else 3) and attempts < 30:
            attempts += 1
            p = pieces[:]
            rng.shuffle(p)
            orders.add(tuple(p))
        if len(orders) >= 3:
            opts = [list(o) for o in orders]
            rng.shuffle(opts)
            questions.append({
                "type": "sentence_order", "item_type": "sentence", "item_id": opts.index(pieces),
                "option_ids": list(range(len(opts))), "options": [{"zh": " ".join(o)} for o in opts],
                "chunks": sorted(pieces, key=lambda _x: rng.random()),
                "sentence": text, "focus_id": focus_word.id if focus_word else None, "say": say,
                "grammar_title": next((g.title for g in match_grammar(db, text)), None),
            })
    if not questions:
        raise SentenceError(422, "This sentence is too short to build a lesson from")
    pinyin = " ".join(t["word"].pinyin for t in tokens if t["word"] is not None)
    for q in questions:
        if q["item_type"] == "sentence":
            q["pinyin"] = pinyin
    questions[0]["ctx"] = {"kind": "sentence", "text": text, "pinyin": pinyin, "tier": tier}
    return questions


def _variants(db: Session, tokens: list[dict], rng: random.Random) -> list[str]:
    words = [(i, t["word"]) for i, t in enumerate(tokens) if t["word"] is not None and len(t["text"]) >= 1]
    rng.shuffle(words)
    out: list[str] = []
    for i, w in words:
        pool = (
            db.query(models.VocabularyWord.simplified)
            .filter(models.VocabularyWord.hsk_level_id == w.hsk_level_id,
                    models.VocabularyWord.id != w.id)
            .limit(400)
            .all()
        )
        same = [s for (s,) in pool if len(s) == len(w.simplified) and s != w.simplified]
        if not same:
            continue
        swap = rng.choice(same)
        variant = "".join(swap if j == i else t["text"] for j, t in enumerate(tokens))
        if variant not in out:
            out.append(variant)
        if len(out) >= 3:
            break
    return out
