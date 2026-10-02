"""Every mission in the content, end to end, on a fresh database: each one
is reachable for a learner at its HSK level and completes only through the
real activity it names (graded by the server), once, paying its reward
once. Offline AI grading keeps the run deterministic."""

import os
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/missions_e2e.db"
os.environ["AI_PROVIDER"] = "offline"
os.environ["SMTP_HOST"] = "smtp.invalid"

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services.lesson_path import path_state  # noqa: E402

settings.ai_provider = "offline"


def expect(client, method, url, expected, **kwargs):
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == expected, f"{method.upper()} {url} -> {resp.status_code} (expected {expected}): {resp.text[:300]}"
    return resp.json() if resp.content else None


def register(client, name):
    data = expect(client, "post", "/api/auth/register", 201,
                  json={"username": name, "email": f"{name}@example.com", "password": "secret1"})
    return data["user"]["id"], {"Authorization": f"Bearer {data['access_token']}"}


def missions(client, h):
    return {m["mission"]["slug"]: m for m in expect(client, "get", "/api/missions", 200, headers=h)}


def reach_hsk2(uid):
    """What finishing HSK 1 really writes: its lessons completed and its
    final exam passed (rows the server's own grading would create)."""
    now = datetime.utcnow()
    with SessionLocal() as db:
        for e in path_state(db, db.get(models.User, uid)).entries:
            if e.level == 1 and e.practicable:
                db.add(models.Progress(user_id=uid, lesson_id=e.lesson.id, status="completed", score=90, completed_at=now))
        db.add(models.HSKExamAttempt(user_id=uid, level=1, status="passed", questions=[], answers=[], total=20,
                                     correct=20, score=100.0, violations=[], started_at=now,
                                     expires_at=now + timedelta(minutes=20), finished_at=now))
        db.commit()


def learner_lines(slug):
    with SessionLocal() as db:
        sc = db.query(models.Scenario).filter_by(slug=slug).one()
        lines = (db.query(models.Dialogue).filter_by(scenario_id=sc.id, speaker="learner")
                 .order_by(models.Dialogue.turn_index).all())
        return sc.id, [(d.id, "".join(d.expected_keywords or []) or d.prompt) for d in lines]


def xp(uid):
    with SessionLocal() as db:
        return db.get(models.User, uid).total_xp


