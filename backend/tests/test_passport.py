"""Chinese Internet (content adaptation, word help, graded rounds) and the
learner's journey page -- shown to learners as "My Chinese Journey", built
by services/passport.py: capabilities, evidence and story, all from real
learning and never invented."""

from datetime import datetime, timedelta

import pytest

from app import models
from app.database import SessionLocal
from app.services import sentence as sent
from app.services.internet_content import ITEM_BY_SLUG, ITEMS
from helpers import expect, register as register_only, unique_name


def register(client):
    uid, h = register_only(client, unique_name("reader"))
    expect(client, "get", "/api/dashboard", 200, headers=h)  # skill rows
    return uid, h


def stored(sid):
    with SessionLocal() as db:
        return db.get(models.PracticeSession, sid).questions


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


def know_original_words(uid, slug):
    """Mark every word of an item's original version as mastered; returns their ids."""
    item = ITEM_BY_SLUG[slug]
    with SessionLocal() as db:
        text = "".join(b["text"] for b in item["versions"]["original"])
        ids = {t["word"].id for t in sent.segment(db, text) if t["word"] is not None}
        now = datetime.utcnow()
        for wid in ids:
            db.add(models.UserVocabulary(user_id=uid, word_id=wid, status="mastered", mastery=90.0, times_seen=9,
                                         last_reviewed_at=now - timedelta(days=1), next_review_at=now + timedelta(days=9)))
        db.commit()
    return ids


def mark_weak(uid, simplified):
    with SessionLocal() as db:
        w = db.query(models.VocabularyWord).filter_by(simplified=simplified).order_by(models.VocabularyWord.id).first()
        db.add(models.LearningMistake(user_id=uid, mistake_type="word", reference=simplified, priority=3, occurrences=3,
                                      mastered=False, last_seen_at=datetime.utcnow()))
        db.commit()
        return w.id


def test_internet_and_journey_require_sign_in(client):
    for path in ("/api/internet/feed", "/api/passport", "/api/internet/items/metro-line", "/api/internet/words/1"):
        expect(client, "get", path, 401)
    expect(client, "post", "/api/vocab/1/track", 401)


def test_every_item_version_reads_and_every_answer_key_is_valid(client):
    with SessionLocal() as db:
        for item in ITEMS:
            assert set(item["versions"]) == {"original", "intermediate", "beginner"}
            for v, blocks in item["versions"].items():
                text = "".join(b["text"] for b in blocks)
                assert [t for t in sent.segment(db, text) if t["word"] is not None], (item["slug"], v)
            for q in item["questions"]:
                assert 0 <= q["answer"] < len(q["options"]) and len(set(q["options"])) == len(q["options"])


def test_a_new_learner_is_offered_adapted_versions_in_their_language(client):
    _, h = register(client)
    feed = expect(client, "get", "/api/internet/feed", 200, headers=h)
    assert len(feed["items"]) == 10 and feed["profile"]["level"] == 1
    assert all(i["recommended"] in ("beginner", "intermediate") for i in feed["items"]), [i["recommended"] for i in feed["items"]]
    ru = expect(client, "get", "/api/internet/feed", 200, headers={**h, "X-Locale": "ru"})
    assert ru["items"][0]["summary"] != feed["items"][0]["summary"]


def test_reading_an_item_shows_word_states_and_writes_nothing(client):
    uid, h = register(client)
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


def test_known_vocabulary_moves_the_recommended_version_up(client):
    uid, h = register(client)
    know_original_words(uid, "class-group-chat")
    view = expect(client, "get", "/api/internet/items/class-group-chat", 200, headers=h)
    assert view["recommended"] == "original", view["coverage"]
    # the other items stay adapted
    other = next(i for i in expect(client, "get", "/api/internet/feed", 200, headers=h)["items"] if i["slug"] == "metro-line")
    assert other["recommended"] != "original" or other["coverage"]["ratio"] >= 0.8


def test_a_word_with_an_open_mistake_leads_the_glossary(client):
    uid, h = register(client)
    weak_id = mark_weak(uid, "地铁")
    view = expect(client, "get", "/api/internet/items/metro-line", 200, headers=h)
    assert view["glossary"][0]["word_id"] == weak_id and view["glossary"][0]["weak"]


def test_word_help_and_add_to_review_respect_the_words_state(client):
    uid, h = register(client)
    mastered_id = next(iter(know_original_words(uid, "class-group-chat")))
    weak_id = mark_weak(uid, "地铁")
    view = expect(client, "get", "/api/internet/items/metro-line", 200, headers=h)
    new_word = next(t for t in view["glossary"] if t["status"] == "new" and not t["weak"])
    help1 = expect(client, "get", f"/api/internet/words/{new_word['word_id']}?item=metro-line", 200, headers=h)
    assert help1["can_add"] and help1["add_reason"] == "new" and help1["characters"] and help1["context"]
    assert all(any(c in r["text"] for c in help1["text"]) for r in help1["related"])
    tr1 = expect(client, "post", f"/api/vocab/{new_word['word_id']}/track", 200, headers=h)
    assert tr1["status"] == "learning"
    expect(client, "post", f"/api/vocab/{new_word['word_id']}/track", 409, headers=h)
    help2 = expect(client, "get", f"/api/internet/words/{new_word['word_id']}", 200, headers=h)
    assert not help2["can_add"] and help2["add_reason"] == "in_review" and help2["state"]["mastery"] == 0.0
    help3 = expect(client, "get", f"/api/internet/words/{mastered_id}", 200, headers=h)
    assert not help3["can_add"] and help3["add_reason"] == "mastered"
    expect(client, "post", f"/api/vocab/{mastered_id}/track", 409, headers=h)
    expect(client, "get", "/api/internet/words/999999", 404, headers=h)
    # the context sentence comes from the version being read
    beg = expect(client, "get", f"/api/internet/words/{weak_id}?item=metro-line&version=beginner", 200, headers=h)
    assert beg["context"]["version"] == "beginner", beg["context"]
    with SessionLocal() as db:
        assert db.query(models.ActivityEvent).filter_by(user_id=uid, action_type="word_saved").count() == 1


