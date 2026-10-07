"""Onboarding placement (routers/onboarding.py): the questions reach the
browser without their answers, the server alone grades them and places the
learner by the levels really passed, an attempt is one learner's and is
graded once, and skipping finishes onboarding too."""

import pytest

from app import models
from app.database import SessionLocal
from helpers import expect, register, unique_name


def save_earlier_steps(client, h, companion=True, questions=True):
    """The onboarding steps before placement: the companion, then the two
    questions -- exactly the calls the Onboarding page makes."""
    if companion:
        animal = expect(client, "get", "/api/animals", 200)[0]
        expect(client, "post", "/api/me/animal", 200, headers=h, json={"animal_id": animal["id"]})
    if questions:
        expect(client, "patch", "/api/me/profile", 200, headers=h,
               json={"learning_motivation": "travel", "discovery_source": "friend"})


@pytest.fixture
def learner(client):
    uid, h = register(client, unique_name("newbie"))
    save_earlier_steps(client, h)
    return uid, h


def start(client, h):
    return expect(client, "post", "/api/onboarding/placement-test/start", 200, headers=h)


def key_of(attempt_id):
    with SessionLocal() as db:
        return db.get(models.PlacementAttempt, attempt_id).question_data


def answers(attempt_id, correct_levels):
    """Right answers for the given levels, deliberately wrong ones elsewhere."""
    return [{"index": q["index"], "answer": q["answer"] if q["level"] in correct_levels else "definitely wrong"}
            for q in key_of(attempt_id)]


def submit(client, h, attempt_id, body, expected=200):
    return expect(client, "post", f"/api/onboarding/placement-test/{attempt_id}/submit", expected,
                  headers=h, json={"answers": body})


def test_placement_questions_arrive_without_their_answers(client, learner):
    _, h = learner
    s = start(client, h)
    assert s["questions"] and {q["level"] for q in s["questions"]} >= {1, 2}
    assert all("answer" not in q and "_correct" not in q for q in s["questions"])
    assert [q["index"] for q in s["questions"]] == list(range(len(s["questions"])))


@pytest.mark.parametrize("correct_levels", [set(), {1}, {1, 2}])
def test_the_learner_is_placed_by_the_levels_they_really_passed(client, learner, correct_levels):
    uid, h = learner
    s = start(client, h)
    r = submit(client, h, s["attempt_id"], answers(s["attempt_id"], correct_levels))
    expected_right = sum(1 for q in key_of(s["attempt_id"]) if q["level"] in correct_levels)
    assert r["correct_count"] == expected_right and r["total_count"] == len(s["questions"])
    assert r["placed_level"] == len(correct_levels) + 1, r
    with SessionLocal() as db:
        u = db.get(models.User, uid)
        assert u.profile.onboarding_completed is True
        assert len({round(s.mastery, 3) for s in u.user_skills}) == 1  # every skill set alike


def test_answers_are_compared_without_case_or_surrounding_spaces(client, learner):
    _, h = learner
    s = start(client, h)
    body = [{"index": q["index"], "answer": f"  {str(q['answer']).upper()}  "} for q in key_of(s["attempt_id"])]
    r = submit(client, h, s["attempt_id"], body)
    assert r["correct_count"] == r["total_count"]


def test_an_attempt_belongs_to_one_learner_and_is_graded_once(client, learner):
    _, h = learner
    _, other = register(client, unique_name("placement_other"))
    s = start(client, h)
    submit(client, other, s["attempt_id"], [], expected=404)
    submit(client, h, 999999, [], expected=404)
    submit(client, h, s["attempt_id"], answers(s["attempt_id"], {1}))
    body = submit(client, h, s["attempt_id"], answers(s["attempt_id"], {1, 2, 3}), expected=409)
    assert body["detail"] == "Placement attempt already finished"
    # ... and onboarding is over, so a new test can't be started to redo it.
    expect(client, "post", "/api/onboarding/placement-test/start", 409, headers=h)


def test_skipping_finishes_onboarding_at_the_current_level(client, learner):
    uid, h = learner
    r = expect(client, "post", "/api/onboarding/placement-test/skip", 200, headers=h)
    assert (r["correct_count"], r["total_count"], r["placed_level"]) == (0, 0, 1)
    with SessionLocal() as db:
        assert db.get(models.User, uid).profile.onboarding_completed is True
        assert db.get(models.PlacementAttempt, r["attempt_id"]).status == "skipped"
    expect(client, "post", "/api/onboarding/placement-test/start", 409, headers=h)


