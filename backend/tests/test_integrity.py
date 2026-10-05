"""Learning state the browser must not be able to decide: the self-graded
vocabulary/grammar endpoints are gone, a Hanzi "got it" only counts when
the card is due, another learner's mistake is a 404 (not a 500), placement
can't re-run after onboarding, a Pet Teacher case counts toward missions
once, a solved case claims no fake XP, voice turns are graded against the
dialogue's own keywords, and response times are bounded by the server
clock. (AI is offline in tests: deterministic keyword grading.)"""

from datetime import datetime, timedelta

import pytest

from app import models
from app.database import SessionLocal
from app.services.gamification import ensure_user_skills
from helpers import expect, register, unique_name


def skill(uid, code):
    with SessionLocal() as db:
        row = (db.query(models.UserSkill).join(models.Skill)
               .filter(models.UserSkill.user_id == uid, models.Skill.code == code).first())
        return row.mastery if row else 0.0


@pytest.fixture
def learner(client):
    return register(client, unique_name("integrity"))


def first_hanzi(client, h):
    return expect(client, "get", "/api/hanzi?hsk_level=1", 200, headers=h)[0]


def test_self_graded_vocab_and_grammar_endpoints_are_gone(client, learner):
    uid, h = learner
    with SessionLocal() as db:
        word_id = db.query(models.VocabularyWord).order_by(models.VocabularyWord.id).first().id
        topic_id = db.query(models.GrammarTopic).order_by(models.GrammarTopic.id).first().id
    for url in (f"/api/vocab/{word_id}/review", f"/api/grammar/{topic_id}/practice"):
        for _ in range(9):
            r = client.post(url, headers=h, json={"correct": True})
            assert r.status_code in (404, 405), (url, r.status_code)
    with SessionLocal() as db:
        assert db.query(models.UserVocabulary).filter_by(user_id=uid).count() == 0
        assert db.query(models.UserGrammar).filter_by(user_id=uid).count() == 0
    # ... and the lists still load
    expect(client, "get", "/api/vocab?hsk_level=1", 200, headers=h)
    expect(client, "get", "/api/grammar?hsk_level=1", 200, headers=h)


def test_hanzi_got_it_only_counts_when_the_card_is_due(client, learner):
    uid, h = learner
    hz = first_hanzi(client, h)
    first = expect(client, "post", f"/api/hanzi/{hz['id']}/review", 200, headers=h, json={"correct": True})
    assert first["counted"] and first["mastery"] == 10.0 and first["next_review_at"], first
    reading = skill(uid, "reading")
    for _ in range(9):
        again = expect(client, "post", f"/api/hanzi/{hz['id']}/review", 200, headers=h, json={"correct": True})
        assert not again["counted"] and again["mastery"] == 10.0 and again["status"] == "learning", again
    assert skill(uid, "reading") == reading, "an early 'got it' moved Learning DNA"
    with SessionLocal() as db:
        rec = db.query(models.UserHanzi).filter_by(user_id=uid, hanzi_id=hz["id"]).one()
        assert rec.times_seen == 1, rec.times_seen
        rec.next_review_at = datetime.utcnow() - timedelta(minutes=1)  # a day passes
        db.commit()
    due = expect(client, "post", f"/api/hanzi/{hz['id']}/review", 200, headers=h, json={"correct": True})
    assert due["counted"] and due["mastery"] == 20.0, due
    miss = expect(client, "post", f"/api/hanzi/{hz['id']}/review", 200, headers=h, json={"correct": False})
    assert miss["counted"] and miss["mastery"] == 15.0, miss  # admitting a miss always counts


def test_another_learners_mistake_is_a_404_not_a_500(client, learner):
    uid, h = learner
    _, oh = register(client, unique_name("integrity_other"))
    hz = first_hanzi(client, h)
    expect(client, "post", f"/api/hanzi/{hz['id']}/review", 200, headers=h, json={"correct": False})
    with SessionLocal() as db:
        m = db.query(models.LearningMistake).filter_by(user_id=uid).first()
        assert m is not None, "the wrong Hanzi answer is in the mistake bank"
        mid = m.id
    expect(client, "patch", f"/api/mistakes/{mid}", 404, headers=oh, json={"request_retest": True})
    expect(client, "patch", "/api/mistakes/999999", 404, headers=oh, json={"request_retest": True})
    expect(client, "patch", f"/api/mistakes/{mid}", 200, headers=h, json={"request_retest": True})