def test_an_internet_round_is_graded_and_logged(client):
    uid, h = register(client)
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "internet", "item": "hotpot-review"})
    types = [q["type"] for q in s["questions"]]
    assert types.count("net_comprehension") == 3 and "net_listen" in types
    assert s["context"]["kind"] == "internet" and s["context"]["slug"] == "hotpot-review"
    expect(client, "post", "/api/practice/sessions", 404, headers=h, json={"source": "internet", "item": "zzz"})
    fin = play(client, h, s)
    assert fin["score"] == 100 and fin["reaction"]["event"] == "internet_complete"
    with SessionLocal() as db:
        assert db.query(models.ActivityEvent).filter_by(user_id=uid, action_type="internet_read").count() == 1


def test_a_new_learners_journey_claims_no_ability_and_is_read_only(client):
    nid, nh = register(client)
    before = counts(nid)
    p = expect(client, "get", "/api/passport", 200, headers=nh)
    assert all(c["band"] == "none" for c in p["capabilities"])
    assert all(w["status"] == "not_yet" for w in p["world"])
    assert [e["kind"] for e in p["timeline"]] == ["joined"]
    assert p["hsk"]["level"] == 1 and p["hsk"]["vocab"]["total"] > 0 and p["recommendations"]
    assert counts(nid) == before, "the journey page must be read-only"


@pytest.fixture(scope="module")
def evidenced(client):
    """A learner who has really played the restaurant scene and a vocabulary round."""
    nid, nh = register(client)
    play(client, nh, expect(client, "post", "/api/practice/sessions", 201, headers=nh,
                            json={"source": "scene", "scene": "restaurant"}))
    play(client, nh, expect(client, "post", "/api/practice/sessions", 201, headers=nh,
                            json={"source": "vocab", "hsk_level": 1, "size": 12}))
    return nid, nh


def test_journey_evidence_comes_from_real_rounds(client, evidenced):
    _, nh = evidenced
    p = expect(client, "get", "/api/passport", 200, headers=nh)
    caps = {c["code"]: c for c in p["capabilities"]}
    assert caps["vocabulary"]["band"] in ("developing", "strong") and caps["vocabulary"]["stats"]["answers"] >= 8
    assert caps["vocabulary"]["facts"]["tracked"] > 0
    rest = next(w for w in p["world"] if w["code"] == "restaurant")
    assert rest["status"] == "can_do" and rest["scene"]["slug"] == "restaurant" and rest["scene"]["tier"] == "beginner"
    kinds = [e["kind"] for e in p["timeline"]]
    assert "first_practice" in kinds and "scene_done" in kinds
    assert any(r["kind"] == "world" for r in p["recommendations"])
    # localized content keeps the same facts
    pr = expect(client, "get", "/api/passport", 200, headers={**nh, "X-Locale": "ru"})
    assert pr["hsk"]["level"] == p["hsk"]["level"]


def test_count_milestones_are_dated_by_the_real_review(client, evidenced):
    nid, nh = evidenced
    with SessionLocal() as db:
        recs = db.query(models.UserVocabulary).filter_by(user_id=nid).all()
        assert len(recs) >= 10, "the vocabulary round tracked at least 10 words"
        base = datetime.utcnow() - timedelta(days=30)
        for i, r in enumerate(recs[:10]):
            r.status, r.mastery, r.last_reviewed_at = "mastered", 90.0, base + timedelta(days=i)
        db.commit()
        tenth = sorted(r.last_reviewed_at for r in recs[:10])[9]
    p = expect(client, "get", "/api/passport", 200, headers=nh)
    # '10 words mastered' is dated by the review that settled the 10th word (no invented date)
    ten = next(e for e in p["timeline"] if e["kind"] == "words_mastered" and e["data"]["count"] == 10)
    assert ten["at"] == tenth.isoformat()
    ats = [e["at"] for e in p["timeline"]]
    assert ats == sorted(ats)


def test_the_companion_remembers_the_newest_journey_milestone(client, evidenced):
    _, nh = evidenced
    mem = expect(client, "get", "/api/companion/memory", 200, headers=nh)
    pm = next((m for m in mem["memories"] if m["kind"] == "passport_milestone"), None)
    assert pm and pm["data"]["event"] in ("scene_done", "chars_mastered", "first_lesson", "words_mastered", "level_started")
