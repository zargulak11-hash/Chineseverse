"""Sequential lesson path (services/lesson_path.py): one current lesson,
locked lessons refused by every endpoint, completion only through a passed
practice round, existing progress resumed, and HSK 1 -> exam -> HSK 2
progression on the real seeded curriculum."""

from datetime import datetime, timedelta

import pytest

from app import models
from app.database import SessionLocal
from app.services import practice as practice_svc
from app.services.lesson_path import EXAMS_INTRODUCED_AT, path_state
from helpers import expect, register, unique_name


def flat(path):
    return [l for lvl in path["levels"] for l in lvl["lessons"]]


def steps(path):
    return [l for l in flat(path) if l["practicable"]]


def get_path(client, h):
    return expect(client, "get", "/api/lessons/path", 200, headers=h)


def play(client, h, lesson_id, correct=True):
    """Play one real lesson round: every answer right, or every answer wrong."""
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "lesson", "lesson_id": lesson_id})
    with SessionLocal() as db:
        qs = db.get(models.PracticeSession, s["id"]).questions
    for i, q in enumerate(qs):
        choice = q["item_id"] if correct else next(o for o in q["option_ids"] if o != q["item_id"])
        expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h, json={"index": i, "choice_id": choice})
    return expect(client, "post", f"/api/practice/sessions/{s['id']}/complete", 200, headers=h)


def complete(uid, lesson_ids, score=90, when=None):
    with SessionLocal() as db:
        for lid in lesson_ids:
            db.add(models.Progress(user_id=uid, lesson_id=lid, status="completed", score=score,
                                   completed_at=when or datetime.utcnow(), **({"created_at": when} if when else {})))
        db.commit()


@pytest.fixture
def learner(client):
    return register(client, unique_name("path"))


@pytest.fixture(scope="module")
def fresh_path(client):
    """The path as a brand-new learner sees it."""
    _, h = register(client, "pathviewer")
    return get_path(client, h)


@pytest.fixture(scope="module")
def stepl(fresh_path):
    return steps(fresh_path)


@pytest.fixture(scope="module")
def level_of(fresh_path):
    return {l["id"]: lv["level"] for lv in fresh_path["levels"] for l in lv["lessons"]}


def test_a_new_learner_has_exactly_one_current_lesson(client, fresh_path):
    expect(client, "get", "/api/lessons/path", 401)
    lessons, stepl = flat(fresh_path), steps(fresh_path)
    assert [l["status"] for l in lessons].count("current") == 1, fresh_path
    first = stepl[0]
    assert first["status"] == "current" and fresh_path["current_lesson_id"] == first["id"], first
    assert fresh_path["current_level"] == 1
    assert fresh_path["levels"][0]["level"] == 1 and fresh_path["levels"][0]["status"] == "current"
    assert all(l["status"] == "locked" for l in stepl[1:]), "every later step starts locked"
    cur_pos = lessons.index(first)
    assert all(l["status"] == "available" for l in lessons[:cur_pos]), "reading-only lessons before it are open"
    assert all(lv["status"] == "locked" for lv in fresh_path["levels"][1:]), "HSK 2+ start locked"
    assert [lv["level"] for lv in fresh_path["levels"]] == sorted(lv["level"] for lv in fresh_path["levels"])
    assert {7, 8, 9} <= {lv["level"] for lv in fresh_path["levels"]}, "the advanced band is walked as stages 7, 8, 9"


def test_every_path_step_builds_a_real_practice_round(client, learner):
    uid, _ = learner
    with SessionLocal() as db:
        u = db.get(models.User, uid)
        for e in path_state(db, u).entries:
            if e.practicable:
                assert practice_svc.build_session(db, u, "lesson", lesson_id=e.lesson.id) is not None, e.lesson.title


def test_intro_lessons_practice_their_own_real_words(fresh_path):
    # Their words are introduced as "米饭 mǐfàn", "我叫…… (...)" or a phrase
    # like "你好" that is practiced through its real words -- they used to have
    # no round at all, so a new learner's first HSK 1 lessons could not be practiced.
    lessons = flat(fresh_path)
    assert all(l["practicable"] for l in lessons), [l["title"] for l in lessons if not l["practicable"]]
    assert steps(fresh_path)[0]["title"] == "Greetings"
    with SessionLocal() as db:
        by_title = {l.title: l for l in db.query(models.Lesson)}

        def round_of(title):
            return [getattr(r, "simplified", None) or r.title for _t, r in practice_svc.lesson_round_items(db, by_title[title])]

        assert round_of("Greetings") == ["你", "好", "早上", "晚上"], round_of("Greetings")
        assert round_of("Food words") == ["米饭", "茶", "水", "牛肉面", "苹果"], round_of("Food words")
        assert round_of("Numbers 1–10")[:3] == ["一", "二", "三"], round_of("Numbers 1–10")
        assert "认识" in round_of("Introduce yourself") and "高兴" in round_of("Introduce yourself")
        assert round_of("Completed actions") == ["了 — completed action"], round_of("Completed actions")
        # Only real rows of the lesson's own level are used to split a phrase.
        greet = by_title["Greetings"]
        assert all(w.hsk_level_id == greet.hsk_level_id for w in practice_svc.lesson_items(db, greet)["vocab"])


