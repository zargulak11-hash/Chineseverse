"""Real 1-vs-1 duels through the HTTP API.

Registered accounts challenge, accept and play; the server alone builds
the questions, times each player's own clock, grades, and decides the
winner. The clock used by the duel service is replaced by a controllable
one so timeouts, independent clocks and expiry are tested exactly, without
sleeping. The concurrent double-submit check runs on SQLite here; on
PostgreSQL the same path is serialized by SELECT ... FOR UPDATE.
"""

import threading
from datetime import datetime, timedelta
from types import SimpleNamespace as P

import pytest

from app import models
from app.database import SessionLocal
from app.services import duel as duel_svc
from helpers import expect, register, unique_name


class Clock:
    def __init__(self):
        self.t = datetime.utcnow()

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += timedelta(seconds=seconds)


@pytest.fixture
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(duel_svc, "_now", c)
    return c


@pytest.fixture
def players(client):
    """players(n) -> [(user_id, headers), ...] with skill rows."""
    def make(n):
        out = []
        for _ in range(n):
            uid, h = register(client, unique_name("duelist"))
            expect(client, "get", "/api/dashboard", 200, headers=h)  # skill rows
            out.append((uid, h))
        return out
    return make


def stored_questions(duel_id):
    with SessionLocal() as db:
        return db.get(models.Duel, duel_id).question_data["questions"]


def right(duel_id, i):
    return stored_questions(duel_id)[i]["item_id"]


def wrong(duel_id, i):
    q = stored_questions(duel_id)[i]
    return next(o for o in q["option_ids"] if o != q["item_id"])


def notes(client, h):
    return expect(client, "get", "/api/notifications?limit=50", 200, headers=h)


def test_opponents_come_from_the_social_graph_and_bad_challenges_are_refused(client):
    a_id, A = register(client, "alice_pick")
    b_id, B = register(client, "bob_pick")
    c_id, C = register(client, "carol_pick")
    for h in (A, B, C):
        expect(client, "get", "/api/dashboard", 200, headers=h)  # skill rows
    expect(client, "post", f"/api/users/{b_id}/follow", 201, headers=A)
    ops = expect(client, "get", "/api/duels/opponents", 200, headers=A)
    names = [o["username"] for o in ops["opponents"]]
    assert names == ["bob_pick"], names  # social graph only, never self
    assert "carol_pick" in [o["username"] for o in expect(client, "get", "/api/duels/opponents?q=carol_pick", 200, headers=A)["opponents"]]
    assert "alice_pick" not in [o["username"] for o in expect(client, "get", "/api/duels/opponents?q=alice_pick", 200, headers=A)["opponents"]]
    expect(client, "get", "/api/duels/opponents", 401)
    # opponents come from the social graph / search, never yourself, auth required

    assert expect(client, "post", "/api/duels", 400, headers=A, json={"opponent_id": a_id})["code"] == "cannot_challenge_self"
    assert expect(client, "post", "/api/duels", 404, headers=A, json={"opponent_id": 999999})["code"] == "opponent_not_found"
    expect(client, "post", "/api/duels", 422, headers=A, json={"opponent_id": b_id, "hsk_level": 12})
    err = expect(client, "post", "/api/duels", 400, headers=A, json={"opponent_id": a_id})
    assert err == {"detail": "You cannot challenge yourself", "code": "cannot_challenge_self"}, err
    # self / nonexistent / invalid-level challenges are refused with a readable detail + code


