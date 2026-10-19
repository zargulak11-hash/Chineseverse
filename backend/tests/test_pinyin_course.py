"""The pinyin foundation course (services/pinyin_course.py): every unit
teaches before it tests (explanation, examples, guided questions), its
checks are honest (the right option really is the syllable's part, tone or
spelling), a wrong answer says what differed, passing every unit completes
the journey's first step, and the beginner's tones round is now heard."""

import random

import pytest

from app import models
from app.database import SessionLocal
from app.services import pinyin_course as pc
from helpers import expect, register as register_only, unique_name


def register(client):
    uid, h = register_only(client, unique_name("py"))
    expect(client, "get", "/api/dashboard", 200, headers=h)  # creates skill rows
    return uid, h


def stored(sid):
    with SessionLocal() as db:
        return db.get(models.PracticeSession, sid).questions


def play(client, h, key, right=True):
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "pronunciation", "env": key})
    keys = stored(s["id"])
    results = []
    for q in s["questions"]:
        k = keys[q["index"]]
        choice = k["item_id"] if right else next(o["id"] for o in q["options"] if o["id"] != k["item_id"])
        results.append(expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h,
                              json={"index": q["index"], "choice_id": choice, "response_ms": 2500}))
    expect(client, "post", f"/api/practice/sessions/{s['id']}/complete", 200, headers=h)
    return s, keys, results


def test_pinyin_helpers():
    assert pc.tone_of("mā") == 1 and pc.tone_of("lǜ") == 4 and pc.tone_of("ma") == 0
    assert pc.split("shāng") == ("sh", "ang") and pc.split("ài") == ("", "ai") and pc.split("nǚ") == ("n", "ü")
    assert pc.plain("xué") == "xue"


def test_course_data_is_consistent():
    for zh, py, ini, fin in pc.SYLLABLES:
        assert pc.split(py) == (ini, fin), py
    for group in pc.INITIALS_1 + pc.INITIALS_2:
        finals = {pc.split(p)[1] for _, p in group}
        tones = {pc.tone_of(p) for _, p in group}
        assert len(finals) == 1 and len(tones) == 1, group  # only the initial differs
        assert len({pc.split(p)[0] for _, p in group}) == len(group)
    for group in pc.FINALS:
        assert len({pc.split(p)[0] for _, p in group}) == 1 and len({pc.split(p)[1] for _, p in group}) == len(group)
    for zh, parts, right, wrong, rule in pc.SPELLING:
        assert right not in wrong and len(set(wrong)) == len(wrong)
        assert rule in ("u_after_jqx", "u_after_nl", "y_w", "mark_a", "mark_oe", "mark_iu_ui")


def test_the_course_teaches_before_it_tests_in_every_language(client):
    uid, h = register(client)
    data = expect(client, "get", "/api/sound-world/pinyin-course", 200, headers=h)
    assert [u["key"] for u in data["units"]] == [u["key"] for u in pc.UNITS]
    assert data["next"] == "py_syllable" and data["passed"] == 0
    for u in data["units"]:
        assert u["title"] and u["intro"] and len(u["points"]) >= 3 and u["examples"]
        assert len(u["guided"]) == 3 and not u["passed"] and u["played"] == 0
        for g in u["guided"]:
            assert 0 <= g["answer"] < len(g["options"]) and g["zh"] and g["py"]
            assert g["why"][g["answer"]] is not None or g["type"] == "sound_pinyin"
    for lang in ("ru", "tg", "zh"):
        loc = expect(client, "get", "/api/sound-world/pinyin-course", 200, headers={**h, "X-Locale": lang})
        assert loc["units"][0]["intro"] == pc.UNITS[0]["intro"][lang]
        assert loc["units"][1]["title"] == pc.UNITS[1]["title"][lang]
    with SessionLocal() as db:
        assert db.query(models.PracticeSession).filter_by(user_id=uid).count() == 0, "reading the course writes nothing"
    assert client.get("/api/sound-world/pinyin-course").status_code == 401


@pytest.mark.parametrize("key", [u["key"] for u in pc.UNITS])
def test_every_unit_check_is_honest(client, key):
    _, h = register(client)
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "pronunciation", "env": key})
    assert s["context"]["lesson"] == key and len(s["questions"]) == 8
    keys = stored(s["id"])
    for q, k in zip(s["questions"], keys):
        labels = [o["label"] for o in q["options"]]
        assert len(labels) == len(set(labels)) >= 2, labels
        right = k["options"][k["item_id"]]
        py = k["lines"][0]["py"]
        if k["type"] in ("sound_tone", "sound_pinyin"):
            assert right["label"] == py and q["prompt"]["lines"][0]["speak"], "heard: the voice says the answer"
        else:
            assert q["prompt"]["lines"] == [], "read questions do not play the answer first"
            assert q["prompt"]["ask"]["item"]
        if k["type"] == "pinyin_part":
            ini, fin = pc.split(py)
            assert right["label"] == (fin if k["part"] == "final" else ini or "—")
        if k["type"] == "pinyin_tone_mark":
            assert int(right["label"]) == pc.tone_of(py)
        if k["type"] == "pinyin_spell":
            assert right["label"] == py


