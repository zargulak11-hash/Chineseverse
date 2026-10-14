"""Tone Coach (services/tone_coach.py): tones are judged from the SHAPE of
the pitch contour the browser measured. Synthetic contours of each tone
(semitone paths around a 200 Hz voice) pin the classifier down; tone
changes decide what is expected; attempts drive stats, the notebook, DNA
and the next item."""

import math

import pytest

from app import models
from app.database import SessionLocal
from app.services import tone_coach as tc
from helpers import expect, register, unique_name

BASE = 200.0


def path(points: list[float], frames: int = 40) -> list[float]:
    """Piecewise-linear semitone path through `points`, as Hz per frame."""
    out = []
    for i in range(frames):
        x = i / (frames - 1) * (len(points) - 1)
        j = min(int(x), len(points) - 2)
        st = points[j] + (points[j + 1] - points[j]) * (x - j)
        out.append(BASE * 2 ** (st / 12))
    return out


GAP = [0.0] * 6
T1, T2, T3, T4 = [0, 0, 0.2], [-2, -1.5, 3], [0, -4, 1], [3, 0, -4]


def heard(f0, expected, rms=None):
    return [s["heard"] for s in tc.analyse(f0, rms, expected)["syllables"]]


@pytest.mark.parametrize("shape, tone", [(T1, 1), (T2, 2), (T3, 3), (T4, 4)])
def test_each_tone_shape_is_recognised(shape, tone):
    assert heard(path(shape), [tone]) == [tone]


def test_a_flat_contour_is_not_heard_as_a_rise_or_fall():
    assert heard(path(T1), [2]) == [1]
    assert heard(path(T4), [1]) == [4]


def test_two_syllables_with_a_pause():
    assert heard(path(T2) + GAP + path(T4), [2, 4]) == [2, 4]
    assert heard(path(T4) + GAP + path(T1), [4, 1]) == [4, 1]


def test_two_syllables_without_a_pause_split_at_the_quietest_point():
    f0 = path(T4, 30) + path([2, 2, 2.2], 30)
    rms = [0.3] * 27 + [0.05] * 6 + [0.3] * 27
    assert heard(f0, [4, 1], rms) == [4, 1]


def test_a_half_third_tone_is_low_and_does_not_rise():
    # 很高 hěn gāo: the 3rd tone before a 1st is low and level-to-falling.
    f0 = path([-4, -4.5, -5]) + GAP + path([2, 2, 2.1])
    assert heard(f0, [3, 1]) == [3, 1]
    # The same low level syllable said LAST is not a third tone.
    assert heard(path([2, 2, 2.1]) + GAP + path([-4, -4.5, -5]), [1, 1])[0] == 1


def test_a_neutral_tone_is_not_judged():
    s = tc.analyse(path(T1) + GAP + path([-2, -3, -3], 15), None, [1, 5])["syllables"]
    assert s[0]["heard"] == 1 and s[1]["judged"] is False and s[1]["heard"] is None


def test_shaky_pitch_is_unclear_not_wrong():
    shaky = [BASE * 2 ** ((2.5 if i % 2 else -2.5) / 12) for i in range(40)]
    assert heard(shaky, [2]) == [None]
    assert heard([0.0] * 40, [1]) == [None]
    assert heard(path(T2, 5), [2]) == [None]  # too short to judge


def test_octave_errors_of_the_tracker_are_ignored():
    f0 = path(T4)
    f0[20] *= 2  # one frame an octave too high
    assert heard(f0, [4]) == [4]


@pytest.mark.parametrize("zh, py, base, surface", [
    ("你好", "nǐhǎo", [3, 3], [2, 3]),
    ("喜欢", "xǐhuan", [3, 5], [3, 5]),
    ("不是", "bùshì", [4, 4], [2, 4]),
    ("不好", "bùhǎo", [4, 3], [4, 3]),
    ("一天", "yītiān", [1, 1], [4, 1]),
    ("一样", "yīyàng", [1, 4], [2, 4]),
    ("好", "hǎo", [3], [3]),
])
def test_dictionary_tones_and_the_tone_changes_speakers_make(zh, py, base, surface):
    assert tc.syllable_tones(zh, py) == base
    assert tc.surface_tones(zh, base) == surface


def test_unalignable_pinyin_is_not_used():
    assert tc.syllable_tones("中国人", "zhōngguó") is None
    assert tc.syllable_tones("OK", "ok") is None


# --------------------------------------------------------------------------- through the API

@pytest.fixture
def learner(client):
    return register(client, unique_name("toner"))


def word_id(zh):
    with SessionLocal() as db:
        return db.query(models.VocabularyWord).filter_by(simplified=zh).order_by(models.VocabularyWord.id).first().id


