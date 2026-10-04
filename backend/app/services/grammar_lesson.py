"""A grammar point as a full learning page -- not a title and two examples.

The curriculum's 600 grammar topics come from the official syllabus: a
title, a pattern and example lines, and (for all but the ~30 hand-written
core points) no explanation at all. A page built on that alone was the
"two sentences and nothing else" the learner saw. This module builds the
page from three layers, each honest about where it comes from:

  1. curriculum data, always: the pattern, every syllabus example split
     into sentences, each with pinyin and a word-by-word gloss from the
     curriculum's own words and Hanzi (never typed by hand, never guessed),
     the learner's real progress on the point, related points and the
     words the examples use with the learner's own status for each.
  2. an authored lesson (seed_content/grammar/*.json) for the core points:
     meaning, structure, when (not) to use it, common mistakes with wrong
     vs right sentences, similar patterns, a dialogue and exercises --
     written in all four interface languages.
  3. otherwise an AI lesson in the same shape, generated once per topic and
     language and cached in ai_explanations (it depends on the topic and the
     language only, never on the learner). Its Chinese is checked by
     services/sentence_check.py: a "correct" example the rules flag as a
     known error is dropped, never shown.

Pinyin on every Chinese sentence -- authored or AI -- is computed here
from the curriculum, so a model can't put a wrong reading on the page.
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import time

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.services import sentence as sent
from app.services import sentence_check
from app.services import story_slots as ss
from app.services.localization import load_translations, tr

LESSONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seed_content", "grammar")
LANGS = ("en", "ru", "tg", "zh")
AI_PER_HOUR = 20     # uncached AI lessons one learner may trigger per hour
CHECKS_PER_HOUR = 60  # AI-judged "try it" answers per learner per hour
_CJK = re.compile(r"[㐀-鿿]")
# Lines of the syllabus examples that aren't example sentences: numbered
# sub-headings ("（1）名量词：碗、脸"), cross-references ("见【一37】").
_HEADING = re.compile(r"^\s*(?:[（(]\d+[)）]|[①-⑳])\s*")
_XREF = re.compile(r"[（(]?见【[^】]*】[^）)]*[）)]?")
_SENTENCE_END = re.compile(r"(?<=[。！？!?])")


class GrammarError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


# --------------------------------------------------------------------------- authored lessons
_AUTHORED: dict[str, dict] | None = None


def authored() -> dict[str, dict]:
    """Hand-written lessons keyed by grammar topic title (the curriculum's
    natural key). Static content, loaded once."""
    global _AUTHORED
    if _AUTHORED is None:
        out = {}
        for path in sorted(glob.glob(os.path.join(LESSONS_DIR, "*.json"))):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            out[data["topic"]] = data
        _AUTHORED = out
    return _AUTHORED


def _loc(value, locale: str):
    """A localized field of an authored lesson in `locale` (English when a
    language is missing). Chinese strings and lists pass through."""
    # A localized string is a dict of language codes only ({"en", "ru", ...});
    # an example item {"zh", "tr"} is not one, though it has a "zh" key.
    if isinstance(value, dict) and value and "en" in value and set(value) <= set(LANGS):
        return value.get(locale) or value.get("en")
    if isinstance(value, list):
        return [_loc(v, locale) for v in value]
    if isinstance(value, dict):
        return {k: _loc(v, locale) for k, v in value.items()}
    return value


# --------------------------------------------------------------------------- curriculum data
def example_blocks(topic: models.GrammarTopic) -> list[dict]:
    """The syllabus example text as blocks: {"kind": "heading", "text"},
    {"kind": "sentence", "zh"} or {"kind": "phrases", "items"}. Lines like
    "我是学生。 / 他是老师。" hold several examples."""
    blocks: list[dict] = []
    for raw in (topic.examples or "").splitlines():
        line = _XREF.sub("", raw).strip()
        if not line or not _CJK.search(line):
            continue
        if _HEADING.match(line):
            blocks.append({"kind": "heading", "text": _HEADING.sub("", line).strip()})
            continue
        for part in re.split(r"\s+/\s+|\s*/\s*(?=[㐀-鿿])", line):
            part = part.strip()
            if not part:
                continue
            if re.search(r"[。！？!?]", part):
                for s in _SENTENCE_END.split(part):
                    s = s.strip()
                    if _CJK.search(s):
                        blocks.append({"kind": "sentence", "zh": s})
            else:
                # 桌子上 树下 房间里 -- a list of phrases, not one sentence.
                items = [p for p in re.split(r"\s+", part) if _CJK.search(p)]
                if len(items) > 1:
                    blocks.append({"kind": "phrases", "items": items})
                elif items:
                    blocks.append({"kind": "sentence", "zh": items[0]})
    return blocks


def annotate(db: Session, texts: list[str], locale: str) -> dict[str, dict]:
    """Pinyin and a word-by-word gloss for each Chinese text, from the
    curriculum. One query for all words and one for all loose characters."""
    joined = "".join(texts)
    known = sent.vocab_rows(db, joined)
    toks_by = {t: sent.segment(db, t, known) for t in texts}
    word_ids = {tok["word"].id for toks in toks_by.values() for tok in toks if tok["word"] is not None}
    meanings = ss.meanings(db, list(word_ids), locale)
    loose = {tok["text"] for toks in toks_by.values() for tok in toks if tok["kind"] == "char"}
    hz = sent.hanzi_rows(db, loose)
    hz_tr = load_translations(db, "hanzi", [str(h.id) for h in hz.values()], locale)
    out = {}
    for text, toks in toks_by.items():
        words, pinyin = [], []
        for tok in toks:
            if tok["word"] is not None:
                w = tok["word"]
                words.append({"text": tok["text"], "pinyin": w.pinyin, "meaning": meanings.get(w.id, ""), "word_id": w.id})
                pinyin.append(w.pinyin)
            elif tok["kind"] == "char":
                h = hz.get(tok["text"])
                words.append({"text": tok["text"], "pinyin": h.pinyin if h else "",
                              "meaning": tr(hz_tr, h.id, "meaning", h.meaning) if h else ""})
                if h and h.pinyin:
                    pinyin.append(h.pinyin.split(",")[0].strip())
            elif tok["kind"] == "other" and pinyin:
                pinyin[-1] += tok["text"].strip()
        out[text] = {"pinyin": " ".join(p for p in pinyin if p), "words": words}
    return out


def _level_of(db: Session, topic: models.GrammarTopic) -> int:
    lvl = db.get(models.HSKLevel, topic.hsk_level_id)
    return lvl.level if lvl else 1


def related(db: Session, topic: models.GrammarTopic, locale: str, extra_titles: list[str] = ()) -> list[dict]:
    """Points to read next to this one: those an authored/AI lesson names
    as similar, then neighbours in the same syllabus group at this level."""
    rows: list[models.GrammarTopic] = []
    if extra_titles:
        rows += db.query(models.GrammarTopic).filter(models.GrammarTopic.title.in_(list(extra_titles))).all()
    q = db.query(models.GrammarTopic).filter(
        models.GrammarTopic.hsk_level_id == topic.hsk_level_id, models.GrammarTopic.id != topic.id)
    if topic.category:
        q = q.filter(models.GrammarTopic.category == topic.category)
    rows += q.order_by(models.GrammarTopic.order_index, models.GrammarTopic.id).limit(6).all()
    seen, out = {topic.id}, []
    trs = load_translations(db, "grammar_topic", [str(r.id) for r in rows], locale)
    levels = sent._level_map(db)
    for r in rows:
        if r.id in seen:
            continue
        seen.add(r.id)
        out.append({"id": r.id, "title": tr(trs, r.id, "title", r.title), "pattern": r.pattern,
                    "hsk_level": levels.get(r.hsk_level_id)})
    return out[:6]


def _progress(db: Session, user: models.User, topic: models.GrammarTopic) -> dict:
    from datetime import datetime

    rec = db.query(models.UserGrammar).filter_by(user_id=user.id, topic_id=topic.id).first()
    if rec is None:
        return {"status": "new", "mastery": 0.0, "times_practiced": 0, "due": False, "next_review_at": None}
    return {
        "status": rec.status or "new", "mastery": round(rec.mastery or 0.0, 1),
        "times_practiced": rec.times_practiced or 0,
        "due": bool(rec.next_review_at and rec.next_review_at <= datetime.utcnow()),
        "next_review_at": rec.next_review_at.isoformat() if rec.next_review_at else None,
    }


def _vocabulary(db: Session, user: models.User, annotated: dict[str, dict], extra: list[str], locale: str) -> list[dict]:
    """Curriculum words the page's examples use (plus any the lesson names),
    with the learner's real status for each -- at most 16."""
    ids: list[int] = []
    for a in annotated.values():
        for w in a["words"]:
            if w.get("word_id") and w["word_id"] not in ids:
                ids.append(w["word_id"])
    if extra:
        rows = sent.vocab_rows(db, "".join(extra))
        for word in extra:
            if word in rows and rows[word].id not in ids:
                ids.insert(0, rows[word].id)
    ids = ids[:16]
    rows = {r.id: r for r in db.query(models.VocabularyWord).filter(models.VocabularyWord.id.in_(ids or [0]))}
    meanings = ss.meanings(db, ids, locale)
    states = {r.word_id: r.status for r in db.query(models.UserVocabulary).filter(
        models.UserVocabulary.user_id == user.id, models.UserVocabulary.word_id.in_(ids or [0]))}
    levels = sent._level_map(db)
    return [{"id": i, "simplified": rows[i].simplified, "pinyin": rows[i].pinyin, "meaning": meanings.get(i, ""),
             "hsk_level": levels.get(rows[i].hsk_level_id), "status": states.get(i, "new")}
            for i in ids if i in rows]


