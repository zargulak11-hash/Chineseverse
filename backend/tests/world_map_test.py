"""The living world on /real-chinese: places open, light up and record
progress only from real learning -- end to end on a fresh database."""

import os
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/world_map.db"
os.environ["AI_PROVIDER"] = "offline"

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services import sentence as sent  # noqa: E402
from app.services.world_places import CANVAS_H, CANVAS_W, DISTRICTS, PATHS, PLACE_BY_KEY, PLACES  # noqa: E402


def expect(client, method, url, expected, **kwargs):
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == expected, f"{method.upper()} {url} -> {resp.status_code} (expected {expected}): {resp.text}"
    return resp.json() if resp.content else None


def register(client, name):
    data = expect(client, "post", "/api/auth/register", 201,
                  json={"username": name, "email": f"{name}@example.com", "password": "secret1"})
    h = {"Authorization": f"Bearer {data['access_token']}"}
    expect(client, "get", "/api/dashboard", 200, headers=h)
    return data["user"]["id"], h


def know(uid, words, status="mastered"):
    """Test setup: give the learner real-shaped records for these words."""
    with SessionLocal() as db:
        now = datetime.utcnow()
        for w in words:
            row = db.query(models.VocabularyWord).filter_by(simplified=w).order_by(models.VocabularyWord.id).first()
            db.add(models.UserVocabulary(user_id=uid, word_id=row.id, status=status, mastery=90.0, times_seen=8,
                                         last_reviewed_at=now - timedelta(days=1), next_review_at=now + timedelta(days=9)))
        db.commit()


def counts(uid):
    with SessionLocal() as db:
        return tuple(db.query(m).filter_by(user_id=uid).count() for m in (
            models.UserVocabulary, models.ActivityEvent, models.PracticeSession, models.UserSkill, models.VoiceAttempt))


def places(w):
    return {p["key"]: p for p in w["places"]}