def attempt(client, h, wid, f0, rms=None, status=200):
    return expect(client, "post", "/api/tones/attempt", status, headers=h,
                  json={"item_type": "vocab", "item_id": wid, "f0": f0, "rms": rms})


def three_three_word():
    """A curriculum word of two 3rd tones (可以, 水果...): said 2-3."""
    with SessionLocal() as db:
        lvl = db.query(models.HSKLevel).filter_by(level=1).one()
        for w in db.query(models.VocabularyWord).filter_by(hsk_level_id=lvl.id).order_by(models.VocabularyWord.id):
            if len(w.simplified) == 2 and tc.syllable_tones(w.simplified, w.pinyin) == [3, 3]:
                return w.id, w.simplified
    pytest.skip("no 3+3 word at HSK 1")


def test_saying_a_three_three_word_right_counts_and_wrong_goes_to_the_notebook(client, learner):
    uid, h = learner
    nihao, text = three_three_word()
    with SessionLocal() as db:
        xp0 = db.get(models.User, uid).total_xp
    ok = attempt(client, h, nihao, path(T2) + GAP + path(T3))
    assert ok["verdict"] == "correct" and ok["item"]["expected"] == [2, 3] and ok["item"]["sandhi"] is True
    assert [s["heard"] for s in ok["syllables"]] == [2, 3] and ok["xp_gained"] == 1 and ok["curve"]
    bad = attempt(client, h, nihao, path(T4) + GAP + path(T4))
    assert bad["verdict"] == "wrong" and [s["heard"] for s in bad["syllables"]] == [4, 4]
    with SessionLocal() as db:
        assert db.get(models.User, uid).total_xp == xp0 + 1
        assert db.query(models.ToneAttempt).filter_by(user_id=uid).count() == 2
    m = next(m for m in expect(client, "get", "/api/mistakes", 200, headers=h) if m["reference"] == text)
    assert m["mistake_type"] == "tone" and m["answer_given"] == "tones 4-4" and m["correct_answer"] == "tones 2-3"


def test_unclear_and_silent_attempts_are_never_mistakes(client, learner):
    uid, h = learner
    hao = word_id("好")
    shaky = [BASE * 2 ** ((2.5 if i % 2 else -2.5) / 12) for i in range(40)]
    assert attempt(client, h, hao, shaky)["verdict"] == "unclear"
    assert attempt(client, h, hao, [0.0] * 30)["verdict"] == "silent"
    assert not any(m["reference"] == "好" for m in expect(client, "get", "/api/mistakes", 200, headers=h))
    st = expect(client, "get", "/api/tones/stats", 200, headers=h)
    assert st["attempts"] == 1 and st["unclear"] == 1 and all(t["judged"] == 0 for t in st["tones"])


def test_stats_and_the_next_item_follow_the_learners_weak_tone(client, learner):
    _, h = learner
    hao = word_id("好")
    for _ in range(3):
        attempt(client, h, hao, path(T4))  # a 3rd tone said as a 4th, three times
    attempt(client, h, word_id("是"), path(T4))  # a 4th tone said right
    st = expect(client, "get", "/api/tones/stats", 200, headers=h)
    t3 = next(t for t in st["tones"] if t["tone"] == 3)
    assert (t3["judged"], t3["correct"], t3["accuracy"]) == (3, 0, 0)
    assert st["confusions"][0] == {"expected": 3, "heard": 4, "count": 3}
    nxt = expect(client, "get", "/api/tones/next?mode=pair", 200, headers=h)
    assert nxt["focus"] == 3 and 3 in nxt["expected"] and len(nxt["zh"]) == 2
    single = expect(client, "get", "/api/tones/next?mode=single", 200, headers=h)
    assert single["item_type"] == "hanzi" and len(single["zh"]) == 1


def test_attempts_are_validated(client, learner):
    _, h = learner
    hao = word_id("好")
    attempt(client, h, hao, [2000.0] * 20, status=422)
    attempt(client, h, hao, path(T3), rms=[0.1] * 3, status=422)
    attempt(client, h, hao, [100.0] * 600, status=422)
    expect(client, "post", "/api/tones/attempt", 422, headers=h,
           json={"item_type": "grammar", "item_id": 1, "f0": [100.0]})
    expect(client, "post", "/api/tones/attempt", 401, json={"item_type": "vocab", "item_id": hao, "f0": [100.0]})
    with SessionLocal() as db:
        long_word = db.query(models.VocabularyWord).filter(models.VocabularyWord.simplified == "中国人").first()
    if long_word:
        expect(client, "get", f"/api/tones/item/vocab/{long_word.id}", 404, headers=h)
