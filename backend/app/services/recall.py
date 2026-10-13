"""Active recall: the learner types the answer instead of picking it.

Every other practice question offers four options, which tests recognition:
a learner who has seen 喜欢 ten times can pick it out of a line-up long
before they could produce it. Recall is the harder, more honest evidence,
so once a word or character is past "learning" (status reviewing/mastered)
its rounds ask for it from memory:

  type_word    the meaning in the learner's language -> type the word,
               as characters or as pinyin with tones
  type_pinyin  a character -> type its reading with tones

and "mastered" requires at least one such recall (services/srs.py).

Grading here is exact where exactness is the point and says WHY when an
answer is wrong -- but only what the typed text really shows:

  exact          the word / the reading itself
  alternative    another curriculum word that shares a gloss with the asked
                 meaning (typed 爱 for "to be fond of"): also right, and the
                 answer the question had in mind is shown next to it
  tone           the right syllables with different tones
  missing_tones  the right syllables with no tone at all; asked once more
                 before it counts, since a phone keyboard may make tones a
                 chore and the syllables were really recalled
  other_word     exactly another word of the curriculum -- a real mix-up,
                 stored like a wrong pick so the mix-up notebook sees it
  unknown        nothing typed ("I don't know")
  wrong          anything else

Pinyin is compared without segmenting syllables: the letters (tone marks
removed, ü written v) must be equal, and the tones -- marks or digits 1-4,
in order -- must be equal. Neutral-tone syllables carry no mark in the
curriculum, and a typed 5 or 0 counts the same, so "ma1ma", "ma1ma5" and
"māma" are all 妈妈. Spaces, apostrophes and capitals don't matter.
"""

from __future__ import annotations

import re
import unicodedata

_MARKED = {}
for base, marks in (("a", "āáǎà"), ("e", "ēéěè"), ("i", "īíǐì"), ("o", "ōóǒò"), ("u", "ūúǔù"), ("v", "ǖǘǚǜ")):
    for tone, ch in enumerate(marks, start=1):
        _MARKED[ch] = (base, tone)
_CJK = re.compile(r"[㐀-鿿]")
_GLOSS_SPLIT = re.compile(r"[;,，；/]")
_PAREN = re.compile(r"\([^)]*\)|（[^）]*）")
_GLOSS_LEAD = re.compile(r"^(?:to|a|an|the)\s+")

TYPED_TYPES = ("type_word", "type_pinyin")
RECALL_TYPE = {"vocab": "type_word", "hanzi": "type_pinyin"}
# Asked as this multiple-choice type when a mix-up made while typing is
# drilled (services/mixups.py): the drill puts both items on screen.
AS_CHOICE = {"type_word": "meaning_to_word", "type_pinyin": "char_to_pinyin"}
MAX_TYPED = 40


def pinyin_key(text: str) -> tuple[str, tuple[int, ...], bool]:
    """(letters, tones, any tone given). `letters` is lower-case a-z with ü
    as v; `tones` are the 1-4 tones in order; neutral tones are not listed."""
    text = unicodedata.normalize("NFC", (text or "").lower()).replace("u:", "v").replace("ü", "v")
    letters, tones, given = [], [], False
    for ch in text:
        if ch in _MARKED:
            base, tone = _MARKED[ch]
            letters.append(base)
            tones.append(tone)
            given = True
        elif "a" <= ch <= "z":
            letters.append(ch)
        elif ch in "1234":
            tones.append(int(ch))
            given = True
        elif ch in "05":
            given = True
    return "".join(letters), tuple(tones), given


def is_chinese(text: str) -> bool:
    return bool(_CJK.search(text or ""))


def hanzi_only(text: str) -> str:
    return "".join(_CJK.findall(text or ""))


def glosses(meanings: str | None) -> set[str]:
    """The separate senses of an English gloss, normalised for comparing
    two words' meanings ("to like; to be fond of" -> {"like", "be fond of"})."""
    out = set()
    for part in _GLOSS_SPLIT.split(_PAREN.sub("", meanings or "")):
        g = _GLOSS_LEAD.sub("", part.strip().lower()).strip(" .!?")
        if len(g) >= 2:
            out.add(g)
    return out


def tone_display(tones: tuple[int, ...]) -> str:
    return "-".join(str(t) for t in tones)


def check_pinyin(typed: str, expected: str) -> dict:
    """A typed reading against the expected one."""
    if not (typed or "").strip():
        return {"kind": "unknown", "correct": False}
    letters, tones, given = pinyin_key(typed)
    want_letters, want_tones, _ = pinyin_key(expected)
    if not letters or letters != want_letters:
        return {"kind": "wrong", "correct": False}
    if tones == want_tones:
        return {"kind": "exact", "correct": True}
    if not given and want_tones:
        return {"kind": "missing_tones", "correct": False}
    return {"kind": "tone", "correct": False,
            "tones_typed": tone_display(tones), "tones_expected": tone_display(want_tones)}


def check_word(typed: str, target, candidates: list) -> dict:
    """A typed word (characters or pinyin) against the asked word `target`.

    `candidates` are the other words of the same level, used to recognise an
    answer that is a real word rather than a slip: a synonym is accepted, a
    word with another meaning is a mix-up. Returns {"kind", "correct"} plus
    "other" (the word the learner produced) where there is one."""
    typed = (typed or "").strip()
    if not typed:
        return {"kind": "unknown", "correct": False}
    if is_chinese(typed):
        han = hanzi_only(typed)
        if han in (target.simplified, target.traditional):
            return {"kind": "exact", "correct": True}
        other = next((w for w in candidates if w.id != target.id and han in (w.simplified, w.traditional)), None)
        return _other(target, other)
    result = check_pinyin(typed, target.pinyin)
    if result["kind"] != "wrong":
        return result
    # The pinyin of exactly one other word of the level: the learner produced
    # that word. Several homophones -> no way to tell which one was meant.
    letters, tones, _ = pinyin_key(typed)
    same = [w for w in candidates if w.id != target.id and pinyin_key(w.pinyin)[:2] == (letters, tones)]
    return _other(target, same[0] if len(same) == 1 else None)


def _other(target, other) -> dict:
    if other is None:
        return {"kind": "wrong", "correct": False}
    if glosses(other.meanings) & glosses(target.meanings):
        return {"kind": "alternative", "correct": True, "other": other}
    return {"kind": "other_word", "correct": False, "other": other}
