"""Tone Coach: say a word, see your pitch, learn which tone you produced.

What it really measures -- and what it doesn't. Every other speaking
feature hears the learner through the browser's speech recognizer, which
returns TEXT: a recognizer picks the right character from context even when
the tone was wrong, so text can never show a tone. Tones are pitch, and
pitch can be measured. The browser records the learner and tracks the
fundamental frequency (YIN, frontend/src/pitch.js) frame by frame; only
those numbers -- no audio -- are sent here. This module turns the contour
into a tone per syllable by its SHAPE:

  1  high and level         2  rising         3  dipping (or low, in a pair)
  4  falling                 neutral tones are not judged

It is an estimate of pitch movement only: consonants and vowels are not
assessed, and a noisy room or a shaky microphone can make a syllable
"unclear" -- reported as unclear (try again), never counted as a mistake.

The expected tones are the dictionary tones with the tone changes Mandarin
speakers really make (3+3 -> 2+3; 不 before a 4th tone -> 2; 一 before a 4th
tone -> 2, before 1/2/3 -> 4), so a learner who says 你好 correctly as
ní hǎo is right.

Attempts are stored (tone_attempts) and drive the coach: per-tone accuracy,
which tone the learner produces instead of which, and the next item,
chosen from their own level's words with the tone they miss most. A
missed word goes to the mistake notebook as a tone mistake; Learning DNA
(tones, speaking) moves by the verdict -- never by chance.
"""

from __future__ import annotations

import math
import random
import re
from datetime import datetime, timedelta
from statistics import median

from sqlalchemy.orm import Session

from app import models
from app.services.activity import log_activity
from app.services.dna import bump_skill
from app.services.gamification import ensure_user_skills, record_mistake, reinforce_mistake, user_rank
from app.services.hsk_band import resolve_level_filter
from app.services.localization import load_translations, tr
from app.services.recall import pinyin_key

HOP_MS = 10
MAX_FRAMES = 500           # 5 s
MIN_SEGMENT = 8            # frames (80 ms) of voiced pitch to judge a syllable
GAP = 4                    # unvoiced frames (40 ms) that separate two syllables
STATS_DAYS = 30
XP_PER_CORRECT = 1
_CJK = re.compile(r"[㐀-鿿]")


class ToneError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


# --------------------------------------------------------------------------- expected tones

def syllable_tones(simplified: str, pinyin: str) -> list[int] | None:
    """Dictionary tone per character (5 = neutral), or None when the
    pinyin can't be aligned to the characters. Pinyin in the curriculum has
    no spaces ("xǐhuan"), so a missing tone mark is taken as a neutral
    final syllable -- the only place one appears in a two-syllable word
    (喜欢 xǐhuan, 朋友 péngyou, 妈妈 māma)."""
    chars = _CJK.findall(simplified or "")
    if not chars or len(chars) != len(simplified):
        return None
    _letters, tones, _given = pinyin_key(pinyin or "")
    tones = list(tones)
    if len(tones) == len(chars):
        return tones
    if len(tones) == 1 and len(chars) == 2:
        return tones + [5]
    return None


def surface_tones(chars: str, tones: list[int]) -> list[int]:
    """The tones a native speaker actually says (tone sandhi)."""
    out = list(tones)
    for i in range(len(out) - 1):
        nxt = out[i + 1]
        if out[i] == 3 and nxt == 3:
            out[i] = 2
        elif chars[i] == "不" and nxt == 4:
            out[i] = 2
        elif chars[i] == "一" and tones[i] == 1:
            out[i] = 2 if nxt == 4 else 4 if nxt in (1, 2, 3) else 1
    return out


# --------------------------------------------------------------------------- the contour

def _semitones(f0: list[float]) -> list[float | None]:
    voiced = [f for f in f0 if f and f > 0]
    if not voiced:
        return [None] * len(f0)
    ref = median(voiced)
    st = [12 * math.log2(f / ref) if f and f > 0 else None for f in f0]
    # Octave errors of the tracker: a frame far from its neighbours is dropped.
    out = list(st)
    for i, v in enumerate(st):
        if v is None:
            continue
        near = [x for x in st[max(0, i - 3): i + 4] if x is not None]
        if abs(v - median(near)) > 6:
            out[i] = None
    return out


