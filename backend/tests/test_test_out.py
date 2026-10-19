"""Testing out of an HSK level (services/hsk_exam.test_out_levels): a
learner who already knows HSK 1-3 is not forced through every HSK 1 and 2
lesson. The same proctored exam, graded by the server, is the evidence;
passing moves the lesson path past that level (lessons stay open, none is
marked completed); failing changes nothing; and the journey suggests it only
when the learner's real level is above their lessons."""

from datetime import datetime, timedelta

from app import models
from app.database import SessionLocal
from helpers import expect, register, unique_name
from test_hsk_exam import answer_all, complete_levels, first_lesson_of, path


def take(client, h, level, right=True):
    a = expect(client, "post", f"/api/exams/{level}/start", 201, headers=h)
    answer_all(client, h, a, right=right)
    return expect(client, "post", f"/api/exams/attempts/{a['id']}/submit", 200, headers=h)


def place_at(uid, level):
    """Skill mastery as the placement test sets it for this level
    (routers/onboarding._score_and_place: 15 per level passed)."""
    with SessionLocal() as db:
        u = db.get(models.User, uid)
        from app.services.gamification import ensure_user_skills

        ensure_user_skills(db, u)
        for s in u.user_skills:
            s.mastery = level * 15 - 1 + 0.5
        db.commit()


def test_passing_a_test_out_moves_the_path_past_it(client):
    uid, h = register(client, unique_name("testout"))
    r = take(client, h, 3)
    assert r["passed"] and r["status"] == "passed"
    p = path(client, h)
    assert p["current_level"] == 4 and p["exam_level"] is None
    lv = {x["level"]: x for x in p["levels"]}
    # The skipped levels stay open (available, not completed) and nothing is marked done.
    hsk1 = first_lesson_of(p, 1)
    assert hsk1["status"] == "available" and lv[1]["completed"] == 0 and lv[3]["completed"] == 0
    expect(client, "get", f"/api/lessons/{hsk1['id']}", 200, headers=h)
    assert lv[1]["exam"] == "cleared" and lv[3]["exam"] == "passed"
    assert first_lesson_of(p, 4)["status"] == "current"
    assert first_lesson_of(p, 5)["status"] == "locked"
    with SessionLocal() as db:
        assert db.query(models.Progress).filter_by(user_id=uid).count() == 0
    # Now HSK 4-6 can be tested out of; HSK 3 is passed.
    assert expect(client, "get", "/api/exams", 200, headers=h)["test_out_levels"] == [4, 5, 6]


def test_failing_a_test_out_changes_nothing(client):
    uid, h = register(client, unique_name("testoutfail"))
    before = path(client, h)
    r = take(client, h, 2, right=False)
    assert not r["passed"]
    after = path(client, h)
    assert after["current_lesson_id"] == before["current_lesson_id"] and after["current_level"] == 1
    assert first_lesson_of(after, 2)["status"] == "locked"


def test_a_level_more_than_two_ahead_cannot_be_tested_out(client):
    _, h = register(client, unique_name("testoutfar"))
    expect(client, "post", "/api/exams/4/start", 403, headers=h)
    take(client, h, 1)
    assert path(client, h)["current_level"] == 2
    expect(client, "post", "/api/exams/5/start", 403, headers=h)
    expect(client, "post", "/api/exams/4/start", 201, headers=h)


def test_finished_levels_still_go_through_their_exam(client):
    # Tested out of HSK 1-2, then every HSK 3 lesson done: HSK 3's exam is the
    # gate again (a test-out never lets a level's own exam be skipped later).
    uid, h = register(client, unique_name("testoutgate"))
    take(client, h, 2)
    complete_levels(uid, {3})
    p = path(client, h)
    assert p["exam_level"] == 3 and p["test_out_levels"] == []
    assert first_lesson_of(p, 4)["status"] == "locked"


def test_existing_progress_keeps_its_place(client):
    # A learner far along (HSK 1-2 lessons done, HSK 1 exam passed the usual
    # way) resumes exactly where they were.
    uid, h = register(client, unique_name("testoutold"))
    complete_levels(uid, {1})
    take(client, h, 1)
    complete_levels(uid, {2})
    p = path(client, h)
    assert p["exam_level"] == 2 and p["test_out_levels"] == []


def test_the_journey_suggests_a_test_out_only_to_a_learner_above_their_lessons(client):
    uid, h = register(client, unique_name("testoutnext"))
    j = expect(client, "get", "/api/journey", 200, headers=h)
    assert j["next"]["kind"] == "foundation", "a beginner is never pushed to an exam"
    place_at(uid, 3)
    j = expect(client, "get", "/api/journey", 200, headers=h)
    assert j["level"] == 3
    assert j["next"] == {"kind": "testout", "key": "testout", "to": "/exam/3", "level": 3, "from": 1}
    # After a failed attempt the lessons are the way on (for a week).
    take(client, h, 3, right=False)
    j = expect(client, "get", "/api/journey", 200, headers=h)
    assert j["next"]["kind"] != "testout"
    with SessionLocal() as db:
        for a in db.query(models.HSKExamAttempt).filter_by(user_id=uid):
            a.started_at = datetime.utcnow() - timedelta(days=8)
        db.commit()
    assert expect(client, "get", "/api/journey", 200, headers=h)["next"]["kind"] == "testout"
    # Passed: the path is at HSK 4 and the learner's level is 3 -- nothing to test out.
    take(client, h, 3)
    j = expect(client, "get", "/api/journey", 200, headers=h)
    assert j["next"]["kind"] != "testout" and j["next"].get("level") != 3