def test_locked_lessons_are_refused_by_every_endpoint(client, learner, stepl):
    _, h = learner
    first, locked, last = stepl[0], stepl[1], stepl[-1]
    for url in (f"/api/lessons/{locked['id']}", f"/api/lessons/{locked['id']}/items"):
        body = expect(client, "get", url, 403, headers=h)
        assert body["code"] == "lesson_locked" and body["current_lesson_id"] == first["id"], body
        expect(client, "get", url, 401)  # no token -> no bypass either
    body = expect(client, "post", "/api/practice/sessions", 403, headers=h, json={"source": "lesson", "lesson_id": locked["id"]})
    assert body["code"] == "lesson_locked", body
    expect(client, "get", f"/api/lessons/{last['id']}", 403, headers=h)
    expect(client, "get", f"/api/lessons/{first['id']}", 200, headers=h)
    expect(client, "get", "/api/lessons/999999", 404, headers=h)


def test_the_public_catalogue_never_carries_lesson_bodies(client, learner):
    _, h = learner
    assert all(l["content"] is None for l in expect(client, "get", "/api/lessons", 200)), "anonymous list leaks content"
    assert all(l["content"] is None for l in expect(client, "get", "/api/lessons", 200, headers=h)), "learner list leaks content"


def test_the_client_cannot_complete_a_lesson_for_itself(client, learner, stepl):
    _, h = learner
    first, locked = stepl[0], stepl[1]
    expect(client, "post", "/api/progress", 403, headers=h, json={"lesson_id": first["id"], "status": "completed", "score": 100})
    expect(client, "post", "/api/progress", 403, headers=h, json={"lesson_id": locked["id"], "status": "completed", "score": 100})
    row = expect(client, "post", "/api/progress", 201, headers=h, json={"lesson_id": first["id"], "status": "in_progress"})
    expect(client, "patch", f"/api/progress/{row['id']}", 403, headers=h, json={"status": "completed", "score": 100})
    expect(client, "put", f"/api/progress/{row['id']}", 403, headers=h, json={"status": "completed", "score": 100})
    again = get_path(client, h)
    assert again["current_lesson_id"] == first["id"] and steps(again)[1]["status"] == "locked", again["current_lesson_id"]


def test_fail_then_pass_unlocks_exactly_the_next_step_and_review_unlocks_nothing(client, learner, stepl):
    _, h = learner
    _, other = register(client, unique_name("pathother"))
    first, locked = stepl[0], stepl[1]

    # A failed round keeps the lesson current and the next one locked.
    fail = play(client, h, first["id"], correct=False)
    assert not fail["passed"] and fail["lesson_status"] == "in_progress" and fail["next_lesson_id"] is None, fail
    after_fail = get_path(client, h)
    assert after_fail["current_lesson_id"] == first["id"] and steps(after_fail)[1]["status"] == "locked"
    expect(client, "get", f"/api/lessons/{locked['id']}", 403, headers=h)

    # Passing completes it and unlocks exactly the next step.
    win = play(client, h, first["id"])
    assert win["passed"] and win["lesson_status"] == "completed", win
    assert win["next_lesson_id"] == stepl[1]["id"], win
    p2 = get_path(client, h)
    s2 = steps(p2)
    assert s2[0]["status"] == "completed" and s2[1]["status"] == "current" and s2[2]["status"] == "locked", [x["status"] for x in s2[:3]]
    assert p2["current_lesson_id"] == stepl[1]["id"] and p2["completed"] == 1
    assert [l["status"] for l in flat(p2)].count("current") == 1
    expect(client, "get", f"/api/lessons/{stepl[1]['id']}", 200, headers=h)
    expect(client, "get", f"/api/lessons/{stepl[2]['id']}", 403, headers=h)

    # A completed lesson stays readable/practicable; re-practicing it never advances the path.
    done = expect(client, "get", f"/api/lessons/{first['id']}", 200, headers=h)
    assert done["path_status"] == "completed", done
    expect(client, "get", f"/api/lessons/{first['id']}/items", 200, headers=h)
    review_pass = play(client, h, first["id"])
    review_fail = play(client, h, first["id"], correct=False)
    assert review_pass["lesson_status"] == review_fail["lesson_status"] == "completed"
    assert review_pass["next_lesson_id"] is None and review_pass["reaction"]["event"] != "lesson_complete"
    p3 = get_path(client, h)
    assert p3["current_lesson_id"] == stepl[1]["id"] and steps(p3)[2]["status"] == "locked"

    # One learner's progress never moves another's path.
    po = get_path(client, other)
    assert po["current_lesson_id"] == first["id"] and po["completed"] == 0, po["current_lesson_id"]
    expect(client, "get", f"/api/lessons/{stepl[1]['id']}", 403, headers=other)