def _runs(st: list[float | None]) -> list[tuple[int, int]]:
    """Voiced stretches [start, end) separated by at least GAP unvoiced frames."""
    runs, start, gap = [], None, 0
    for i, v in enumerate(st + [None] * GAP):
        if v is not None:
            if start is None:
                start = i
            gap, last = 0, i
        elif start is not None:
            gap += 1
            if gap >= GAP:
                runs.append((start, last + 1))
                start, gap = None, 0
    return [r for r in runs if r[1] - r[0] >= MIN_SEGMENT]


def _split(run: tuple[int, int], rms: list[float] | None, n: int) -> list[tuple[int, int]]:
    """One voiced stretch holding n syllables (spoken without a pause):
    split where the voice is quietest in the middle part."""
    a, b = run
    if n == 1:
        return [run]
    lo, hi = a + int((b - a) * 0.3), a + int((b - a) * 0.7)
    cut = (a + b) // 2
    if rms and hi > lo:
        cut = min(range(lo, hi), key=lambda i: rms[i] if i < len(rms) else 1e9)
    return [(a, cut), (cut, b)]


def segments(st: list[float | None], rms: list[float] | None, n: int) -> list[tuple[int, int]] | None:
    runs = _runs(st)
    if not runs:
        return None
    if len(runs) >= n:
        # The n longest stretches, in time order (stray noises are short).
        return sorted(sorted(runs, key=lambda r: r[0] - r[1])[:n])
    if n == 2 and len(runs) == 1:
        return _split(runs[0], rms, 2)
    return None


