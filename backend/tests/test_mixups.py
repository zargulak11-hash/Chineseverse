"""Mix-up memory (services/mixups.py): a wrong pick between two curriculum
items is remembered as a pair, the notebook shows it, every round puts the
partner back among the options, the drill asks each item with the other on
screen, and telling them apart RESOLVE_AFTER times resolves the pair. Also:
the wrong answer itself now reaches the mistake notebook."""

import pytest

from app import models
from app.database import SessionLocal
from app.services import mixups
from helpers import expect, register, unique_name

ROUNDS = "/api/practice/sessions"


@pytest.fixture
def learner(client):
    return register(client, unique_name("mixer"))


def stored(sid):
    with SessionLocal() as db:
        return db.get(models.PracticeSession, sid).questions


def answer(client, h, sid, index, choice):
    return expect(client, "post", f"{ROUNDS}/{sid}/answer", 200, headers=h,
                  json={"index": index, "choice_id": choice, "response_ms": 1500})


def word(item_id):
    with SessionLocal() as db:
        return db.get(models.VocabularyWord, item_id).simplified


def confuse_once(client, h):
    """A vocabulary round whose first question is answered with a wrong
    option. Returns (target id, picked id)."""
    s = expect(client, "post", ROUNDS, 201, headers=h, json={"source": "vocab", "hsk_level": 1, "size": 4})
    q = stored(s["id"])[0]
    wrong = next(o for o in q["option_ids"] if o != q["item_id"])
    answer(client, h, s["id"], 0, wrong)
    return q["item_id"], wrong, q["type"]


def test_the_wrong_choice_is_kept_in_the_notebook(client, learner):
    _, h = learner
    target, wrong, _ = confuse_once(client, h)
    notebook = expect(client, "get", "/api/mistakes", 200, headers=h)
    m = next(m for m in notebook if m["reference"] == word(target))
    assert m["answer_given"] and m["answer_given"].startswith(word(wrong)), m


def test_a_mixed_up_partner_comes_back_among_the_options(client, learner):
    uid, h = learner
    target, wrong, _ = confuse_once(client, h)
    with SessionLocal() as db:
        assert mixups.partners_by_item(db, db.get(models.User, uid))[("vocab", target)] == [wrong]
    # One mix-up is not a notebook entry yet (it may have been a guess).
    assert expect(client, "get", "/api/mistakes/mixups", 200, headers=h) == {"active": [], "resolved": []}
    # Review brings the missed word back -- with the word it was taken for.
    review = expect(client, "post", ROUNDS, 201, headers=h, json={"source": "review"})
    q = next(q for q in stored(review["id"]) if q["item_id"] == target)
    assert wrong in q["option_ids"], q


def test_mixed_up_twice_is_drilled_until_told_apart(client, learner):
    uid, h = learner
    target, wrong, qtype = confuse_once(client, h)
    review = expect(client, "post", ROUNDS, 201, headers=h, json={"source": "review"})
    idx, q = next((i, q) for i, q in enumerate(stored(review["id"])) if q["item_id"] == target)
    answer(client, h, review["id"], idx, wrong)  # the same mix-up again

    pairs = expect(client, "get", "/api/mistakes/mixups", 200, headers=h)
    assert len(pairs["active"]) == 1 and pairs["resolved"] == []
    p = pairs["active"][0]
    assert {p["a"]["hanzi"], p["b"]["hanzi"]} == {word(target), word(wrong)}
    assert (p["confused"], p["told_apart"], p["status"]) == (2, 0, "active")

    # Today's plan offers the drill.
    tasks = expect(client, "get", "/api/journey", 200, headers=h)["today"]["tasks"]
    assert any(t["key"] == "mixups" and t["to"] == "/practice?source=mixups" and t["count"] == 1 for t in tasks), tasks

    # The drill: each of the two asked with the other on screen, in the
    # question type the mix-up happened in.
    told = 0
    for _ in range(2):
        drill = expect(client, "post", ROUNDS, 201, headers=h, json={"source": "mixups"})
        qs = stored(drill["id"])
        assert sorted(q["item_id"] for q in qs) == sorted((target, wrong))
        for i, q in enumerate(qs):
            partner = wrong if q["item_id"] == target else target
            assert partner in q["option_ids"] and q["type"] == qtype, q
            answer(client, h, drill["id"], i, q["item_id"])
            told += 1
        expect(client, "post", f"{ROUNDS}/{drill['id']}/complete", 200, headers=h)

    pairs = expect(client, "get", "/api/mistakes/mixups", 200, headers=h)
    assert pairs["active"] == [] and pairs["resolved"][0]["told_apart"] == told >= mixups.RESOLVE_AFTER
    # Nothing left to drill, and the partner is no longer forced into rounds.
    assert expect(client, "post", ROUNDS, 200, headers=h, json={"source": "mixups"})["empty"] == "nothing_due"
    with SessionLocal() as db:
        assert ("vocab", target) not in mixups.partners_by_item(db, db.get(models.User, uid))
    # ... and the companion remembers it was sorted out.
    memory = expect(client, "get", "/api/companion/memory", 200, headers=h)
    assert any(m["kind"] == "resolved_pair" for m in memory["memories"]), memory


def test_mixups_are_private_and_need_sign_in(client, learner):
    _, h = learner
    confuse_once(client, h)
    expect(client, "get", "/api/mistakes/mixups", 401)
    _, other = register(client, unique_name("mixer_other"))
    assert expect(client, "get", "/api/mistakes/mixups", 200, headers=other) == {"active": [], "resolved": []}
    assert expect(client, "post", ROUNDS, 200, headers=other, json={"source": "mixups"})["empty"] == "nothing_due"