def test_a_round_left_open_on_a_locked_lesson_completes_nothing(client, learner, stepl):
    oid, other = learner
    with SessionLocal() as db:
        u = db.get(models.User, oid)
        stale = practice_svc.build_session(db, u, "lesson", lesson_id=stepl[3]["id"])  # bypasses the router gate
        stale_id, sq = stale.id, stale.questions
    for i, q in enumerate(sq):
        expect(client, "post", f"/api/practice/sessions/{stale_id}/answer", 200, headers=other, json={"index": i, "choice_id": q["item_id"]})
    res = expect(client, "post", f"/api/practice/sessions/{stale_id}/complete", 200, headers=other)
    assert res["passed"] and res["lesson_status"] is None and res["next_lesson_id"] is None, res
    po2 = get_path(client, other)
    assert po2["current_lesson_id"] == stepl[0]["id"] and steps(po2)[3]["status"] == "locked"


def test_existing_progress_resumes_and_earlier_gaps_stay_open(client, stepl):
    lid, lh = register(client, unique_name("pathlegacy"))
    gid, gh = register(client, unique_name("pathgappy"))
    complete(lid, [s["id"] for s in stepl[:10]])
    complete(gid, [stepl[5]["id"]], score=80)
    # completed 1-10 resumes at 11
    pl = get_path(client, lh)
    assert pl["current_lesson_id"] == stepl[10]["id"] and pl["completed"] == 10, pl["current_lesson_id"]
    assert all(s["status"] == "completed" for s in steps(pl)[:10]) and steps(pl)[11]["status"] == "locked"
    # only lesson 6 done: resume at 7, earlier lessons open, nothing reset
    pg = get_path(client, gh)
    sg = steps(pg)
    assert pg["current_lesson_id"] == stepl[6]["id"], pg["current_lesson_id"]
    assert [s["status"] for s in sg[:7]] == ["available"] * 5 + ["completed", "current"] and sg[7]["status"] == "locked"
    expect(client, "get", f"/api/lessons/{stepl[2]['id']}", 200, headers=gh)
    gap = play(client, gh, stepl[2]["id"])  # filling an old gap
    assert gap["lesson_status"] == "completed" and gap["next_lesson_id"] == stepl[6]["id"], gap
    assert get_path(client, gh)["current_lesson_id"] == stepl[6]["id"]


def test_finishing_hsk1_and_passing_its_exam_opens_hsk2(client, learner, level_of):
    _, h = learner
    hsk1 = [s for s in steps(get_path(client, h)) if level_of[s["id"]] == 1]
    for s in hsk1:
        assert get_path(client, h)["current_lesson_id"] == s["id"]
        assert play(client, h, s["id"])["lesson_status"] == "completed"
    ph = get_path(client, h)
    by_level = {lv["level"]: lv for lv in ph["levels"]}
    assert by_level[1]["completed"] == by_level[1]["total"] and by_level[1]["exam"] == "ready", by_level[1]["exam"]
    assert ph["exam_level"] == 1 and ph["current_lesson_id"] is None
    assert by_level[2]["status"] == "locked" and by_level[3]["status"] == "locked"
    exam = expect(client, "post", "/api/exams/1/start", 201, headers=h)
    with SessionLocal() as db:
        qs = db.get(models.HSKExamAttempt, exam["id"]).questions
    for i, q in enumerate(qs):
        expect(client, "post", f"/api/exams/attempts/{exam['id']}/answer", 200, headers=h, json={"index": i, "choice_id": q["item_id"]})
    assert expect(client, "post", f"/api/exams/attempts/{exam['id']}/submit", 200, headers=h)["status"] == "passed"
    ph = get_path(client, h)
    by_level = {lv["level"]: lv for lv in ph["levels"]}
    assert by_level[1]["status"] == "completed" and by_level[1]["exam"] == "passed", by_level[1]["status"]
    assert by_level[2]["status"] == "current" and ph["current_level"] == 2, by_level[2]["status"]
    assert by_level[3]["status"] == "locked"
    first_hsk2 = next(s for s in steps(ph) if level_of[s["id"]] == 2)
    assert ph["current_lesson_id"] == first_hsk2["id"]


