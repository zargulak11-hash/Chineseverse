"""Chinese Internet, content adaptation / word help, and the Chinese
Passport (capabilities, evidence, story) -- end to end on a fresh database."""

import os
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/passport.db"
os.environ["AI_PROVIDER"] = "offline"

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services import sentence as sent  # noqa: E402
from app.services.internet_content import ITEM_BY_SLUG, ITEMS  # noqa: E402


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


def stored(sid):
    with SessionLocal() as db:
        s = db.get(models.PracticeSession, sid)
        return s.questions


def play(client, h, s, right=True):
    qs = stored(s["id"])
    for q in s["questions"]:
        good = qs[q["index"]]["item_id"]
        choice = good if right else next(o["id"] for o in q["options"] if o["id"] != good)
        expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h,
               json={"index": q["index"], "choice_id": choice, "response_ms": 3000})
    return expect(client, "post", f"/api/practice/sessions/{s['id']}/complete", 200, headers=h)


def counts(uid):
    with SessionLocal() as db:
        return tuple(db.query(m).filter_by(user_id=uid).count() for m in (
            models.UserVocabulary, models.UserHanzi, models.ActivityEvent, models.LearningMistake,
            models.PracticeSession, models.UserSkill))


with TestClient(app) as client:
    for path in ("/api/internet/feed", "/api/passport", "/api/internet/items/metro-line", "/api/internet/words/1"):
        expect(client, "get", path, 401)
    expect(client, "post", "/api/vocab/1/track", 401)

    # ---- content sanity: every version reads, every answer option is in place
    with SessionLocal() as db:
        for item in ITEMS:
            assert set(item["versions"]) == {"original", "intermediate", "beginner"}
            for v, blocks in item["versions"].items():
                text = "".join(b["text"] for b in blocks)
                assert [t for t in sent.segment(db, text) if t["word"] is not None], (item["slug"], v)
            for q in item["questions"]:
                assert 0 <= q["answer"] < len(q["options"]) and len(set(q["options"])) == len(q["options"])
    print("[PASS] 10 curated items x 3 versions, comprehension answer keys valid")

    uid, h = register(client, "netreader")
    feed = expect(client, "get", "/api/internet/feed", 200, headers=h)
    assert len(feed["items"]) == 10 and feed["profile"]["level"] == 1
    assert all(i["recommended"] in ("beginner", "intermediate") for i in feed["items"]), [i["recommended"] for i in feed["items"]]
    ru = expect(client, "get", "/api/internet/feed", 200, headers={**h, "X-Locale": "ru"})
    assert ru["items"][0]["summary"] != feed["items"][0]["summary"]
    print("[PASS] feed: a new HSK 1 learner is offered adapted versions; summaries localized")

    before = counts(uid)
    view = expect(client, "get", "/api/internet/items/metro-line", 200, headers=h)
    words = [t for b in view["blocks"] for t in b["tokens"] if t["kind"] == "word"]
    assert words and all(t["status"] == "new" for t in words)
    assert view["glossary"] and view["notes"] and view["coverage"]["original"]["total"] > 0
    orig = expect(client, "get", "/api/internet/items/metro-line?version=original", 200, headers=h)
    assert orig["version"] == "original" and orig["blocks"][0]["text"] != view["blocks"][0]["text"]
    expect(client, "get", "/api/internet/items/nope", 404, headers=h)
    expect(client, "get", "/api/internet/items/metro-line?version=hard", 422, headers=h)
    assert counts(uid) == before, "reading must not write progress"
    print("[PASS] item view: word states, glossary, notes, version switch; read-only; 404/422")

    # ---- known vocabulary moves the recommended version up
    item = ITEM_BY_SLUG["class-group-chat"]
    with SessionLocal() as db:
        text = "".join(b["text"] for b in item["versions"]["original"])
        ids = {t["word"].id for t in sent.segment(db, text) if t["word"] is not None}
        now = datetime.utcnow()
        for wid in ids:
            db.add(models.UserVocabulary(user_id=uid, word_id=wid, status="mastered", mastery=90.0, times_seen=9,
                                         last_reviewed_at=now - timedelta(days=1), next_review_at=now + timedelta(days=9)))
        db.commit()
    view2 = expect(client, "get", "/api/internet/items/class-group-chat", 200, headers=h)
    assert view2["recommended"] == "original", view2["coverage"]
    other = next(i for i in expect(client, "get", "/api/internet/feed", 200, headers=h)["items"] if i["slug"] == "metro-line")
    assert other["recommended"] != "original" or other["coverage"]["ratio"] >= 0.8
    print("[PASS] a learner who knows the original's words is offered the original (others stay adapted)")

    # ---- weak words come first
    with SessionLocal() as db:
        w = db.query(models.VocabularyWord).filter_by(simplified="地铁").order_by(models.VocabularyWord.id).first()
        db.add(models.LearningMistake(user_id=uid, mistake_type="word", reference="地铁", priority=3, occurrences=3,
                                      mastered=False, last_seen_at=datetime.utcnow()))
        db.commit()
        weak_id = w.id
    view = expect(client, "get", "/api/internet/items/metro-line", 200, headers=h)
    assert view["glossary"][0]["word_id"] == weak_id and view["glossary"][0]["weak"]
    print("[PASS] a word with an open mistake is marked weak and leads the glossary")

    # ---- word help + add to review only when not already scheduled
    new_word = next(t for t in view["glossary"] if t["status"] == "new" and not t["weak"])
    help1 = expect(client, "get", f"/api/internet/words/{new_word['word_id']}?item=metro-line", 200, headers=h)
    assert help1["can_add"] and help1["add_reason"] == "new" and help1["characters"] and help1["context"]
    assert all(any(c in r["text"] for c in help1["text"]) for r in help1["related"])
    tr1 = expect(client, "post", f"/api/vocab/{new_word['word_id']}/track", 200, headers=h)
    assert tr1["status"] == "learning"
    expect(client, "post", f"/api/vocab/{new_word['word_id']}/track", 409, headers=h)
    help2 = expect(client, "get", f"/api/internet/words/{new_word['word_id']}", 200, headers=h)
    assert not help2["can_add"] and help2["add_reason"] == "in_review" and help2["state"]["mastery"] == 0.0
    mastered_id = next(iter(ids))
    help3 = expect(client, "get", f"/api/internet/words/{mastered_id}", 200, headers=h)
    assert not help3["can_add"] and help3["add_reason"] == "mastered"
    expect(client, "post", f"/api/vocab/{mastered_id}/track", 409, headers=h)
    expect(client, "get", "/api/internet/words/999999", 404, headers=h)
    # the context sentence comes from the version being read
    beg = expect(client, "get", f"/api/internet/words/{weak_id}?item=metro-line&version=beginner", 200, headers=h)
    assert beg["context"]["version"] == "beginner", beg["context"]
    with SessionLocal() as db:
        assert db.query(models.ActivityEvent).filter_by(user_id=uid, action_type="word_saved").count() == 1
    print("[PASS] word help: meaning, characters, related words, context; add-to-review respects existing state")

    # ---- graded round
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "internet", "item": "hotpot-review"})
    types = [q["type"] for q in s["questions"]]
    assert types.count("net_comprehension") == 3 and "net_listen" in types
    assert s["context"]["kind"] == "internet" and s["context"]["slug"] == "hotpot-review"
    expect(client, "post", "/api/practice/sessions", 404, headers=h, json={"source": "internet", "item": "zzz"})
    fin = play(client, h, s)
    assert fin["score"] == 100 and fin["reaction"]["event"] == "internet_complete"
    with SessionLocal() as db:
        assert db.query(models.ActivityEvent).filter_by(user_id=uid, action_type="internet_read").count() == 1
    print("[PASS] Chinese Internet round: comprehension + listening + glossary words, graded and logged")

    # ---- Passport: a brand-new learner has no invented abilities
    nid, nh = register(client, "freshpass")
    before = counts(nid)
    p = expect(client, "get", "/api/passport", 200, headers=nh)
    assert all(c["band"] == "none" for c in p["capabilities"])
    assert all(w["status"] == "not_yet" for w in p["world"])
    assert [e["kind"] for e in p["timeline"]] == ["joined"]
    assert p["hsk"]["level"] == 1 and p["hsk"]["vocab"]["total"] > 0 and p["recommendations"]
    assert counts(nid) == before, "passport must be read-only"
    print("[PASS] new learner passport: no evidence -> no claimed ability, story starts at joining, read-only")

    # ---- evidence: a real scene, a real practice round
    sc = expect(client, "post", "/api/practice/sessions", 201, headers=nh, json={"source": "scene", "scene": "restaurant"})
    play(client, nh, sc)
    vr = expect(client, "post", "/api/practice/sessions", 201, headers=nh, json={"source": "vocab", "hsk_level": 1, "size": 12})
    play(client, nh, vr)
    p = expect(client, "get", "/api/passport", 200, headers=nh)
    caps = {c["code"]: c for c in p["capabilities"]}
    assert caps["vocabulary"]["band"] in ("developing", "strong") and caps["vocabulary"]["stats"]["answers"] >= 8
    assert caps["vocabulary"]["facts"]["tracked"] > 0
    rest = next(w for w in p["world"] if w["code"] == "restaurant")
    assert rest["status"] == "can_do" and rest["scene"]["slug"] == "restaurant" and rest["scene"]["tier"] == "beginner"
    kinds = [e["kind"] for e in p["timeline"]]
    assert "first_practice" in kinds and "scene_done" in kinds
    assert any(r["kind"] == "world" for r in p["recommendations"])
    print("[PASS] passport evidence comes from real rounds: vocabulary band, restaurant 'can do', story events")

    # ---- timeline truthfulness for count milestones
    with SessionLocal() as db:
        recs = db.query(models.UserVocabulary).filter_by(user_id=nid).all()
        base = datetime.utcnow() - timedelta(days=30)
        for i, r in enumerate(recs[:10]):
            r.status, r.mastery, r.last_reviewed_at = "mastered", 90.0, base + timedelta(days=i)
        db.commit()
        tenth = sorted(r.last_reviewed_at for r in recs[:10])[9] if len(recs) >= 10 else None
    p = expect(client, "get", "/api/passport", 200, headers=nh)
    if tenth:
        ten = next(e for e in p["timeline"] if e["kind"] == "words_mastered" and e["data"]["count"] == 10)
        assert ten["at"] == tenth.isoformat()
        print("[PASS] '10 words mastered' is dated by the review that settled the 10th word (no invented date)")
    ats = [e["at"] for e in p["timeline"]]
    assert ats == sorted(ats)

    # ---- companion references the passport
    mem = expect(client, "get", "/api/companion/memory", 200, headers=nh)
    pm = next((m for m in mem["memories"] if m["kind"] == "passport_milestone"), None)
    assert pm and pm["data"]["event"] in ("scene_done", "chars_mastered", "first_lesson", "words_mastered", "level_started")
    print("[PASS] the companion remembers the newest passport milestone")

    # ---- localization of passport content
    pr = expect(client, "get", "/api/passport", 200, headers={**nh, "X-Locale": "ru"})
    assert pr["hsk"]["level"] == p["hsk"]["level"]
    print("ALL PASSPORT / INTERNET TESTS PASSED")
