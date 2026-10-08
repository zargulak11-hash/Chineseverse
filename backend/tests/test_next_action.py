"""The one next step (services/journey.py) reads the learner's own
records: a pair confused three times comes before new material and names
the two words, known words fading send them to Review (and say how many),
and a book they were just reading is "continue reading" -- each step
carrying the numbers that justify it."""

from datetime import datetime, timedelta

import pytest

from app import models
from app.database import SessionLocal
from helpers import expect, register, unique_name

ROUNDS = "/api/practice/sessions"


@pytest.fixture
def placed(client):
    """A learner past the beginner foundation (HSK 2), as placement would
    leave them: every Learning Compass skill at the same mastery."""
    uid, h = register(client, unique_name("next"))
    expect(client, "get", "/api/journey", 200, headers=h)  # creates the skill rows
    with SessionLocal() as db:
        for s in db.get(models.User, uid).user_skills:
            s.mastery = 20.0
        db.commit()
    assert expect(client, "get", "/api/journey", 200, headers=h)["level"] == 2
    return uid, h


def stored(sid):
    with SessionLocal() as db:
        return db.get(models.PracticeSession, sid).questions


def pick(client, h, sid, index, choice):
    expect(client, "post", f"{ROUNDS}/{sid}/answer", 200, headers=h,
           json={"index": index, "choice_id": choice, "response_ms": 1500})


def word(item_id):
    with SessionLocal() as db:
        return db.get(models.VocabularyWord, item_id).simplified


def test_a_pair_confused_three_times_is_the_next_step(client, placed):
    _, h = placed
    s = expect(client, "post", ROUNDS, 201, headers=h, json={"source": "vocab", "hsk_level": 1, "size": 4})
    q = stored(s["id"])[0]
    target, wrong = q["item_id"], next(o for o in q["option_ids"] if o != q["item_id"])
    pick(client, h, s["id"], 0, wrong)
    assert expect(client, "get", "/api/journey", 200, headers=h)["next"]["kind"] != "mixups"
    for _ in range(2):  # Review brings the word back with its partner; the same mix-up again
        r = expect(client, "post", ROUNDS, 201, headers=h, json={"source": "review"})
        i = next(i for i, q in enumerate(stored(r["id"])) if q["item_id"] == target)
        pick(client, h, r["id"], i, wrong)

    j = expect(client, "get", "/api/journey", 200, headers=h)
    nxt = j["next"]
    assert nxt["kind"] == "mixups" and nxt["to"] == "/practice?source=mixups", nxt
    assert {nxt["a"], nxt["b"]} == {word(target), word(wrong)} and nxt["count"] == 3 and nxt["pairs"] == 1
    # The drill is the next step, so today's plan doesn't list it twice.
    assert [t["key"] for t in j["today"]["tasks"]].count("mixups") == 0


def test_known_words_fading_send_the_learner_to_review(client, placed):
    uid, h = placed
    words = expect(client, "get", "/api/vocab?hsk_level=1", 200, headers=h)[:3]
    now = datetime.utcnow()
    with SessionLocal() as db:
        for w in words:
            db.add(models.UserVocabulary(user_id=uid, word_id=w["id"], status="mastered", mastery=90.0,
                                         times_seen=4, times_missed=0, last_reviewed_at=now - timedelta(days=30),
                                         next_review_at=now - timedelta(days=6)))
        db.commit()
    nxt = expect(client, "get", "/api/journey", 200, headers=h)["next"]
    # Only 3 items are due -- under the usual backlog -- but all three were known.
    assert (nxt["kind"], nxt["count"], nxt["slipping"]) == ("review", 3, 3), nxt


def test_a_book_just_being_read_is_continued(client, placed):
    uid, h = placed
    lib = expect(client, "get", "/api/stories", 200, headers=h)
    book = next(b for b in lib["books"] if b["level"] == 1)
    with SessionLocal() as db:
        db.add(models.StoryProgress(user_id=uid, slug=book["slug"], chapter=1, position=3, chapters_done=[0],
                                    looked_up={}, updated_at=datetime.utcnow()))
        db.commit()
    nxt = expect(client, "get", "/api/journey", 200, headers=h)["next"]
    assert nxt["kind"] == "continue" and nxt["to"] == f"/stories/{book['slug']}/read/2" and nxt["chapter"] == 2, nxt
    # Not reading anything for a week: the lesson path leads again.
    with SessionLocal() as db:
        row = db.query(models.StoryProgress).filter_by(user_id=uid).one()
        row.updated_at = datetime.utcnow() - timedelta(days=7)
        db.commit()
    j = expect(client, "get", "/api/journey", 200, headers=h)
    assert j["next"]["kind"] == "lesson", j["next"]
    # ... and today's plan still leads back into the book.
    read = next(t for t in j["today"]["tasks"] if t["key"] == "read")
    assert read["to"] == f"/stories/{book['slug']}/read/2" and read["book"], read


def test_a_brand_new_learner_starts_with_the_foundation(client):
    _, h = register(client, unique_name("fresh"))
    nxt = expect(client, "get", "/api/journey", 200, headers=h)["next"]
    assert nxt["kind"] == "foundation" and nxt["key"] == "tones", nxt