def _pet_cases(db: Session, topic: models.GrammarTopic) -> int:
    return db.query(models.PetTeacherCase).filter_by(grammar_topic_id=topic.id).count()


# --------------------------------------------------------------------------- the lesson
def _ai_key(topic: models.GrammarTopic, locale: str) -> str:
    return hashlib.sha256(f"grammar|v2|{locale}|{topic.title}".encode("utf-8")).hexdigest()


def cached_lesson(db: Session, topic: models.GrammarTopic, locale: str) -> dict | None:
    hit = db.query(models.AIExplanation).filter_by(key=_ai_key(topic, locale)).first()
    return hit.payload if hit else None


def lesson_for(db: Session, topic: models.GrammarTopic, locale: str) -> tuple[dict | None, str | None]:
    """(lesson in `locale`, source) -- source "authored" or "ai", or
    (None, None) when neither exists yet."""
    data = authored().get(topic.title)
    if data is not None:
        lesson = {k: _loc(v, locale) for k, v in data.items() if k != "topic"}
        if locale == "zh":
            _drop_translations(lesson)
        return lesson, "authored"
    cached = cached_lesson(db, topic, locale)
    return (cached, "ai") if cached else (None, None)


def _drop_translations(lesson: dict) -> None:
    """A Chinese interface explains in Chinese; a "translation" of a Chinese
    example into Chinese would only repeat it."""
    for key in ("examples", "negative", "questions", "dialogue"):
        for item in lesson.get(key) or []:
            if isinstance(item, dict):
                item["tr"] = None