def test_placement_requires_sign_in(client):
    expect(client, "post", "/api/onboarding/placement-test/start", 401)
    expect(client, "post", "/api/onboarding/placement-test/skip", 401)
    expect(client, "post", "/api/onboarding/placement-test/1/submit", 401, json={"answers": []})


def onboarded(client, h):
    me = expect(client, "get", "/api/me", 200, headers=h)
    assert me["user"]["onboarding_completed"] == me["profile"]["onboarding_completed"]
    return me["user"]["onboarding_completed"]


@pytest.mark.parametrize("companion,questions,detail", [
    (False, True, "Choose your companion before finishing onboarding"),
    (True, False, "Answer the onboarding questions before finishing onboarding"),
    (False, False, "Choose your companion before finishing onboarding"),
])
def test_onboarding_cannot_finish_before_the_earlier_steps_are_saved(client, companion, questions, detail):
    uid, h = register(client, unique_name("half_done"))
    save_earlier_steps(client, h, companion=companion, questions=questions)
    body = expect(client, "post", "/api/onboarding/placement-test/skip", 409, headers=h)
    assert body["detail"] == detail
    s = start(client, h)  # the test itself may be taken; only finishing waits
    assert submit(client, h, s["attempt_id"], answers(s["attempt_id"], {1}), expected=409)["detail"] == detail
    assert onboarded(client, h) is False
    with SessionLocal() as db:
        assert db.get(models.PlacementAttempt, s["attempt_id"]).status == "active"  # can still be finished
    # ... and once the missing step is saved, the very same attempt finishes it.
    save_earlier_steps(client, h, companion=not companion, questions=not questions)
    submit(client, h, s["attempt_id"], answers(s["attempt_id"], {1}))
    assert onboarded(client, h) is True


def test_completion_is_reported_by_every_sign_in_and_survives_a_new_session(client):
    name = unique_name("returning")
    reg = expect(client, "post", "/api/auth/register", 201,
                 json={"username": name, "email": f"{name}@example.com", "password": "secret1"})
    assert reg["user"]["onboarding_completed"] is False  # a new account starts in onboarding
    h = {"Authorization": f"Bearer {reg['access_token']}"}
    save_earlier_steps(client, h)
    assert onboarded(client, h) is False  # companion + answers alone don't finish it
    expect(client, "post", "/api/onboarding/placement-test/skip", 200, headers=h)
    assert onboarded(client, h) is True
    # Log out and back in: a brand-new token, same answer -- and the saved
    # companion and answers are still there.
    again = expect(client, "post", "/api/auth/login", 200, json={"username": name, "password": "secret1"})
    assert again["user"]["onboarding_completed"] is True and again["user"]["animal_id"] is not None
    me = expect(client, "get", "/api/me", 200, headers={"Authorization": f"Bearer {again['access_token']}"})
    assert (me["profile"]["learning_motivation"], me["profile"]["discovery_source"]) == ("travel", "friend")


def test_finished_onboarding_cannot_be_finished_again(client, learner):
    _, h = learner
    expect(client, "post", "/api/onboarding/placement-test/skip", 200, headers=h)
    with SessionLocal() as db:
        n = db.query(models.PlacementAttempt).count()
    body = expect(client, "post", "/api/onboarding/placement-test/skip", 409, headers=h)
    assert body["detail"] == "The placement test is part of onboarding, which is already complete"
    with SessionLocal() as db:
        assert db.query(models.PlacementAttempt).count() == n


def test_changing_the_companion_later_keeps_onboarding_complete(client, learner):
    _, h = learner
    expect(client, "post", "/api/onboarding/placement-test/skip", 200, headers=h)
    other = expect(client, "get", "/api/animals", 200)[-1]
    expect(client, "post", "/api/me/animal", 200, headers=h, json={"animal_id": other["id"]})
    expect(client, "patch", "/api/me/profile", 200, headers=h, json={"bio": "hi"})
    me = expect(client, "get", "/api/me", 200, headers=h)
    assert me["user"]["onboarding_completed"] is True and me["user"]["animal_id"] == other["id"]