def test_dashboard_and_roadmap_follow_the_path_not_the_dna_average(client, stepl, level_of):
    rid, rh = register(client, unique_name("pathrank"))
    complete(rid, [s["id"] for s in stepl if level_of[s["id"]] == 1])
    assert expect(client, "get", "/api/dashboard", 200, headers=rh)["hsk_level"] == 1  # exam still due
    with SessionLocal() as db:
        db.add(models.HSKExamAttempt(user_id=rid, level=1, status="passed", questions=[], answers=[], total=20,
                                     correct=20, score=100.0, violations=[], started_at=datetime.utcnow(),
                                     expires_at=datetime.utcnow(), finished_at=datetime.utcnow()))
        db.commit()
    assert expect(client, "get", "/api/dashboard", 200, headers=rh)["hsk_level"] == 2
    road = expect(client, "get", "/api/hsk/roadmap", 200, headers=rh)
    assert road["current_level"] == 2 and road["overall_mastery"] == 0.0, road["current_level"]
    assert [l["status"] for l in road["levels"][:3]] == ["unlocked", "current", "locked"], [l["status"] for l in road["levels"][:3]]
    _, fresh_h = register(client, unique_name("pathfresh"))
    assert expect(client, "get", "/api/dashboard", 200, headers=fresh_h)["hsk_level"] == 1
    assert expect(client, "get", "/api/hsk/roadmap", 200, headers=fresh_h)["current_level"] == 1


def test_admins_read_any_lesson_but_still_progress_in_order(client, learner, stepl):
    aid, ah = learner
    with SessionLocal() as db:
        db.get(models.User, aid).is_admin = True
        db.commit()
    last = stepl[-1]
    expect(client, "get", f"/api/lessons/{last['id']}", 200, headers=ah)
    assert any(l["content"] for l in expect(client, "get", "/api/lessons", 200, headers=ah))
    expect(client, "post", "/api/practice/sessions", 403, headers=ah, json={"source": "lesson", "lesson_id": last["id"]})


def pre_exam_learner(client, started_at):
    lid, lh = register(client, unique_name("preexam"))
    before = EXAMS_INTRODUCED_AT - timedelta(days=3)
    with SessionLocal() as db:
        entries = path_state(db, db.get(models.User, lid)).entries
        for e in entries:
            if e.level == 1 and e.practicable:
                db.add(models.Progress(user_id=lid, lesson_id=e.lesson.id, status="completed", score=90,
                                       created_at=before, completed_at=before))
        hsk2_first = next(e.lesson.id for e in entries if e.level == 2 and e.practicable)
        db.add(models.Progress(user_id=lid, lesson_id=hsk2_first, status="in_progress", score=40, created_at=started_at))
        db.commit()
    return lh, hsk2_first


def test_learners_who_started_hsk2_before_exams_existed_are_not_relocked(client):
    lh, first2 = pre_exam_learner(client, EXAMS_INTRODUCED_AT - timedelta(days=1))
    p = get_path(client, lh)
    assert p["exam_level"] is None and p["current_level"] == 2, (p["exam_level"], p["current_level"])
    assert p["current_lesson_id"] == first2
    expect(client, "get", f"/api/lessons/{first2}", 200, headers=lh)
    expect(client, "post", "/api/practice/sessions", 201, headers=lh, json={"source": "lesson", "lesson_id": first2})


def test_an_hsk2_row_made_after_exams_existed_does_not_skip_the_exam(client):
    lh, first2 = pre_exam_learner(client, datetime.utcnow())
    assert get_path(client, lh)["exam_level"] == 1
    expect(client, "get", f"/api/lessons/{first2}", 403, headers=lh)


def test_the_progress_api_refuses_rows_on_locked_lessons(client, learner):
    # ...so nobody can plant such a row.
    nid, nh = learner
    locked_id = next(l["id"] for l in flat(get_path(client, nh)) if l["status"] == "locked")
    for status in ("in_progress", "not_started"):
        expect(client, "post", "/api/progress", 403, headers=nh, json={"lesson_id": locked_id, "status": status})
    with SessionLocal() as db:
        assert db.query(models.Progress).filter_by(user_id=nid).count() == 0