def _lesson_texts(lesson: dict | None) -> list[str]:
    if not lesson:
        return []
    out = []
    for key in ("examples", "negative", "questions", "dialogue"):
        out += [i["zh"] for i in lesson.get(key) or [] if isinstance(i, dict) and i.get("zh")]
    for s in lesson.get("structure") or []:
        if s.get("zh"):
            out.append(s["zh"])
    for m in lesson.get("mistakes") or []:
        out += [m.get("wrong") or "", m.get("right") or ""]
    return [t for t in out if t]


def page(db: Session, user: models.User, topic_id: int, locale: str) -> dict:
    topic = db.get(models.GrammarTopic, topic_id)
    if topic is None:
        raise GrammarError(404, "Grammar point not found")
    trs = load_translations(db, "grammar_topic", [str(topic.id)], locale)
    blocks = example_blocks(topic)
    lesson, source = lesson_for(db, topic, locale)
    texts = [b["zh"] for b in blocks if b["kind"] == "sentence"] + _lesson_texts(lesson)
    annotated = annotate(db, list(dict.fromkeys(texts)), locale)
    for b in blocks:
        if b["kind"] == "sentence":
            b.update(annotated.get(b["zh"], {}))
    if lesson:
        _attach_pinyin(lesson, annotated)
    similar_titles = [s.get("topic") for s in (lesson or {}).get("similar") or [] if s.get("topic")]
    if similar_titles:
        ids = {}
        for r in db.query(models.GrammarTopic).filter(models.GrammarTopic.title.in_(similar_titles)).order_by(models.GrammarTopic.id):
            ids.setdefault(r.title, r.id)
        for item in lesson["similar"]:
            item["topic_id"] = ids.get(item.get("topic"))
    return {
        "id": topic.id,
        "title": tr(trs, topic.id, "title", topic.title),
        "syllabus_title": topic.title,
        "pattern": topic.pattern,
        "category": tr(trs, topic.id, "category", topic.category),
        "hsk_level": _level_of(db, topic),
        "explanation": tr(trs, topic.id, "explanation", topic.explanation),
        "examples": blocks,
        "lesson": lesson,
        "lesson_source": source,
        # An AI lesson can be asked for when none exists yet; the page shows
        # the curriculum data meanwhile.
        "can_generate": lesson is None,
        "progress": _progress(db, user, topic),
        "related": related(db, topic, locale, similar_titles),
        "vocabulary": _vocabulary(db, user, annotated, (lesson or {}).get("vocabulary") or [], locale),
        "pet_teacher_cases": _pet_cases(db, topic),
    }