with TestClient(app) as client:
    uid, h = register(client, "missione2e")
    rival, rh = register(client, "missionrival")
    expect(client, "post", "/api/me/animal", 200, headers=h, json={"animal_id": 1})
    reach_hsk2(uid)
    assert expect(client, "get", "/api/lessons/path", 200, headers=h)["current_level"] == 2
    ms = missions(client, h)
    with SessionLocal() as db:
        all_slugs = {m.slug for m in db.query(models.Mission)}
    assert set(ms) == all_slugs and not any(m["locked"] for m in ms.values()), {s: m["locked"] for s, m in ms.items()}
    print(f"[PASS] an HSK 2 learner sees all {len(ms)} missions unlocked")

    done = {}

    def completes(slug, action, first_should_not=None):
        before = xp(uid)
        if first_should_not:
            first_should_not()
            assert missions(client, h)[slug]["status"] != "completed", f"{slug} completed by a wrong attempt"
        action()
        m = missions(client, h)[slug]
        assert m["status"] == "completed", (slug, m)
        assert xp(uid) >= before + m["mission"]["reward_xp"], (slug, xp(uid), before)
        done[slug] = m

    # listening: 3 Daily Voice Companion turns
    def voice_turns(n=3):
        for _ in range(n):
            expect(client, "post", "/api/voice/companion-chat", 200, headers=h,
                   json={"animal_id": 2, "spoken_text": "你好，我今天很好。", "history": []})
    completes("listen-drill", voice_turns)

    # conversations: the last learner line answered correctly
    for slug, scenario in (("greet-day", "greet-grandma"), ("first-order", "ordering-noodles"), ("find-way", "asking-directions"),
                           ("directions-master", "asking-directions"), ("fruit-shop", "buying-fruit")):
        if slug in done:  # find-way and directions-master share a scenario: one playthrough completes both
            continue
        sc_id, lines = learner_lines(scenario)

        def wrong_last(sc_id=sc_id, lines=lines):
            expect(client, "post", "/api/voice/attempt", 200, headers=h,
                   json={"spoken_text": "嗯", "scenario_id": sc_id, "dialogue_id": lines[-1][0]})

        def play(sc_id=sc_id, lines=lines):
            for did, answer in lines:
                expect(client, "post", "/api/voice/attempt", 200, headers=h,
                       json={"spoken_text": answer, "scenario_id": sc_id, "dialogue_id": did})
        completes(slug, play, first_should_not=wrong_last)
        if slug == "find-way":
            assert missions(client, h)["directions-master"]["status"] == "completed"
            done["directions-master"] = missions(client, h)["directions-master"]

    # cases: a correct verdict; "Repeat Detective" needs two
    def bad_verdict():
        expect(client, "post", "/api/world/scenarios/the-missing-bill/solve", 200, headers=h, json={"conclusion": "不知道"})

    def solve():
        r = expect(client, "post", "/api/world/scenarios/the-missing-bill/solve", 200, headers=h,
                   json={"conclusion": "顾客是对的，老板错了，他收了二十五元"})
        assert r["solved"], r
    completes("solve-case", solve, first_should_not=bad_verdict)
    assert missions(client, h)["case-streak"]["progress"] == 1
    completes("case-streak", solve)

    # teach: a Pet Teacher case fixed and explained
    def teach():
        with SessionLocal() as db:
            case = db.query(models.PetTeacherCase).join(models.HSKLevel).filter(models.HSKLevel.level <= 2).first()
            cid, fix, kws = case.id, case.correct_sentence, case.explanation_keywords or []
        r = expect(client, "post", f"/api/pet-teacher/lesson/{cid}/answer", 200, headers=h,
                   json={"correction": fix, "explanation": " ".join(kws) or "because"})
        assert r["success"], r

    def wrong_fix():
        with SessionLocal() as db:
            cid = db.query(models.PetTeacherCase).first().id
        expect(client, "post", f"/api/pet-teacher/lesson/{cid}/answer", 200, headers=h,
               json={"correction": "不对", "explanation": "不知道"})
    completes("teach-your-friend", teach, first_should_not=wrong_fix)

    # vocab: 10 correct graded answers
    def vocab_round():
        s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "vocab", "hsk_level": 1, "size": 10})
        with SessionLocal() as db:
            stored = db.get(models.PracticeSession, s["id"]).questions
        for i, q in enumerate(stored):
            expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h,
                   json={"index": i, "choice_id": q["item_id"]})
    completes("word-collector", vocab_round)

    # duel: winning one (a lost duel doesn't count)
    def duel(win):
        d = expect(client, "post", "/api/duels", 201, headers=h, json={"opponent_id": rival, "hsk_level": 1})
        expect(client, "post", f"/api/duels/{d['id']}/accept", 200, headers=rh)
        with SessionLocal() as db:
            qs = db.get(models.Duel, d["id"]).question_data["questions"]
        for headers, good in ((h, win), (rh, not win)):
            expect(client, "post", f"/api/duels/{d['id']}/start", 200, headers=headers)
            for i, q in enumerate(qs):
                choice = q["item_id"] if good else next(o for o in q["option_ids"] if o != q["item_id"])
                expect(client, "post", f"/api/duels/{d['id']}/answer", 200, headers=headers, json={"index": i, "choice_id": choice})
    completes("first-duel", lambda: duel(True), first_should_not=lambda: duel(False))

    assert set(done) == all_slugs, all_slugs - set(done)
    print(f"[PASS] all {len(done)} missions complete through their real activity (wrong attempts don't): {', '.join(sorted(done))}")

    # rewards were paid once: more of the same activity changes nothing
    paid = xp(uid)
    with SessionLocal() as db:
        coins = db.get(models.User, uid).coins
    solve()
    voice_turns(1)
    after = missions(client, h)
    assert all(after[s]["status"] == "completed" for s in all_slugs)
    with SessionLocal() as db:
        u = db.get(models.User, uid)
        # case/voice activity may earn quest progress, never a mission reward again
        assert u.coins - coins < min(m["mission"]["reward_coins"] for m in done.values() if m["mission"]["reward_coins"]) or u.coins == coins
    print("[PASS] repeating a completed mission's activity never pays its reward again")

    # the rival's missions were untouched by the learner's activity (except their own duels)
    rm = missions(client, rh)
    assert all(rm[s]["status"] != "completed" for s in all_slugs if s != "first-duel"), {s: m["status"] for s, m in rm.items()}
    print("[PASS] one learner's activity never moves another learner's missions")

print("ALL MISSION E2E TESTS PASSED")