def test_wrong_answers_say_what_differed(client):
    _, h = register(client)
    _, keys, results = play(client, h, "py_initials1", right=False)
    for k, r in zip(keys, results):
        assert not r["correct"] and r["check"]["kind"] == "pinyin"
        assert r["check"]["why"] == "initial" and r["check"]["picked_part"] != r["check"]["answer_part"]
    _, keys, results = play(client, h, "py_spelling", right=False)
    assert all(r["check"]["why"] == "rule" and r["check"]["rule"] for r in results)
    _, keys, results = play(client, h, "py_tones", right=False)
    for k, r in zip(keys, results):
        assert r["check"]["why"] in ("tone", "mark") and r["check"]["picked_tone"] != r["check"]["answer_tone"]


def test_explain_compares_heard_syllables():
    q = {"type": "sound_pinyin", "options": [{"label": "shān"}, {"label": "shāng"}], "item_id": 1}
    w = pc.explain(q, 0)
    assert (w["why"], w["tip"], w["picked_part"], w["answer_part"]) == ("final", "nasal", "an", "ang")
    q = {"type": "sound_pinyin", "options": [{"label": "bà"}, {"label": "pà"}], "item_id": 1}
    assert pc.explain(q, 0)["tip"] == "air"
    q = {"type": "sound_tone", "options": [{"label": "mǎ"}, {"label": "mà"}], "item_id": 0}
    w = pc.explain(q, 1)
    assert w["why"] == "tone" and (w["picked_tone"], w["answer_tone"]) == (4, 3)


def test_passing_every_unit_completes_the_first_journey_step(client):
    _, h = register(client)
    step = lambda: next(s for s in expect(client, "get", "/api/journey", 200, headers=h)["foundation"]["steps"]
                        if s["key"] == "tones")
    assert step()["status"] == "current"
    for u in pc.UNITS[:-1]:
        play(client, h, u["key"])
    assert step()["status"] == "current", "not done until every unit is passed"
    data = expect(client, "get", "/api/sound-world/pinyin-course", 200, headers=h)
    assert data["passed"] == len(pc.UNITS) - 1 and data["next"] == "py_spelling"
    play(client, h, "py_spelling")
    assert step()["status"] == "done"
    # The Sound World course is not touched by the pinyin units.
    sw = expect(client, "get", "/api/sound-world/pronunciation", 200, headers=h)
    assert sw["passed"] == 0 and all(x["played"] == 0 for x in sw["lessons"])


def test_the_tones_round_is_heard(client):
    _, h = register(client)
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "tones"})
    chars = [q for q in s["questions"] if q["type"] == "char_to_pinyin"]
    assert chars and all(q["prompt"]["speak"] == q["prompt"]["text"] for q in chars)
    # ... while ordinary Hanzi practice still asks the reading from memory.
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "hanzi", "hsk_level": 1})
    assert all(q["prompt"].get("speak") is None for q in s["questions"] if q["type"] == "char_to_pinyin")


def test_a_wrong_tone_in_the_tones_round_names_both_tones(client):
    _, h = register(client)
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "tones"})
    keys = stored(s["id"])
    seen = 0
    for q in s["questions"]:
        k = keys[q["index"]]
        if q["type"] != "char_to_pinyin":
            continue
        wrong = next(o for o in q["options"] if o["id"] != k["item_id"])
        r = expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h,
                   json={"index": q["index"], "choice_id": wrong["id"], "response_ms": 2000})
        c = r["check"]
        if "picked_tone" in c:
            seen += 1
            assert c["picked_tone"] == pc.tone_of(c["picked"]) and c["answer_tone"] == pc.tone_of(c["answer"])
            assert c["picked_tone"] != c["answer_tone"]
    assert seen >= 1


def test_every_syllable_question_has_real_choices():
    with SessionLocal() as db:
        rng = random.Random(7)
        for zh, py, ini, fin in pc.SYLLABLES:
            for ask in ("initial", "final"):
                q = pc._part_question(db, zh, py, ini, fin, ask, rng)
                labels = [o["label"] for o in q["options"]]
                assert len(labels) == len(set(labels)) >= 2, (py, ask, labels)