def _attach_pinyin(lesson: dict, annotated: dict[str, dict]) -> None:
    for key in ("examples", "negative", "questions", "dialogue", "structure"):
        for item in lesson.get(key) or []:
            if isinstance(item, dict) and item.get("zh") in annotated:
                item["pinyin"] = annotated[item["zh"]]["pinyin"]
                if key == "examples":
                    item["words"] = annotated[item["zh"]]["words"]
    for m in lesson.get("mistakes") or []:
        if m.get("right") in annotated:
            m["right_pinyin"] = annotated[m["right"]]["pinyin"]


# --------------------------------------------------------------------------- AI generation
_ai_calls: dict[tuple[str, int], list[float]] = {}


def _allowed(kind: str, user_id: int, per_hour: int) -> bool:
    now = time.monotonic()
    calls = [t for t in _ai_calls.get((kind, user_id), []) if now - t < 3600]
    _ai_calls[(kind, user_id)] = calls
    if len(calls) >= per_hour:
        return False
    calls.append(now)
    return True


def validate_ai_lesson(data) -> dict | None:
    """Keep only well-formed parts of a model's lesson. A Chinese example
    that the rules recognise as a known learner error is dropped, as is a
    "right" sentence in a mistake pair that is itself wrong; a lesson with
    no explanation and no examples left is no lesson."""
    if not isinstance(data, dict):
        return None

    def text(v, limit=900):
        return v.strip()[:limit] if isinstance(v, str) and v.strip() else None

    def zh_ok(v):
        return isinstance(v, str) and _CJK.search(v) and len(v) <= 80 and not [
            i for i in sentence_check.detect(v) if i["severity"] == "error"]

    def texts(v, n=6):
        # Models sometimes return one string where a list of paragraphs or
        # points was asked for; split it instead of losing the section.
        if isinstance(v, str):
            v = [p for p in re.split(r"\n+", v) if p.strip()]
        if not isinstance(v, list):
            return []
        return [t for t in (text(x, 600) for x in v[:n]) if t]

    def zh_items(v, n=8, extra=()):
        out = []
        for it in (v or [])[:n] if isinstance(v, list) else []:
            if isinstance(it, dict) and zh_ok(it.get("zh")):
                item = {"zh": it["zh"].strip(), "tr": text(it.get("tr"), 300)}
                for k in extra:
                    item[k] = text(it.get(k), 300)
                out.append(item)
        return out

    lesson = {
        "name": text(data.get("name"), 120),
        "summary": text(data.get("summary"), 400),
        "structure": [{"formula": text(s.get("formula"), 160), "zh": s["zh"].strip() if zh_ok(s.get("zh")) else None}
                      for s in (data.get("structure") or [])[:4] if isinstance(s, dict) and text(s.get("formula"), 160)],
        "when_to_use": texts(data.get("when_to_use")),
        "when_not": texts(data.get("when_not")),
        "explanation": texts(data.get("explanation"), 4),
        "deeper": texts(data.get("deeper"), 3),
        "examples": zh_items(data.get("examples"), 8, ("note",)),
        "negative": zh_items(data.get("negative"), 3),
        "questions": zh_items(data.get("questions"), 3),
        "mistakes": [],
        "similar": [],
        "dialogue": [],
        "register": text(data.get("register"), 400),
        "vocabulary": [],
        "exercises": [],
    }
    for m in (data.get("mistakes") or [])[:5] if isinstance(data.get("mistakes"), list) else []:
        if (isinstance(m, dict) and isinstance(m.get("wrong"), str) and _CJK.search(m["wrong"]) and zh_ok(m.get("right"))
                and sentence_check.normalize(m["wrong"]) != sentence_check.normalize(m["right"]) and text(m.get("why"))):
            lesson["mistakes"].append({"wrong": m["wrong"].strip()[:80], "right": m["right"].strip(), "why": text(m["why"], 400)})
    for s in (data.get("similar") or [])[:4] if isinstance(data.get("similar"), list) else []:
        if isinstance(s, dict) and text(s.get("pattern"), 80) and text(s.get("difference")):
            lesson["similar"].append({"pattern": text(s["pattern"], 80), "difference": text(s["difference"], 400)})
    for d in (data.get("dialogue") or [])[:6] if isinstance(data.get("dialogue"), list) else []:
        if isinstance(d, dict) and zh_ok(d.get("zh")):
            lesson["dialogue"].append({"speaker": "A" if d.get("speaker") != "B" else "B",
                                       "zh": d["zh"].strip(), "tr": text(d.get("tr"), 300)})
    for e in (data.get("exercises") or [])[:4] if isinstance(data.get("exercises"), list) else []:
        if not isinstance(e, dict) or not text(e.get("prompt"), 300):
            continue
        if e.get("type") == "choose" and isinstance(e.get("options"), list) and 2 <= len(e["options"]) <= 4:
            opts = [o.strip() for o in e["options"] if isinstance(o, str) and _CJK.search(o)]
            ans = e.get("answer")
            if len(opts) == len(e["options"]) and isinstance(ans, int) and 0 <= ans < len(opts) and zh_ok(opts[ans]):
                lesson["exercises"].append({"type": "choose", "prompt": text(e["prompt"], 300), "options": opts,
                                            "answer": ans, "why": text(e.get("why"), 400)})
        elif e.get("type") == "write" and zh_ok(e.get("answer")):
            lesson["exercises"].append({"type": "write", "prompt": text(e["prompt"], 300), "answer": e["answer"].strip()})
    vocab = data.get("vocabulary")
    if isinstance(vocab, list):
        lesson["vocabulary"] = [v.strip() for v in vocab[:10] if isinstance(v, str) and _CJK.search(v) and len(v) <= 6]
    if not (lesson["explanation"] or lesson["summary"]) or not lesson["examples"]:
        return None
    return lesson