with TestClient(app) as client:
    expect(client, "get", "/api/real-life/world", 401)

    # ---- content: real words, real sentences, every scene on the map
    with SessionLocal() as db:
        have = {w for (w,) in db.query(models.VocabularyWord.simplified)}
        for p in PLACES:
            assert all(w in have for w in p["theme"]), p["key"]
            for t in p["topics"]:
                assert all(w in have and w in t["sentence"] for w in t["words"]), (p["key"], t["key"])
                sent.validate(db, t["sentence"])
    assert len({p["scene"] for p in PLACES if p["scene"]}) == 10
    print(f"[PASS] {len(PLACES)} places: real theme words, valid topic sentences, all 10 Real Chinese scenes placed")

    # ---- the city: every place on the canvas, apart from the others, in a
    # known district, reachable by road; the 19 original places all still there
    ORIGINAL = {"home", "library", "calligraphy", "word_garden", "street", "restaurant", "shop", "shopping_district",
                "internet_cafe", "detective", "sound_plaza", "passport_office", "university", "hospital", "office",
                "train_station", "hotel", "old_town", "airport"}
    keys = [p["key"] for p in PLACES]
    assert len(keys) == len(set(keys)) and ORIGINAL <= set(keys) and len(set(keys) - ORIGINAL) >= 20, len(keys)
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
    print(f"[PASS] a {CANVAS_W}x{CANVAS_H} city: {len(DISTRICTS)} districts, {len(PATHS)} roads, every place reachable from home")

    # ---- a brand-new learner: nothing claimed
    uid, h = register(client, "newcomer")
    before = counts(uid)
    w = expect(client, "get", "/api/real-life/world", 200, headers=h)
    ps = places(w)
    assert w["level"] == 1 and w["current"] == "home"
    assert all(p["status"] in ("open", "locked") for p in ps.values()), [(k, p["status"]) for k, p in ps.items()]
    assert ps["restaurant"]["status"] == "open" and ps["hospital"]["status"] == "locked"
    assert ps["hospital"]["to_open"] and ps["hospital"]["greeting"] is None
    assert not any(t["lit"] for p in ps.values() for t in p["topics"])
    assert w["passport"]["explored"] == 0 and w["passport"]["scenes_done"] == 0 and w["passport"]["skills_shown"] == 0
    assert w["adaptation"]["speech"] == "standard" and not w["adaptation"]["evidence"]
    assert ps["restaurant"]["greeting"]["tokens"] and ps["restaurant"]["talks"]
    assert counts(uid) == before, "the map must not write progress"
    print("[PASS] new learner: only level-1 places open, nothing explored or lit, standard difficulty, read-only")

    # ---- the server enforces the same lock
    expect(client, "post", "/api/practice/sessions", 403, headers=h, json={"source": "scene", "scene": "hospital"})
    expect(client, "get", "/api/real-life/scenes/hospital", 403, headers=h)
    print("[PASS] a locked place's scene is refused by the server too (403)")

    # ---- learning its words opens a place before its level
    know(uid, ["医生", "医院", "药"])
    ps = places(expect(client, "get", "/api/real-life/world", 200, headers=h))
    assert ps["hospital"]["status"] == "open" and ps["hospital"]["opened_by"] == "words"
    assert any(t["lit"] for t in ps["hospital"]["topics"] if t["key"] == "doctor")
    expect(client, "get", "/api/real-life/scenes/hospital", 200, headers=h)
    print("[PASS] knowing 3 hospital words opens the hospital early and lights its 'doctor' topic")

    # ---- playing a scene explores the place and moves the learner there
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "scene", "scene": "restaurant"})
    with SessionLocal() as db:
        keys = db.get(models.PracticeSession, s["id"]).questions
    for q in s["questions"]:
        expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h,
               json={"index": q["index"], "choice_id": keys[q["index"]]["item_id"]})
    expect(client, "post", f"/api/practice/sessions/{s['id']}/complete", 200, headers=h)
    w = expect(client, "get", "/api/real-life/world", 200, headers=h)
    ps = places(w)
    assert ps["restaurant"]["status"] in ("explored", "mastered") and ps["restaurant"]["scene"]["best"] == 100
    assert w["current"] == "restaurant" and w["passport"]["explored"] >= 1 and w["passport"]["scenes_done"] == 1
    print("[PASS] a completed scene explores the place, records its best score and moves the companion there")

    # ---- a new place with no scene: learning one of its sentences is being there
    assert ps["cafe"]["status"] == "open" and ps["cafe"]["links"] == ["/assistant"] and not ps["cafe"]["scene"]
    assert w["map"]["w"] == CANVAS_W and len(w["map"]["river"]) >= 2 and w["map"]["districts"] == list(DISTRICTS)
    cafe_sentence = PLACE_BY_KEY["cafe"]["topics"][0]["sentence"]
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "sentence", "sentence": cafe_sentence})
    with SessionLocal() as db:
        keys_ = db.get(models.PracticeSession, s["id"]).questions
    for q in s["questions"]:
        expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h,
               json={"index": q["index"], "choice_id": keys_[q["index"]]["item_id"]})
    expect(client, "post", f"/api/practice/sessions/{s['id']}/complete", 200, headers=h)
    w = expect(client, "get", "/api/real-life/world", 200, headers=h)
    ps = places(w)
    assert ps["cafe"]["status"] == "explored" and w["current"] == "cafe", (ps["cafe"]["status"], w["current"])
    assert ps["bookstore"]["status"] == "open" and ps["park"]["status"] == "open", "nothing else claimed"
    print("[PASS] learning a cafe sentence explores the cafe and moves the companion there; nothing else is claimed")

    # ---- Learning DNA adapts the scenes
    aid, ah = register(client, "goodlistener")
    with SessionLocal() as db:
        for us in db.query(models.UserSkill).filter_by(user_id=aid):
            us.mastery = {"listening": 80.0, "vocabulary": 10.0, "grammar": 30.0}.get(us.skill.code, 30.0)
        db.commit()
    ad = expect(client, "get", "/api/real-life/world", 200, headers=ah)["adaptation"]
    assert ad["speech"] == "faster" and ad["words"] == "familiar" and ad["grammar"] == "standard"
    sc = expect(client, "post", "/api/practice/sessions", 201, headers=ah, json={"source": "scene", "scene": "restaurant"})
    listens = [q for q in sc["questions"] if q["type"] == "scene_listen"]
    reply = next(q for q in sc["questions"] if q["type"] == "scene_reply")
    from app.services.real_life import RULES

    tier = sc["context"]["tier"]
    assert len(listens) == len(RULES[tier]["listen"]) + 1, (tier, len(listens))
    assert reply["prompt"]["rate"] > RULES[tier]["rate"], (tier, reply["prompt"]["rate"])
    newbie = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "scene", "scene": "restaurant"})
    assert not any(q["type"] == "scene_listen" for q in newbie["questions"])
    print("[PASS] strong listening -> faster speech and an extra listening check; new learners get the tier as written")

    # The old World map is gone; its talks and cases live on inside this one.
    expect(client, "get", "/api/world/locations", 404, headers=h)
    expect(client, "get", "/api/world/locations/restaurant", 404, headers=h)
    expect(client, "get", "/api/world/scenarios/ordering-noodles", 200, headers=h)
    print("[PASS] the old World map endpoints are removed; scenario talks still load")

    print("ALL WORLD MAP TESTS PASSED")