def _shape(st: list[float | None], seg: tuple[int, int]) -> dict | None:
    vals = [v for v in st[seg[0]:seg[1]] if v is not None]
    if len(vals) < MIN_SEGMENT:
        return None
    trim = max(1, len(vals) // 10)
    vals = vals[trim:-trim] or vals
    # Light smoothing (median of 5): the tracker's frame-to-frame jitter is
    # not intonation.
    sm = [median(vals[max(0, i - 2): i + 3]) for i in range(len(vals))]
    k = max(1, len(sm) // 5)
    start, end = sum(sm[:k]) / k, sum(sm[-k:]) / k
    lo, hi = min(sm), max(sm)
    return {"start": start, "end": end, "min": lo, "max": hi, "mean": sum(sm) / len(sm),
            "min_pos": sm.index(lo) / max(1, len(sm) - 1), "range": hi - lo, "slope": end - start}


def classify(shape: dict, final: bool = True, other_mean: float | None = None, expected: int | None = None) -> int | None:
    """A tone (1-4) from one syllable's pitch shape, or None when it is not
    clear enough to say. `other_mean` is the other syllable's mean pitch in a
    two-syllable word: a third tone that is not last is a LOW tone (half
    third, it doesn't rise), recognisable only against its neighbour."""
    s = shape
    dip = s["start"] - s["min"] >= 1.0 and s["end"] - s["min"] >= 1.0 and 0.2 <= s["min_pos"] <= 0.8
    if dip and s["range"] >= 2.0:
        return 3
    if s["slope"] >= 2.0 and s["min_pos"] <= 0.5:
        return 2
    low = other_mean is not None and s["mean"] <= other_mean - 1.5
    if not final and expected == 3 and low and s["slope"] <= 1.0:
        return 3  # half third: low, level or slightly falling
    if s["slope"] <= -2.5:
        return 4
    if s["range"] < 2.0 and abs(s["slope"]) < 1.5:
        return 3 if (low and not final) else 1
    return None


def analyse(f0: list[float], rms: list[float] | None, expected: list[int]) -> dict:
    """Per syllable: the tone heard (or None), and the normalised curve for
    drawing. `expected` holds surface tones (5 = neutral, not judged)."""
    st = _semitones(f0)
    segs = segments(st, rms, len(expected))
    out = {"syllables": [], "curve": [round(v, 2) if v is not None else None for v in st[::2]]}
    if segs is None:
        out["syllables"] = [{"expected": e, "heard": None, "judged": e != 5} for e in expected]
        return out
    shapes = [_shape(st, s) for s in segs]
    for i, (e, shape) in enumerate(zip(expected, shapes)):
        if e == 5:
            out["syllables"].append({"expected": 5, "heard": None, "judged": False})
            continue
        other = [x["mean"] for j, x in enumerate(shapes) if j != i and x is not None]
        heard = classify(shape, final=i == len(expected) - 1, other_mean=other[0] if other else None,
                         expected=e) if shape else None
        out["syllables"].append({"expected": e, "heard": heard, "judged": True,
                                 "span": [segs[i][0] // 2, segs[i][1] // 2]})
    return out


# --------------------------------------------------------------------------- items

def _card(db: Session, item_type: str, row, locale: str) -> dict | None:
    zh = row.simplified if item_type == "vocab" else row.character
    tones = syllable_tones(zh, row.pinyin)
    if not tones or len(tones) > 2 or all(t == 5 for t in tones):
        return None
    content, field = ("vocab_word", "meanings") if item_type == "vocab" else ("hanzi", "meaning")
    meaning = tr(load_translations(db, content, [str(row.id)], locale), row.id, field, getattr(row, field))
    if locale == "zh" and (meaning or "").strip() == zh:
        meaning = ""
    surface = surface_tones(zh, tones)
    return {"item_type": item_type, "item_id": row.id, "zh": zh, "pinyin": row.pinyin, "meaning": meaning or "",
            "tones": tones, "expected": surface, "sandhi": surface != tones}


def item(db: Session, user: models.User, item_type: str, item_id: int, locale: str) -> dict:
    model = {"vocab": models.VocabularyWord, "hanzi": models.Hanzi}.get(item_type)
    row = db.get(model, item_id) if model else None
    card = _card(db, item_type, row, locale) if row is not None else None
    if card is None:
        raise ToneError(404, "This word can't be practised here")
    return card


def _recent(db: Session, user: models.User, days: int = STATS_DAYS) -> list[models.ToneAttempt]:
    since = datetime.utcnow() - timedelta(days=days)
    return (db.query(models.ToneAttempt).filter(models.ToneAttempt.user_id == user.id,
                                                models.ToneAttempt.created_at >= since)
            .order_by(models.ToneAttempt.created_at).all())


def stats(db: Session, user: models.User) -> dict:
    """Per expected tone: syllables judged and heard right (last 30 days),
    and the most frequent confusions (said X when Y was expected). Counts
    only -- no score beyond what was measured; unclear syllables are
    counted separately."""
    per = {t: {"tone": t, "judged": 0, "correct": 0} for t in (1, 2, 3, 4)}
    confused: dict[tuple[int, int], int] = {}
    unclear = attempts = 0
    for a in _recent(db, user):
        attempts += 1
        for s in a.syllables or []:
            if not s.get("judged"):
                continue
            if s.get("heard") is None:
                unclear += 1
                continue
            p = per[s["expected"]]
            p["judged"] += 1
            if s["heard"] == s["expected"]:
                p["correct"] += 1
            else:
                key = (s["expected"], s["heard"])
                confused[key] = confused.get(key, 0) + 1
    tones = list(per.values())
    for p in tones:
        p["accuracy"] = round(p["correct"] / p["judged"] * 100) if p["judged"] else None
    top = sorted(confused.items(), key=lambda kv: -kv[1])[:3]
    return {"days": STATS_DAYS, "attempts": attempts, "unclear": unclear, "tones": tones,
            "confusions": [{"expected": e, "heard": h, "count": n} for (e, h), n in top]}


def weakest_tone(st: dict) -> int | None:
    """The tone to practise: the lowest accuracy among tones with at least
    3 judged syllables; None until there is that much evidence."""
    known = [p for p in st["tones"] if p["judged"] >= 3]
    if not known:
        return None
    worst = min(known, key=lambda p: (p["accuracy"], -p["judged"]))
    return worst["tone"] if worst["accuracy"] < 90 else None


def next_item(db: Session, user: models.User, mode: str, locale: str, rng: random.Random | None = None) -> dict:
    """A word (mode "pair": two syllables) or character ("single") from the
    learner's own HSK level, favouring words they are learning, and the
    tone they miss most when there is evidence of one."""
    rng = rng or random.Random()
    level, _ = user_rank(db, user)
    level = max(1, min(level, 7))
    focus = weakest_tone(stats(db, user))
    if mode == "single":
        model, id_field, item_type = models.Hanzi, models.Hanzi.hsk_level_id, "hanzi"
        level_id, subset = resolve_level_filter(db, model, id_field, level)
        q = db.query(model).filter(id_field == (level_id or 0))
    else:
        model, id_field, item_type = models.VocabularyWord, models.VocabularyWord.hsk_level_id, "vocab"
        level_id, subset = resolve_level_filter(db, model, id_field, level)
        q = db.query(model).filter(id_field == (level_id or 0))
    if subset is not None:
        q = q.filter(model.id.in_(subset or [0]))
    rows = q.all()
    want = 2 if mode == "pair" else 1
    rows = [r for r in rows if len(r.simplified if item_type == "vocab" else r.character) == want]
    rng.shuffle(rows)
    learning = set()
    if item_type == "vocab":
        learning = {r.word_id for r in db.query(models.UserVocabulary.word_id).filter(
            models.UserVocabulary.user_id == user.id, models.UserVocabulary.status.in_(("learning", "reviewing")))}
    # Words being learned first, then the rest; within each, ones with the
    # focus tone first. Recently practised items are skipped.
    recent = {(a.item_type, a.item_id) for a in _recent(db, user, days=1)[-12:]}
    best = None
    for r in sorted(rows, key=lambda r: r.id not in learning):
        if (item_type, r.id) in recent:
            continue
        card = _card(db, item_type, r, locale)
        if card is None:
            continue
        if focus is None or focus in card["expected"]:
            card["focus"] = focus
            return card
        best = best or card
    if best is None:
        raise ToneError(404, "No words to practise at this level")
    best["focus"] = focus
    return best


# --------------------------------------------------------------------------- an attempt

def attempt(db: Session, user: models.User, item_type: str, item_id: int, f0: list[float], rms: list[float] | None,
            locale: str) -> dict:
    if not f0 or len(f0) > MAX_FRAMES:
        raise ToneError(422, "The recording should be between a moment and 5 seconds long")
    if rms is not None and len(rms) != len(f0):
        raise ToneError(422, "Pitch and loudness frames don't match")
    if any((not isinstance(f, (int, float))) or f < 0 or f > 1000 for f in f0):
        raise ToneError(422, "Pitch values out of range")
    card = item(db, user, item_type, item_id, locale)
    result = analyse(list(map(float, f0)), list(map(float, rms)) if rms else None, card["expected"])
    judged = [s for s in result["syllables"] if s["judged"]]
    if not any(f for f in f0):
        verdict = "silent"
    elif any(s["heard"] is None for s in judged):
        verdict = "unclear"
    else:
        verdict = "correct" if all(s["heard"] == s["expected"] for s in judged) else "wrong"

    if verdict != "silent":
        db.add(models.ToneAttempt(user_id=user.id, item_type=item_type, item_id=item_id, text=card["zh"],
                                  expected="-".join(map(str, card["expected"])), verdict=verdict,
                                  syllables=result["syllables"]))
    if verdict in ("correct", "wrong"):
        ensure_user_skills(db, user)
        ok = verdict == "correct"
        bump_skill(user, "tones", 1.5 if ok else -0.3)
        bump_skill(user, "speaking", 0.5 if ok else 0.0)
        ref = card["zh"]
        mistake_type = "tone" if item_type == "vocab" else "hanzi"
        if ok:
            reinforce_mistake(db, user, mistake_type, ref)
            user.total_xp += XP_PER_CORRECT
        else:
            heard = "-".join(str(s["heard"]) if s["judged"] else "·" for s in result["syllables"])
            record_mistake(db, user, mistake_type, ref, question_text=f"{card['zh']} ({card['pinyin']})",
                           answer_given=f"tones {heard}",
                           correct_answer=f"tones {'-'.join(map(str, card['expected']))}")
        log_activity(db, user, "tone_attempt")
    db.commit()
    return {"verdict": verdict, "item": card, **result,
            "xp_gained": XP_PER_CORRECT if verdict == "correct" else 0}