def generate(db: Session, user: models.User, topic_id: int, locale: str) -> dict:
    """Make the AI lesson for a topic that has neither an authored nor a
    cached one, cache it, and return the whole page."""
    from app.services import ai_client

    topic = db.get(models.GrammarTopic, topic_id)
    if topic is None:
        raise GrammarError(404, "Grammar point not found")
    lesson, _source = lesson_for(db, topic, locale)
    if lesson is None:
        if not _allowed("lesson", user.id, AI_PER_HOUR):
            raise GrammarError(429, "You've asked for many new explanations this hour — try again a bit later")
        examples = [b["zh"] for b in example_blocks(topic) if b["kind"] == "sentence"][:8]
        data = ai_client.grammar_lesson(topic.title, topic.pattern or "", examples, locale, _level_of(db, topic))
        lesson = validate_ai_lesson(data)
        if lesson is None:
            raise GrammarError(503, "A full explanation isn't available right now — the examples below still work")
        if locale == "zh":
            _drop_translations(lesson)
        db.add(models.AIExplanation(key=_ai_key(topic, locale), kind="grammar", locale=locale,
                                    text=topic.title[:2000], payload=lesson))
        try:
            db.commit()
        except IntegrityError:  # another learner's request cached it first
            db.rollback()
    return page(db, user, topic_id, locale)