def test_placement_cannot_rerun_after_onboarding(client, learner):
    fid, fh = learner
    start = expect(client, "post", "/api/onboarding/placement-test/start", 200, headers=fh)
    with SessionLocal() as db:
        qd = db.get(models.PlacementAttempt, start["attempt_id"]).question_data
    answers = [{"index": q["index"], "answer": q["answer"]} for q in qd if q["level"] == 1]
    expect(client, "post", f"/api/onboarding/placement-test/{start['attempt_id']}/submit", 200, headers=fh,
           json={"answers": answers})
    with SessionLocal() as db:
        dna_after = {s.skill_id: s.mastery for s in db.get(models.User, fid).user_skills}
    expect(client, "post", "/api/onboarding/placement-test/start", 409, headers=fh)
    with SessionLocal() as db:
        assert {s.skill_id: s.mastery for s in db.get(models.User, fid).user_skills} == dna_after


def first_pet_case(db):
    return (db.query(models.PetTeacherCase).join(models.HSKLevel)
            .order_by(models.HSKLevel.level, models.PetTeacherCase.id).first())


def test_a_solved_pet_teacher_case_counts_once(client, learner):
    uid, h = learner
    with SessionLocal() as db:
        case = first_pet_case(db)
        case_id, fix, kws = case.id, case.correct_sentence, case.explanation_keywords or []
        teach = db.query(models.Mission).filter_by(kind="teach").first()
        teach_id = teach.id if teach else None
    body = {"correction": fix, "explanation": " ".join(kws) or "because"}
    r1 = expect(client, "post", f"/api/pet-teacher/lesson/{case_id}/answer", 200, headers=h, json=body)
    if not r1.get("success"):
        pytest.skip("the offline grader did not accept the seeded explanation")

    def teach_progress():
        with SessionLocal() as db:
            um = db.query(models.UserMission).filter_by(user_id=uid, mission_id=teach_id).first()
            return um.progress if um else 0

    def bond():
        with SessionLocal() as db:
            return db.get(models.User, uid).user_animal.bond_points

    p1 = teach_progress() if teach_id else None
    expect(client, "post", "/api/me/animal", 200, headers=h, json={"animal_id": 1})
    b1 = bond()
    for _ in range(3):
        expect(client, "post", f"/api/pet-teacher/lesson/{case_id}/answer", 200, headers=h, json=body)
    if teach_id:
        assert teach_progress() == p1, (teach_progress(), p1)
    assert bond() == b1, (bond(), b1)
    with SessionLocal() as db:
        assert db.query(models.UserTaughtFact).filter_by(user_id=uid, case_id=case_id).count() == 1


def test_a_pet_teacher_case_above_the_learners_level_is_refused(client, learner):
    _, h = learner
    with SessionLocal() as db:
        case = first_pet_case(db)
        high = (db.query(models.PetTeacherCase).join(models.HSKLevel)
                .filter(models.HSKLevel.level > 1).order_by(models.HSKLevel.level.desc()).first())
        assert high is not None, "the seed has Pet Teacher cases above HSK 1"
        body = {"correction": case.correct_sentence, "explanation": "because"}
        high_id = high.id
    expect(client, "post", f"/api/pet-teacher/lesson/{high_id}/answer", 403, headers=h, json=body)


def test_solving_a_case_claims_no_xp_it_never_grants(client, learner):
    _, h = learner
    with SessionLocal() as db:
        sc = db.query(models.Scenario).filter(models.Scenario.is_case.is_(True)).first()
        assert sc is not None, "the seed has detective cases"
        slug = sc.slug
    r = client.post(f"/api/world/scenarios/{slug}/solve", headers=h, json={"conclusion": "不知道"})
    # Either solvable (then no fake XP in the answer) or locked for a new learner.
    assert r.status_code in (200, 403), r.status_code
    if r.status_code == 200:
        assert "xp_reward" not in r.json(), r.json()


