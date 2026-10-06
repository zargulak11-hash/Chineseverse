"""Sound World pronunciation lessons (services/pronunciation.py): the course
list, every lesson's round, honest answers (the right option really is
what was spoken), grading through the practice engine, and the record."""

import pytest

from app import models
from app.database import SessionLocal
from app.services import pronunciation
from helpers import expect, register as register_only, unique_name


def register(client):
    uid, h = register_only(client, unique_name("ear"))
    expect(client, "get", "/api/dashboard", 200, headers=h)  # creates skill rows
    return uid, h


def stored(sid):
    with SessionLocal() as db:
        return db.get(models.PracticeSession, sid).questions


def tones_skill(uid):
    with SessionLocal() as db:
        return next(us.mastery for us in db.query(models.UserSkill).join(models.Skill)
                    .filter(models.UserSkill.user_id == uid) if us.skill.code == "tones")


def test_the_course_lists_every_lesson_with_explanations_and_writes_nothing(client):
    uid, h = register(client)
    data = expect(client, "get", "/api/sound-world/pronunciation", 200, headers=h)
    keys = [x["key"] for x in data["lessons"]]
    assert keys == ["tones", "neutral", "initials", "finals", "tone_pairs", "sandhi", "pairs", "dialogues"]
    assert data["next"] == "tones" and data["passed"] == 0
    for x in data["lessons"]:
        assert x["title"] and x["title_zh"] and x["how"] and x["examples"] and x["played"] == 0 and not x["passed"]
        assert all(e["zh"] and e["py"] for e in x["examples"])
    ru = expect(client, "get", "/api/sound-world/pronunciation", 200, headers={**h, "X-Locale": "ru"})
    assert ru["lessons"][0]["title"] == pronunciation.BY_KEY["tones"]["title"]["ru"]
    with SessionLocal() as db:
        assert db.query(models.PracticeSession).filter_by(user_id=uid).count() == 0
    assert client.get("/api/sound-world/pronunciation").status_code == 401


@pytest.mark.parametrize("key", [lesson["key"] for lesson in pronunciation.LESSONS])
def test_every_lesson_builds_a_heard_round_with_honest_options(client, key):
    _, h = register(client)
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "pronunciation", "env": key})
    assert s["context"]["kind"] == "pronunciation" and s["context"]["lesson"] == key
    assert 1 <= len(s["questions"]) <= pronunciation.ROUND
    keys = stored(s["id"])
    for q, k in zip(s["questions"], keys):
        assert q["type"].startswith("sound_") and q["answer"] is None and "item_id" not in q
        assert all(line["text"] is None and line["speak"] for line in q["prompt"]["lines"]), "heard before it is read"
        labels = [o["label"] for o in q["options"]]
        assert len(labels) == len(set(labels)) >= 2, labels
        right = k["options"][k["item_id"]]
        if k["type"] in ("sound_tone", "sound_pinyin"):
            assert right["label"] == k["lines"][0]["py"], "the right pinyin is what the voice says"
        if k["type"] == "sound_pair":
            assert right["zh"] == k["lines"][0]["zh"]
        if k["type"] == "sound_dialogue":
            assert q["prompt"]["ask"]["question_zh"] and q["prompt"]["ask"]["question"]


def test_a_passed_lesson_counts_and_trains_tones(client):
    uid, h = register(client)
    before = tones_skill(uid)
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "pronunciation", "env": "tones"})
    keys = stored(s["id"])
    first = s["questions"][0]
    r = expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h,
               json={"index": first["index"], "choice_id": keys[0]["item_id"], "response_ms": 2000})
    assert r["correct"] and r["card"]["hanzi"] == keys[0]["lines"][0]["zh"]
    for q in s["questions"][1:]:
        expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h,
               json={"index": q["index"], "choice_id": keys[q["index"]]["item_id"], "response_ms": 2000})
    expect(client, "post", f"/api/practice/sessions/{s['id']}/complete", 200, headers=h)
    assert tones_skill(uid) > before
    data = expect(client, "get", "/api/sound-world/pronunciation", 200, headers=h)
    tones = data["lessons"][0]
    assert tones["played"] == 1 and tones["best"] == 100.0 and tones["passed"] and data["next"] == "neutral"
    with SessionLocal() as db:
        assert db.query(models.ActivityEvent).filter_by(user_id=uid, action_type="sound_world").count() == 1


def test_a_missed_sound_is_shown_with_its_pinyin_and_not_passed(client):
    _, h = register(client)
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "pronunciation", "env": "pairs"})
    keys = stored(s["id"])
    for q in s["questions"]:
        wrong = next(o["id"] for o in q["options"] if o["id"] != keys[q["index"]]["item_id"])
        r = expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h,
                   json={"index": q["index"], "choice_id": wrong})
        assert not r["correct"] and r["card"]["pinyin"]
    expect(client, "post", f"/api/practice/sessions/{s['id']}/complete", 200, headers=h)
    pairs = next(x for x in expect(client, "get", "/api/sound-world/pronunciation", 200, headers=h)["lessons"]
                 if x["key"] == "pairs")
    assert pairs["played"] == 1 and not pairs["passed"]


def test_an_unknown_lesson_is_not_found(client):
    _, h = register(client)
    expect(client, "post", "/api/practice/sessions", 404, headers=h, json={"source": "pronunciation", "env": "singing"})
    expect(client, "post", "/api/practice/sessions", 404, headers=h, json={"source": "pronunciation"})


def test_course_data_is_consistent():
    for group in pronunciation.TONE_SETS:
        assert len(group) == 4 and len({p for _, p in group}) == 4
    for z, p, wrong in pronunciation.NEUTRAL + pronunciation.SANDHI:
        assert p not in wrong and len(set(wrong)) == len(wrong)
    for _, _, pattern in pronunciation.TONE_PAIRS:
        assert pattern in pronunciation.PATTERNS
    for a, b, q, options, answer, tr in pronunciation.DIALOGUES:
        assert 0 <= answer < len(options) and all(tr)
