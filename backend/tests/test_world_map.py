"""The living world on /real-chinese: places open, light up and record
progress only from real learning, and the HSK level is the only gate."""

from datetime import datetime, timedelta

import pytest

from app import models
from app.database import SessionLocal
from app.services import sentence as sent
from app.services.gamification import user_rank
from app.services.real_life import RULES
from app.services.world_map import _trains
from app.services.world_places import CANVAS_H, CANVAS_W, DISTRICTS, PATHS, PLACE_BY_KEY, PLACES
from helpers import expect, register as register_only, unique_name

ORIGINAL_PLACES = {"home", "library", "calligraphy", "word_garden", "street", "restaurant", "shop", "shopping_district",
                   "internet_cafe", "detective", "sound_plaza", "passport_office", "university", "hospital", "office",
                   "train_station", "hotel", "old_town", "airport"}


def register(client):
    uid, h = register_only(client, unique_name("explorer"))
    expect(client, "get", "/api/dashboard", 200, headers=h)  # skill rows
    return uid, h


def know(uid, words, status="mastered"):
    """Test setup: give the learner real-shaped records for these words."""
    with SessionLocal() as db:
        now = datetime.utcnow()
        for w in words:
            row = db.query(models.VocabularyWord).filter_by(simplified=w).order_by(models.VocabularyWord.id).first()
            db.add(models.UserVocabulary(user_id=uid, word_id=row.id, status=status, mastery=90.0, times_seen=8,
                                         last_reviewed_at=now - timedelta(days=1), next_review_at=now + timedelta(days=9)))
        db.commit()


def set_skills(uid, value_for):
    with SessionLocal() as db:
        for us in db.query(models.UserSkill).filter_by(user_id=uid):
            us.mastery = value_for(us.skill.code)
        db.commit()


def counts(uid):
    with SessionLocal() as db:
        return tuple(db.query(m).filter_by(user_id=uid).count() for m in (
            models.UserVocabulary, models.ActivityEvent, models.PracticeSession, models.UserSkill, models.VoiceAttempt))


def world(client, h):
    return expect(client, "get", "/api/real-life/world", 200, headers=h)


def places(w):
    return {p["key"]: p for p in w["places"]}


def play_all_right(client, h, body):
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json=body)
    with SessionLocal() as db:
        keys = db.get(models.PracticeSession, s["id"]).questions
    for q in s["questions"]:
        expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h,
               json={"index": q["index"], "choice_id": keys[q["index"]]["item_id"]})
    expect(client, "post", f"/api/practice/sessions/{s['id']}/complete", 200, headers=h)


@pytest.fixture
def newcomer(client):
    return register(client)


def test_the_world_requires_sign_in(client):
    expect(client, "get", "/api/real-life/world", 401)


def test_places_use_real_words_valid_sentences_and_every_scene(client):
    with SessionLocal() as db:
        have = {w for (w,) in db.query(models.VocabularyWord.simplified)}
        for p in PLACES:
            assert all(w in have for w in p["theme"]), p["key"]
            for t in p["topics"]:
                assert all(w in have and w in t["sentence"] for w in t["words"]), (p["key"], t["key"])
                sent.validate(db, t["sentence"])
    assert len({p["scene"] for p in PLACES if p["scene"]}) == 13


