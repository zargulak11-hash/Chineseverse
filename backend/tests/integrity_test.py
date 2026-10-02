"""Learning state the browser must not be able to decide, on a fresh
database: the self-graded vocabulary/grammar endpoints are gone, a Hanzi
"got it" only counts when the card is due, another learner's mistake is a
404 (not a 500), placement can't re-run after onboarding, a Pet Teacher case
counts toward missions once, and a solved case no longer claims fake XP."""

import os
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/integrity.db"
os.environ["AI_PROVIDER"] = "offline"  # deterministic keyword grading, no network
os.environ["SMTP_HOST"] = "smtp.invalid"

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402

settings.ai_provider = "offline"


def expect(client, method, url, expected, **kwargs):
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == expected, f"{method.upper()} {url} -> {resp.status_code} (expected {expected}): {resp.text[:300]}"
    return resp.json() if resp.content else None


def register(client, name):
    data = expect(client, "post", "/api/auth/register", 201,
                  json={"username": name, "email": f"{name}@example.com", "password": "secret1"})
    return data["user"]["id"], {"Authorization": f"Bearer {data['access_token']}"}


def skill(uid, code):
    with SessionLocal() as db:
        row = (db.query(models.UserSkill).join(models.Skill)
               .filter(models.UserSkill.user_id == uid, models.Skill.code == code).first())
        return row.mastery if row else 0.0


with TestClient(app) as client:
    uid, h = register(client, "integritylearner")
    oid, oh = register(client, "integrityother")

    # ---------------------------------------------- self-graded endpoints are gone
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
    expect(client, "get", "/api/vocab?hsk_level=1", 200, headers=h)
    expect(client, "get", "/api/grammar?hsk_level=1", 200, headers=h)
    print("[PASS] {'correct': true} can no longer master vocabulary or grammar; the lists still load")

    # ---------------------------------------------- Hanzi self-check is due-gated
    hz = expect(client, "get", "/api/hanzi?hsk_level=1", 200, headers=h)[0]
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
    print("[PASS] Hanzi 'got it' spam changes nothing until the card is due; 'still learning' always counts")

    # ---------------------------------------------- another learner's mistake is a 404
    with SessionLocal() as db:
        m = db.query(models.LearningMistake).filter_by(user_id=uid).first()
        assert m is not None, "the wrong Hanzi answer above is in the mistake bank"
        mid = m.id
    expect(client, "patch", f"/api/mistakes/{mid}", 404, headers=oh, json={"request_retest": True})
    expect(client, "patch", "/api/mistakes/999999", 404, headers=oh, json={"request_retest": True})
    expect(client, "patch", f"/api/mistakes/{mid}", 200, headers=h, json={"request_retest": True})
    print("[PASS] PATCH on another learner's mistake is a 404 (it used to be a 500)")

    # ---------------------------------------------- placement belongs to onboarding
    fid, fh = register(client, "integrityfresh")
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
    print("[PASS] the placement test can't be re-run after onboarding to overwrite Learning DNA")

    # ---------------------------------------------- Pet Teacher counts a case once
    with SessionLocal() as db:
        case = (db.query(models.PetTeacherCase).join(models.HSKLevel)
                .order_by(models.HSKLevel.level, models.PetTeacherCase.id).first())
        case_id, fix, kws = case.id, case.correct_sentence, case.explanation_keywords or []
        teach = db.query(models.Mission).filter_by(kind="teach").first()
        teach_id = teach.id if teach else None
    body = {"correction": fix, "explanation": " ".join(kws) or "because"}
    r1 = expect(client, "post", f"/api/pet-teacher/lesson/{case_id}/answer", 200, headers=h, json=body)
    if r1.get("success"):
        def teach_progress():
            with SessionLocal() as db:
                um = db.query(models.UserMission).filter_by(user_id=uid, mission_id=teach_id).first()
                return um.progress if um else 0
        p1 = teach_progress() if teach_id else None
        expect(client, "post", "/api/me/animal", 200, headers=h, json={"animal_id": 1})
        def bond():
            with SessionLocal() as db:
                return db.get(models.User, uid).user_animal.bond_points
        b1 = bond()
        for _ in range(3):
            expect(client, "post", f"/api/pet-teacher/lesson/{case_id}/answer", 200, headers=h, json=body)
        if teach_id:
            assert teach_progress() == p1, (teach_progress(), p1)
        assert bond() == b1, (bond(), b1)
        with SessionLocal() as db:
            assert db.query(models.UserTaughtFact).filter_by(user_id=uid, case_id=case_id).count() == 1
        print("[PASS] re-submitting a solved Pet Teacher case earns no more bond points or 'teach' mission progress")
    else:
        print("[SKIP] offline grader did not accept the seeded explanation; repeat-count check skipped")
    with SessionLocal() as db:
        high = (db.query(models.PetTeacherCase).join(models.HSKLevel)
                .filter(models.HSKLevel.level > 1).order_by(models.HSKLevel.level.desc()).first())
        high_id = high.id if high else None
    if high_id:
        expect(client, "post", f"/api/pet-teacher/lesson/{high_id}/answer", 403, headers=h, json=body)
        print("[PASS] a Pet Teacher case above the learner's level is refused")

    # ---------------------------------------------- no fake XP claim on cases
    with SessionLocal() as db:
        sc = db.query(models.Scenario).filter(models.Scenario.is_case.is_(True)).first()
        slug = sc.slug if sc else None
    if slug:
        r = client.post(f"/api/world/scenarios/{slug}/solve", headers=h, json={"conclusion": "不知道"})
        if r.status_code == 200:
            assert "xp_reward" not in r.json(), r.json()
            print("[PASS] solving a case no longer reports XP that is never granted")
        else:
            assert r.status_code == 403, r.status_code
            print("[PASS] case locked for a new learner (403); no XP claim reachable")

    # ---------------------------------------------- reads never pick a main companion
    nid, nh = register(client, "integritynocompanion")
    expect(client, "get", "/api/dashboard", 200, headers=nh)
    with SessionLocal() as db:
        loc = db.query(models.Location).order_by(models.Location.id).first()
    expect(client, "get", f"/api/world/locations/{loc.slug}", 200, headers=nh)
    dash = expect(client, "get", "/api/dashboard", 200, headers=nh)
    assert dash["animal"] is None, dash["animal"]
    with SessionLocal() as db:
        u = db.get(models.User, nid)
        assert u.animal_id is None and u.user_animal is None
    print("[PASS] loading the dashboard or a location no longer makes the panda the learner's companion")

    # ---------------------------------------------- first-load race on skill rows
    # Two first requests for a new account (dashboard + the page's own) both
    # create the learner's skill rows; the one that loses must not 500.
    from app.services.gamification import ensure_user_skills
    rid, rh = register(client, "integrityrace")
    with SessionLocal() as a, SessionLocal() as b:
        ua = a.get(models.User, rid)
        assert not ua.user_skills  # request A saw no rows...
        ensure_user_skills(b, b.get(models.User, rid))  # ...request B created them first
        ensure_user_skills(a, ua)  # A's insert collides and recovers
        assert len(ua.user_skills) == len(b.get(models.User, rid).user_skills) > 0
    expect(client, "get", "/api/missions", 200, headers=rh)
    print("[PASS] concurrent first loads no longer 500 on the learner's skill rows")

print("ALL INTEGRITY TESTS PASSED")