def test_reading_pages_never_picks_a_main_companion(client, learner):
    nid, nh = learner
    expect(client, "get", "/api/dashboard", 200, headers=nh)
    expect(client, "get", "/api/real-life/world", 200, headers=nh)
    dash = expect(client, "get", "/api/dashboard", 200, headers=nh)
    assert dash["animal"] is None, dash["animal"]
    with SessionLocal() as db:
        u = db.get(models.User, nid)
        assert u.animal_id is None and u.user_animal is None


def test_concurrent_first_loads_do_not_500_on_skill_rows(client, learner):
    # Two first requests for a new account (dashboard + the page's own) both
    # create the learner's skill rows; the one that loses must not 500.
    rid, rh = learner
    with SessionLocal() as a, SessionLocal() as b:
        ua = a.get(models.User, rid)
        assert not ua.user_skills  # request A saw no rows...
        ensure_user_skills(b, b.get(models.User, rid))  # ...request B created them first
        ensure_user_skills(a, ua)  # A's insert collides and recovers
        assert len(ua.user_skills) == len(b.get(models.User, rid).user_skills) > 0
    expect(client, "get", "/api/missions", 200, headers=rh)


def test_voice_turns_are_graded_against_the_dialogue_and_locked_lines_stay_locked(client, learner):
    _, vh = learner
    with SessionLocal() as db:
        sc = db.query(models.Scenario).filter_by(slug="asking-directions").one()
        line = (db.query(models.Dialogue).filter_by(scenario_id=sc.id, speaker="learner")
                .order_by(models.Dialogue.turn_index).first())
        locked_sc = db.query(models.Scenario).filter_by(slug="buying-fruit").one()
        locked_line = db.query(models.Dialogue).filter_by(scenario_id=locked_sc.id, speaker="learner").first()
        sc_id, line_id, locked_line_id = sc.id, line.id, locked_line.id
    forged = expect(client, "post", "/api/voice/attempt", 200, headers=vh, json={
        "spoken_text": "好", "expected_keywords": ["好"], "prompt_text": "好", "scenario_id": sc_id, "dialogue_id": line_id})
    assert forged["attempt"]["relevance"] < 55, forged["attempt"]  # graded against the line's own keywords
    free = expect(client, "post", "/api/voice/attempt", 200, headers=vh, json={
        "spoken_text": "好", "expected_keywords": ["好"]})
    assert free["attempt"]["relevance"] == 0, free["attempt"]  # no client-chosen answer key
    # a locked location's line can't be answered by leaving scenario_id out or naming another one
    expect(client, "post", "/api/voice/attempt", 403, headers=vh, json={"spoken_text": "我要苹果", "dialogue_id": locked_line_id})
    expect(client, "post", "/api/voice/attempt", 422, headers=vh,
           json={"spoken_text": "我要苹果", "scenario_id": sc_id, "dialogue_id": locked_line_id})
    expect(client, "post", "/api/voice/attempt", 404, headers=vh, json={"spoken_text": "好", "dialogue_id": 999999})


def test_response_time_is_bounded_by_the_server_clock(client, learner):
    pid, ph = learner

    def correct_answer(sess, idx, ms):
        with SessionLocal() as db:
            stored = db.get(models.PracticeSession, sess["id"]).questions
        return expect(client, "post", f"/api/practice/sessions/{sess['id']}/answer", 200, headers=ph,
                      json={"index": idx, "choice_id": stored[idx]["item_id"], "response_ms": ms})

    expect(client, "get", "/api/dashboard", 200, headers=ph)  # skill rows
    s = expect(client, "post", "/api/practice/sessions", 201, headers=ph, json={"source": "vocab", "hsk_level": 1, "size": 4})
    with SessionLocal() as db:  # a minute passes before the "1 ms" answer arrives
        row = db.get(models.PracticeSession, s["id"])
        row.created_at = datetime.utcnow() - timedelta(seconds=60)
        db.commit()
    speed = skill(pid, "reaction_speed")
    correct_answer(s, 0, 1)
    assert skill(pid, "reaction_speed") == speed, "a claimed 1 ms answer a minute in earned Reaction Speed"
    with SessionLocal() as db:
        assert db.get(models.PracticeSession, s["id"]).answers[0]["response_ms"] >= 50_000
    correct_answer(s, 1, 1500)  # answered right after the previous one: genuinely fast
    assert skill(pid, "reaction_speed") == speed + 0.5, (skill(pid, "reaction_speed"), speed)