def test_the_city_is_laid_out_and_every_place_is_reachable_from_home():
    keys = [p["key"] for p in PLACES]
    assert len(keys) == len(set(keys)) and ORIGINAL_PLACES <= set(keys) and len(set(keys) - ORIGINAL_PLACES) >= 20, len(keys)
    for p in PLACES:
        assert 6 <= p["x"] <= CANVAS_W - 6 and 6 <= p["y"] <= CANVAS_H - 6, p["key"]
        assert p["district"] in DISTRICTS, p["key"]
        assert all(link.startswith("/") for link in p["links"]), p["key"]
        assert p["topics"] or p["gateway"], f"{p['key']} has nothing to learn or open"
    for i, a in enumerate(PLACES):
        for b in PLACES[i + 1:]:
            assert ((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5 >= 14, (a["key"], b["key"])
    assert set(DISTRICTS) == {p["district"] for p in PLACES}
    assert all(a in PLACE_BY_KEY and b in PLACE_BY_KEY for a, b in PATHS)
    reach, todo = {"home"}, ["home"]
    while todo:
        k = todo.pop()
        for a, b in PATHS:
            for x, y in ((a, b), (b, a)):
                if x == k and y not in reach:
                    reach.add(y)
                    todo.append(y)
    assert reach == set(keys), set(keys) - reach


def test_a_newcomer_has_nothing_claimed_and_one_next_stop(client, newcomer):
    uid, h = newcomer
    before = counts(uid)
    w = world(client, h)
    ps = places(w)
    assert w["level"] == 1 and w["current"] == "home"
    assert all(p["status"] in ("open", "locked") for p in ps.values()), [(k, p["status"]) for k, p in ps.items()]
    assert ps["restaurant"]["status"] == "open" and ps["hospital"]["status"] == "locked"
    assert ps["hospital"]["greeting"] is None and ps["hospital"]["min_level"] == 3
    assert not any(t["lit"] for p in ps.values() for t in p["topics"])
    assert w["passport"]["explored"] == 0 and w["passport"]["scenes_done"] == 0 and w["passport"]["skills_shown"] == 0
    assert w["adaptation"]["speech"] == "standard" and not w["adaptation"]["evidence"]
    assert ps["restaurant"]["greeting"]["tokens"] and ps["restaurant"]["talks"]
    assert counts(uid) == before, "the map must not write progress"
    # nothing is "new" or "visited" for a newcomer; one next stop
    assert not any(p["new"] or p["visited"] for p in ps.values())
    rec = w["recommended"]
    assert rec and ps[rec["key"]]["status"] == "open" and rec["key"] != w["current"] and rec["reason"] in ("words", "next")
    assert rec["skill"] is None, "no weakest skill without evidence"


def test_knowing_a_places_words_never_opens_it_before_its_level(client, newcomer):
    uid, h = newcomer
    # the server enforces the lock
    expect(client, "post", "/api/practice/sessions", 403, headers=h, json={"source": "scene", "scene": "hospital"})
    expect(client, "get", "/api/real-life/scenes/hospital", 403, headers=h)
    know(uid, list(PLACE_BY_KEY["hospital"]["theme"]))
    w = world(client, h)
    hosp = places(w)["hospital"]
    assert w["level"] == 1 and hosp["status"] == "locked"
    assert not (hosp["topics"] or hosp["theme"]["words"] or hosp["talks"] or hosp["scene"] or hosp["internet"]
                or hosp["sound"] or hosp["gateway"] or hosp["links"] or hosp["greeting"]), "a locked place leaks content"
    expect(client, "post", "/api/practice/sessions", 403, headers=h, json={"source": "scene", "scene": "hospital"})
    expect(client, "get", "/api/real-life/scenes/hospital", 403, headers=h)


def test_a_round_started_and_left_marks_the_place_visited_not_explored(client, newcomer):
    _, h = newcomer
    expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "scene", "scene": "convenience-store"})
    shop = places(world(client, h))["shop"]
    assert shop["status"] == "open" and shop["visited"] and not shop["new"]


def test_a_completed_scene_explores_the_place_and_moves_the_learner_there(client, newcomer):
    _, h = newcomer
    play_all_right(client, h, {"source": "scene", "scene": "restaurant"})
    w = world(client, h)
    rest = places(w)["restaurant"]
    assert rest["status"] in ("explored", "mastered") and rest["scene"]["best"] == 100
    assert w["current"] == "restaurant" and w["passport"]["explored"] >= 1 and w["passport"]["scenes_done"] == 1