def test_full_duel_lifecycle_between_two_players(client, clock):
    a_id, A = register(client, "alice_duel")
    b_id, B = register(client, "bob_duel")
    c_id, C = register(client, "carol_duel")
    for h in (A, B, C):
        expect(client, "get", "/api/dashboard", 200, headers=h)  # skill rows
    with SessionLocal() as db:
        duels_before = db.query(models.Duel).count() + 1
    d = expect(client, "post", "/api/duels", 201, headers=A, json={"opponent_id": b_id, "hsk_level": 1})
    did = d["id"]
    assert d["status"] == "pending" and d["my_role"] == "challenger" and d["can_cancel"] and not d["can_accept"]
    assert d["current"] is None and d["opponent"]["username"] == "bob_duel"
    with SessionLocal() as db:
        row = db.get(models.Duel, did)
        assert row.created_at and row.expires_at and row.status == "pending"
        assert {(p.user_id, p.role) for p in row.participants} == {(a_id, "challenger"), (b_id, "opponent")}
        qs = row.question_data["questions"]
        assert len(qs) == duel_svc.QUESTION_COUNT
        for q in qs:  # real curriculum rows
            model = {"vocab": models.VocabularyWord, "hanzi": models.Hanzi, "grammar": models.GrammarTopic}[q["item_type"]]
            assert db.get(model, q["item_id"]) is not None and q["item_id"] in q["option_ids"]
    n = [x for x in notes(client, B) if x["type"] == "duel_challenge"]
    assert len(n) == 1 and n[0]["actor"]["id"] == a_id and n[0]["link"] == f"/duels/{did}" and not n[0]["read"]
    assert expect(client, "post", "/api/duels", 409, headers=A, json={"opponent_id": b_id})["code"] == "duel_already_open"
    assert expect(client, "post", "/api/duels", 409, headers=B, json={"opponent_id": a_id})["code"] == "duel_already_open"
    # challenge stored with both players, real questions, in-app notification; one open duel per pair

    expect(client, "get", f"/api/duels/{did}", 404, headers=C)
    for action in ("accept", "decline", "cancel", "start", "forfeit"):
        expect(client, "post", f"/api/duels/{did}/{action}", 404, headers=C)
    expect(client, "post", f"/api/duels/{did}/answer", 404, headers=C, json={"index": 0, "choice_id": 1})
    expect(client, "get", f"/api/duels/{did}", 401)
    assert expect(client, "post", f"/api/duels/{did}/accept", 403, headers=A)["code"] == "not_allowed"  # challenger can't accept
    assert expect(client, "post", f"/api/duels/{did}/cancel", 403, headers=B)["code"] == "not_allowed"
    assert expect(client, "post", f"/api/duels/{did}/start", 409, headers=A)["code"] == "not_active_pending"
    expect(client, "post", f"/api/duels/{did}/answer", 409, headers=A, json={"index": 0, "choice_id": right(did, 0)})
    assert all(did != x["id"] for x in expect(client, "get", "/api/duels", 200, headers=C))
    # outsiders get 404 on every duel route; roles enforced; no play before acceptance

    d = expect(client, "post", f"/api/duels/{did}/accept", 200, headers=B)
    assert d["status"] == "active" and d["play_deadline"]
    assert expect(client, "post", f"/api/duels/{did}/accept", 409, headers=B)["code"] == "not_pending_active"
    assert [x for x in notes(client, B) if x["type"] == "duel_challenge"][0]["read"] is True
    acc = [x for x in notes(client, A) if x["type"] == "duel_accepted"]
    assert len(acc) == 1 and acc[0]["actor"]["id"] == b_id
    da = expect(client, "get", f"/api/duels/{did}", 200, headers=A)
    db_ = expect(client, "get", f"/api/duels/{did}", 200, headers=B)
    assert da["id"] == db_["id"] == did and da["status"] == db_["status"] == "active"
    assert da["current"] is None and da["me"]["remaining_ms"] == duel_svc.TIME_LIMIT_SECONDS * 1000  # clock not started
    # accept activates the same duel for both; challenger notified

    sa = expect(client, "post", f"/api/duels/{did}/start", 200, headers=A)
    clock.advance(1)
    sb = expect(client, "post", f"/api/duels/{did}/start", 200, headers=B)
    assert sa["current"]["index"] == sb["current"]["index"] == 0
    assert [o["id"] for o in sa["current"]["options"]] == [o["id"] for o in sb["current"]["options"]]
    assert sa["current"]["answer"] is None and "correct_id" not in str(sa["current"])
    assert sa["review"] is None
    ru = expect(client, "get", f"/api/duels/{did}", 200, headers={**B, "X-Locale": "ru"})
    assert [o["id"] for o in ru["current"]["options"]] == [o["id"] for o in sb["current"]["options"]]
    # both players get the identical question/options; correct answer not sent; localized per viewer

    a_remaining_0 = expect(client, "get", f"/api/duels/{did}", 200, headers=A)["me"]["remaining_ms"]
    b_remaining_0 = expect(client, "get", f"/api/duels/{did}", 200, headers=B)["me"]["remaining_ms"]
    assert a_remaining_0 == 149_000 and b_remaining_0 == 150_000, (a_remaining_0, b_remaining_0)

    clock.advance(2)  # A answers 3s after starting
    r = expect(client, "post", f"/api/duels/{did}/answer", 200, headers=A, json={"index": 0, "choice_id": right(did, 0)})
    assert r["answer"]["correct"] is True and r["answer"]["response_ms"] == 3000
    assert "correct_id" not in r["answer"]  # no answer key while the duel runs
    assert r["answer"]["points"] == 10 + round((1 - 3000 / 6000) * 8)
    assert r["duel"]["me"]["remaining_ms"] == 147_000
    assert r["duel"]["opponent"]["answered"] == 0 and "score" not in r["duel"]["opponent"]
    b_view = expect(client, "get", f"/api/duels/{did}", 200, headers=B)
    assert b_view["me"]["remaining_ms"] == 148_000, b_view["me"]["remaining_ms"]  # only real time passed for B
    assert b_view["me"]["answered"] == 0 and b_view["me"]["score"] == 0 and b_view["current"]["index"] == 0
    assert b_view["opponent"]["answered"] == 1 and "correct" not in b_view["opponent"]  # private until the end

    clock.advance(4)  # B answers 7s after starting, wrong
    r = expect(client, "post", f"/api/duels/{did}/answer", 200, headers=B, json={"index": 0, "choice_id": wrong(did, 0)})
    assert r["answer"]["correct"] is False and r["answer"]["response_ms"] == 6000 and r["answer"]["points"] == 2
    assert r["duel"]["me"]["remaining_ms"] == 144_000
    a_view = expect(client, "get", f"/api/duels/{did}", 200, headers=A)
    assert a_view["me"]["remaining_ms"] == 143_000  # A's clock never paused or reset
    assert a_view["me"]["score"] == 14 and a_view["me"]["correct"] == 1
    with SessionLocal() as db:
        ps = {p.user_id: p for p in db.get(models.Duel, did).participants}
        assert (ps[a_id].score, ps[a_id].correct_count) == (14, 1)
        assert (ps[b_id].score, ps[b_id].correct_count) == (2, 0)
        w = db.get(models.VocabularyWord, stored_questions(did)[0]["item_id"]) if stored_questions(did)[0]["item_type"] == "vocab" else None
        if w is not None:  # B's wrong answer became a real learning mistake
            assert db.query(models.LearningMistake).filter_by(user_id=b_id, reference=w.simplified).first() is not None
    # scores, correctness and remaining time are independent per player and server-timed

    assert expect(client, "post", f"/api/duels/{did}/answer", 409, headers=A, json={"index": 0, "choice_id": right(did, 0)})["code"] == "already_answered"
    assert expect(client, "post", f"/api/duels/{did}/answer", 409, headers=A, json={"index": 3, "choice_id": right(did, 3)})["code"] == "out_of_order"
    assert expect(client, "post", f"/api/duels/{did}/answer", 422, headers=A, json={"index": 1, "choice_id": -7})["code"] == "invalid_option"
    # re-answering, skipping ahead and foreign options are refused

    # client-sent score / correctness / time / winner are ignored
    clock.advance(1)
    r = expect(client, "post", f"/api/duels/{did}/answer", 200, headers=A, json={
        "index": 1, "choice_id": wrong(did, 1), "score": 9999, "correct": True,
        "remaining_time": 150000, "response_time_ms": 1, "winner": "alice_duel", "user_id": b_id,
    })
    assert r["answer"]["correct"] is False and r["answer"]["points"] == 2 and r["duel"]["me"]["score"] == 16
    with SessionLocal() as db:
        assert db.query(models.DuelAnswer).filter_by(duel_id=did, user_id=b_id).count() == 1  # B untouched
    # score/correctness/time/winner/player id from the client are ignored

    # double click: two concurrent submits for the same question -> scored once
    results = []

    barrier = threading.Barrier(4)

    def submit():
        # Each thread is its own request: own DB session, same question.
        with SessionLocal() as db:
            bob = db.get(models.User, b_id)
            barrier.wait()
            try:
                duel = duel_svc.load_for(db, did, bob)
                duel_svc.answer(db, duel, bob, 1, right(did, 1))
                results.append("ok")
            except duel_svc.DuelError as exc:
                results.append(exc.code)
            except Exception as exc:  # e.g. SQLite "database is locked" under contention
                results.append(type(exc).__name__)

    threads = [threading.Thread(target=submit) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(results) == 4 and results.count("ok") == 1, results
    assert all(r == "already_answered" for r in results if r != "ok"), results
    with SessionLocal() as db:
        assert db.query(models.DuelAnswer).filter_by(duel_id=did, user_id=b_id, question_index=1).count() == 1
        p = next(p for p in db.get(models.Duel, did).participants if p.user_id == b_id)
        assert p.answered == 2 and p.correct_count == 1
    # concurrent duplicate submissions (double click / two tabs) score exactly once

    before = expect(client, "get", f"/api/duels/{did}", 200, headers=A)
    again = expect(client, "post", f"/api/duels/{did}/start", 200, headers=A)  # reopening never restarts the clock
    assert again["me"]["remaining_ms"] == before["me"]["remaining_ms"]
    assert again["current"]["index"] == before["current"]["index"] == 2
    clock.advance(30)  # tab closed for 30s: the clock kept running
    back = expect(client, "get", f"/api/duels/{did}", 200, headers=A)
    assert back["me"]["remaining_ms"] == before["me"]["remaining_ms"] - 30_000
    assert back["me"]["score"] == 16 and back["current"]["index"] == 2
    with SessionLocal() as db:
        assert db.query(models.Duel).count() == duels_before  # no new duel was created
    # refresh / reopen / second tab restore the same state and a still-running clock

    total = duel_svc.QUESTION_COUNT
    for i in range(2, total):
        clock.advance(2)
        r = expect(client, "post", f"/api/duels/{did}/answer", 200, headers=A, json={"index": i, "choice_id": right(did, i)})
    assert r["duel"]["me"]["finished"] and r["duel"]["me"]["finish_reason"] == "completed"
    assert r["duel"]["status"] == "active" and r["duel"]["result"] is None and r["duel"]["review"] is None
    assert r["duel"]["current"] is None
    assert expect(client, "post", f"/api/duels/{did}/answer", 409, headers=A, json={"index": 0, "choice_id": right(did, 0)})["code"] == "already_finished"
    a_mid = expect(client, "get", f"/api/duels/{did}", 200, headers=A)
    assert "score" not in a_mid["opponent"]  # no result while the opponent still plays
    # first finisher waits; no result, no peeking at the opponent's score or the answer key

    b_now = expect(client, "get", f"/api/duels/{did}", 200, headers=B)
    assert not b_now["me"]["finished"] and b_now["me"]["remaining_ms"] > 0
    clock.advance(b_now["me"]["remaining_ms"] / 1000 + 2)  # past B's own deadline (+ grace)
    assert expect(client, "post", f"/api/duels/{did}/answer", 409, headers=B, json={"index": 2, "choice_id": right(did, 2)})["code"] in ("time_up", "not_active_completed")

    fa = expect(client, "get", f"/api/duels/{did}", 200, headers=A)
    fb = expect(client, "get", f"/api/duels/{did}", 200, headers=B)
    assert fa["status"] == fb["status"] == "completed"
    assert fb["me"]["finish_reason"] == "timeout" and fb["me"]["time_used_ms"] == 150_000
    assert fb["me"]["answered"] == 2  # earlier answers preserved
    assert fa["result"] == {"outcome": "win", "winner_id": a_id, "decided_by": "correct"}
    assert fb["result"]["outcome"] == "loss" and fb["result"]["winner_id"] == a_id
    assert fa["opponent"]["score"] == fb["me"]["score"] and fb["opponent"]["score"] == fa["me"]["score"]
    with SessionLocal() as db:
        ans = db.query(models.DuelAnswer).filter_by(duel_id=did, user_id=a_id).all()
        p = next(p for p in db.get(models.Duel, did).participants if p.user_id == a_id)
        assert p.score == sum(a.points for a in ans) and p.correct_count == sum(1 for a in ans if a.correct)
        assert db.get(models.Duel, did).winner_id == a_id
    assert len(fa["review"]) == total and fa["review"][0]["answer"]["correct_id"] == right(did, 0)
    # B never answered these: still shown with the correct answer, no choice
    assert all(q["answer"]["choice_id"] is None and q["answer"]["correct_id"] == right(did, q["index"]) for q in fb["review"][2:])
    assert any(x["type"] == "duel_completed" for x in notes(client, A))
    assert any(x["type"] == "duel_completed" for x in notes(client, B))
    # timeout finishes only B; result computed from stored answers and shown to both

    # the list shows the finished duel without question content
    lst = expect(client, "get", "/api/duels", 200, headers=A)
    assert {x["id"]: x["status"] for x in lst}[did] == "completed"
    assert all(x["current"] is None and x["review"] is None for x in lst)
    # completion is a real activity for BOTH players (not only the winner)
    with SessionLocal() as db:
        for uid in (a_id, b_id):
            assert db.query(models.ActivityEvent).filter_by(user_id=uid, action_type="duel_finish").count() == 1


def test_opponent_finishes_first_then_equal_correct_answers_go_to_score(client, clock, players):
    (a_id, A), (b_id, B) = players(2)
    d2 = expect(client, "post", "/api/duels", 201, headers=B, json={"opponent_id": a_id, "hsk_level": 2, "focus": "hanzi"})
    d2id = d2["id"]
    assert all(q["item_type"] == "hanzi" for q in stored_questions(d2id))
    expect(client, "post", f"/api/duels/{d2id}/accept", 200, headers=A)
    expect(client, "post", f"/api/duels/{d2id}/start", 200, headers=A)  # opponent (A here) starts first
    clock.advance(10)
    expect(client, "post", f"/api/duels/{d2id}/start", 200, headers=B)
    n2 = len(stored_questions(d2id))
    for i in range(n2):  # A: all correct but slow
        clock.advance(5)
        expect(client, "post", f"/api/duels/{d2id}/answer", 200, headers=A, json={"index": i, "choice_id": right(d2id, i)})
    mid = expect(client, "get", f"/api/duels/{d2id}", 200, headers=B)
    assert mid["status"] == "active" and mid["opponent"]["finished"] and "score" not in mid["opponent"]
    for i in range(n2):  # B: all correct and fast -> same correct count, higher score
        clock.advance(1)
        expect(client, "post", f"/api/duels/{d2id}/answer", 200, headers=B, json={"index": i, "choice_id": right(d2id, i)})
    rb = expect(client, "get", f"/api/duels/{d2id}", 200, headers=B)
    assert rb["status"] == "completed" and rb["result"] == {"outcome": "win", "winner_id": b_id, "decided_by": "score"}
    assert expect(client, "get", f"/api/duels/{d2id}", 200, headers=A)["result"]["outcome"] == "loss"
    # opponent finishing first, then me: equal correct answers -> decided by score

    with SessionLocal() as db:
        for uid in (a_id, b_id):
            assert db.query(models.ActivityEvent).filter_by(user_id=uid, action_type="duel_finish").count() == 1


def test_decline_and_cancel_leave_no_ghost_duel(client, clock, players):
    (a_id, A), (c_id, C) = players(2)
    d3 = expect(client, "post", "/api/duels", 201, headers=A, json={"opponent_id": c_id})
    d3id = d3["id"]
    r = expect(client, "post", f"/api/duels/{d3id}/decline", 200, headers=C)
    assert r["status"] == "declined" and r["current"] is None and r["review"] is None
    assert expect(client, "post", f"/api/duels/{d3id}/start", 409, headers=C)["code"] == "not_active_declined"
    assert expect(client, "post", f"/api/duels/{d3id}/accept", 409, headers=C)["code"] == "not_pending_declined"
    assert [x for x in notes(client, A) if x["type"] == "duel_declined" and x["duel_id"] == d3id]
    d3b = expect(client, "post", "/api/duels", 201, headers=A, json={"opponent_id": c_id})  # no ghost duel blocks a new one
    # decline ends the challenge, notifies the challenger, leaves no ghost active duel

    # cancel by the challenger
    r = expect(client, "post", f"/api/duels/{d3b['id']}/cancel", 200, headers=A)
    assert r["status"] == "cancelled"
    assert expect(client, "post", f"/api/duels/{d3b['id']}/accept", 409, headers=C)["code"] == "not_pending_cancelled"
    assert [x for x in notes(client, C) if x["duel_id"] == d3b["id"]][0]["read"] is True
    # challenger can cancel a pending challenge; it can no longer be accepted

    statuses = {x["id"]: x["status"] for x in expect(client, "get", "/api/duels", 200, headers=A)}
    assert statuses[d3id] == "declined" and statuses[d3b["id"]] == "cancelled"


def test_an_unanswered_challenge_expires(client, clock, players):
    (a_id, A), (c_id, C) = players(2)
    d4 = expect(client, "post", "/api/duels", 201, headers=C, json={"opponent_id": a_id})
    clock.advance(duel_svc.CHALLENGE_TTL.total_seconds() + 1)
    assert expect(client, "get", f"/api/duels/{d4['id']}", 200, headers=A)["status"] == "expired"
    assert expect(client, "post", f"/api/duels/{d4['id']}/accept", 409, headers=A)["code"] == "not_pending_expired"
    # an unanswered challenge expires and can't be accepted

    statuses = {x["id"]: x["status"] for x in expect(client, "get", "/api/duels", 200, headers=A)}
    assert statuses[d4["id"]] == "expired"


def test_forfeit_ends_only_my_attempt_and_a_no_show_is_finished(client, clock, players):
    (a_id, A), (c_id, C) = players(2)
    # no-show: accepted but one player never starts within the play window
    d5 = expect(client, "post", "/api/duels", 201, headers=C, json={"opponent_id": a_id})
    expect(client, "post", f"/api/duels/{d5['id']}/accept", 200, headers=A)
    expect(client, "post", f"/api/duels/{d5['id']}/start", 200, headers=C)
    clock.advance(3)
    expect(client, "post", f"/api/duels/{d5['id']}/answer", 200, headers=C, json={"index": 0, "choice_id": right(d5["id"], 0)})
    expect(client, "post", f"/api/duels/{d5['id']}/forfeit", 200, headers=C)  # C stops early
    r = expect(client, "get", f"/api/duels/{d5['id']}", 200, headers=C)
    assert r["status"] == "active" and r["me"]["finish_reason"] == "forfeit"
    clock.advance(duel_svc.PLAY_WINDOW.total_seconds() + 1)
    r = expect(client, "get", f"/api/duels/{d5['id']}", 200, headers=A)
    assert r["status"] == "completed" and r["me"]["finish_reason"] == "no_show" and r["result"]["outcome"] == "loss"
    # forfeit ends only my attempt; a player who never starts is finished as no-show

    with SessionLocal() as db:
        assert db.query(models.ActivityEvent).filter_by(user_id=a_id, action_type="duel_finish").count() == 1


def test_winner_rule_is_symmetric():
    # correct > score > less time > draw, independent of player order
    x = P(correct_count=5, score=60, time_used_ms=90_000, user_id=1)
    y = P(correct_count=5, score=60, time_used_ms=90_000, user_id=2)
    assert duel_svc.decide(x, y) == (None, "draw") and duel_svc.decide(y, x) == (None, "draw")
    y.time_used_ms = 80_000
    assert duel_svc.decide(x, y) == (y, "time") and duel_svc.decide(y, x) == (y, "time")
    y.score = 50
    assert duel_svc.decide(x, y) == (x, "score") and duel_svc.decide(y, x) == (x, "score")
    y.correct_count = 6
    assert duel_svc.decide(x, y) == (y, "correct") and duel_svc.decide(y, x) == (y, "correct")
