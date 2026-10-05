"""Onboarding placement (routers/onboarding.py): the questions reach the
browser without their answers, the server alone grades them and places the
learner by the levels really passed, an attempt is one learner's and is
graded once, and skipping finishes onboarding too."""

import pytest

from app import models
from app.database import SessionLocal
from helpers import expect, register, unique_name


@pytest.fixture
def learner(client):
    return register(client, unique_name("newbie"))


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