# --------------------------------------------------------------------------- "try it"
def check_answer(db: Session, user: models.User, topic_id: int, answer: str, exercise: int | None,
                 locale: str) -> dict:
    """Check a sentence the learner wrote on a grammar page. With an
    exercise index the lesson's own answer is the target; without one it is
    "write your own sentence with this pattern". Never touches mastery --
    graded progress comes only from practice rounds."""
    from app.services import ai_client

    topic = db.get(models.GrammarTopic, topic_id)
    if topic is None:
        raise GrammarError(404, "Grammar point not found")
    answer = (answer or "").strip()
    if not _CJK.search(answer):
        raise GrammarError(422, "Write the sentence in Chinese characters")
    expected = None
    if exercise is not None:
        lesson, _ = lesson_for(db, topic, locale)
        items = (lesson or {}).get("exercises") or []
        if not 0 <= exercise < len(items) or items[exercise].get("type") != "write":
            raise GrammarError(404, "Exercise not found")
        expected = items[exercise]["answer"]
    result = sentence_check.check(answer, expected)
    uses = sent.uses_grammar(topic.title, answer) if any(t == topic.title for _p, t, _u in sent.GRAMMAR_RULES) else None
    feedback = ""
    if not result["final"] and _allowed("check", user.id, CHECKS_PER_HOUR):
        task = (f"Write a Chinese sentence that uses the grammar point {topic.title} (pattern: {topic.pattern})."
                if expected is None else f"Exercise on the grammar point {topic.title}.")
        judged = ai_client.judge_sentence(answer, expected or "(any correct sentence using the pattern)", task, locale)
        if judged:
            result["source"] = "ai"
            result["category"] = judged["category"]
            result["verdict"] = {"correct": "correct", "alternative": "acceptable",
                                 "typo": "close"}.get(judged["category"], "incorrect")
            feedback = judged["feedback"]
    return {
        "verdict": result["verdict"], "category": result["category"], "source": result["source"],
        "issues": [i["code"] for i in result["issues"]], "feedback": feedback,
        "uses_pattern": uses, "expected": expected,
    }
