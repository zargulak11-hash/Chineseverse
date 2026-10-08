"""Slipping (services/srs.is_slipping): a word the learner KNEW (reviewing
or mastered) that is SLIP_AFTER past its review date is reported as
slipping -- on its vocabulary card and in the journey's count -- while a
word only just due, or one never known, is not. Nothing is downgraded."""

from datetime import datetime, timedelta

from app import models
from app.database import SessionLocal
from helpers import expect, register, unique_name


def test_known_words_long_past_review_are_slipping(client):
    uid, h = register(client, unique_name("slip"))
    words = expect(client, "get", "/api/vocab?hsk_level=1", 200, headers=h)[:4]
    now = datetime.utcnow()
    states = [  # (status, mastery, review due this long ago)
        ("mastered", 90.0, timedelta(days=5)),   # knew it, 5 days late -> slipping
        ("reviewing", 60.0, timedelta(days=1)),  # knew it, only just due -> due, not slipping
        ("learning", 30.0, timedelta(days=10)),  # never really knew it -> due, not slipping
        ("mastered", 95.0, -timedelta(days=4)),  # review is in the future -> neither
    ]
    with SessionLocal() as db:
        for w, (status, mastery, ago) in zip(words, states):
            db.add(models.UserVocabulary(user_id=uid, word_id=w["id"], status=status, mastery=mastery,
                                         times_seen=3, times_missed=0, last_reviewed_at=now - timedelta(days=20),
                                         next_review_at=now - ago))
        db.commit()

    listed = {w["id"]: w for w in expect(client, "get", "/api/vocab?hsk_level=1", 200, headers=h)}
    got = [(listed[w["id"]]["due_for_review"], listed[w["id"]]["slipping"], listed[w["id"]]["status"]) for w in words]
    assert got == [(True, True, "mastered"), (True, False, "reviewing"), (True, False, "learning"),
                   (False, False, "mastered")], got
    assert expect(client, "get", "/api/journey", 200, headers=h)["slipping"] == 1