def test_learning_a_cafe_sentence_explores_the_cafe_and_claims_nothing_else(client, newcomer):
    _, h = newcomer
    w = world(client, h)
    ps = places(w)
    assert ps["cafe"]["status"] == "open" and ps["cafe"]["links"] == ["/assistant"] and not ps["cafe"]["scene"]
    assert w["map"]["w"] == CANVAS_W and len(w["map"]["river"]) >= 2 and w["map"]["districts"] == list(DISTRICTS)
    play_all_right(client, h, {"source": "sentence", "sentence": PLACE_BY_KEY["cafe"]["topics"][0]["sentence"]})
    w = world(client, h)
    ps = places(w)
    assert ps["cafe"]["status"] == "explored" and w["current"] == "cafe", (ps["cafe"]["status"], w["current"])
    assert ps["bookstore"]["status"] == "open" and ps["park"]["status"] == "open", "nothing else claimed"


def test_the_next_stop_trains_the_weakest_skill(client, newcomer):
    uid, h = newcomer
    set_skills(uid, lambda code: 10.0 if code == "reading" else 55.0)
    rec = world(client, h)["recommended"]
    assert rec["reason"] == "skill" and rec["skill"] == "reading" and "reading" in _trains(PLACE_BY_KEY[rec["key"]]), rec


def test_strong_listening_gets_faster_speech_and_an_extra_listening_check(client, newcomer):
    _, newbie_h = newcomer
    aid, ah = register(client)
    set_skills(aid, lambda code: {"listening": 80.0, "vocabulary": 10.0, "grammar": 30.0}.get(code, 30.0))
    ad = world(client, ah)["adaptation"]
    assert ad["speech"] == "faster" and ad["words"] == "familiar" and ad["grammar"] == "standard"
    sc = expect(client, "post", "/api/practice/sessions", 201, headers=ah, json={"source": "scene", "scene": "restaurant"})
    listens = [q for q in sc["questions"] if q["type"] == "scene_listen"]
    reply = next(q for q in sc["questions"] if q["type"] == "scene_reply")
    tier = sc["context"]["tier"]
    assert len(listens) == len(RULES[tier]["listen"]) + 1, (tier, len(listens))
    assert reply["prompt"]["rate"] > RULES[tier]["rate"], (tier, reply["prompt"]["rate"])
    # a new learner gets the tier as written
    newbie = expect(client, "post", "/api/practice/sessions", 201, headers=newbie_h, json={"source": "scene", "scene": "restaurant"})
    assert not any(q["type"] == "scene_listen" for q in newbie["questions"])


@pytest.mark.parametrize("level", range(1, 8))
def test_the_hsk_level_is_the_only_gate(client, level):
    # 7 = the shared 7-9 band
    lid, lh = register(client)
    set_skills(lid, lambda code: (level - 1) * 15 + 0.5)
    with SessionLocal() as db:
        assert user_rank(db, db.get(models.User, lid))[0] == level
    w = world(client, lh)
    assert w["level"] == level
    ps = places(w)
    should = {p["key"] for p in PLACES if p["min_level"] <= level}
    is_open = {k for k, p in ps.items() if p["status"] != "locked"}
    assert is_open == should, (level, sorted(is_open ^ should))
    assert all(not ps[k]["topics"] and not ps[k]["theme"]["words"] for k in ps if k not in should)
    for p in (p for p in PLACES if p["scene"]):
        code = 201 if p["min_level"] <= level else 403
        expect(client, "post", "/api/practice/sessions", code, headers=lh, json={"source": "scene", "scene": p["scene"]})
        expect(client, "get", f"/api/real-life/scenes/{p['scene']}", 200 if code == 201 else 403, headers=lh)


def test_the_old_world_map_endpoints_are_gone_but_scenario_talks_load(client, newcomer):
    _, h = newcomer
    expect(client, "get", "/api/world/locations", 404, headers=h)
    expect(client, "get", "/api/world/locations/restaurant", 404, headers=h)
    expect(client, "get", "/api/world/scenarios/ordering-noodles", 200, headers=h)
