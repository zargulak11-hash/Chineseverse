"""Every mission in the content, end to end: each one is reachable for a
learner at its HSK level and completes only through the real activity it
names (graded by the server), once, paying its reward once. Offline AI
grading (forced by conftest) keeps the run deterministic."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app import models
from app.database import SessionLocal
from app.services.lesson_path import path_state
from helpers import expect, register, unique_name

# Each mission's activity; find-way and directions-master share a scenario.
CONVERSATIONS = {
    "greet-day": "greet-grandma",
    "first-order": "ordering-noodles",
    "find-way": "asking-directions",
    "directions-master": "asking-directions",
    "fruit-shop": "buying-fruit",
}
OTHER_MISSIONS = {"listen-drill", "solve-case", "case-streak", "teach-your-friend", "word-collector", "first-duel"}
RIGHT_VERDICT = "顾客是对的，老板错了，他收了二十五元"


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


@pytest.fixture
def hsk2(client):
    """An HSK 2 learner with a companion, and a rival to duel."""
    uid, h = register(client, unique_name("missione2e"))
    rival, rh = register(client, unique_name("missionrival"))
    expect(client, "post", "/api/me/animal", 200, headers=h, json={"animal_id": 1})
    reach_hsk2(uid)
    assert expect(client, "get", "/api/lessons/path", 200, headers=h)["current_level"] == 2
    return SimpleNamespace(uid=uid, h=h, rival=rival, rh=rh)


class Activities:
    """The real activity behind each mission, and a wrong attempt at it."""

    def __init__(self, client, L):
        self.client, self.L = client, L

    def voice_turns(self, n=3):
        for _ in range(n):
            expect(self.client, "post", "/api/voice/companion-chat", 200, headers=self.L.h,
                   json={"animal_id": 2, "spoken_text": "你好，我今天很好。", "history": []})

    def play_conversation(self, scenario):
        sc_id, lines = learner_lines(scenario)
        for did, answer in lines:
            expect(self.client, "post", "/api/voice/attempt", 200, headers=self.L.h,
                   json={"spoken_text": answer, "scenario_id": sc_id, "dialogue_id": did})

    def wrong_last_line(self, scenario):
        sc_id, lines = learner_lines(scenario)
        expect(self.client, "post", "/api/voice/attempt", 200, headers=self.L.h,
               json={"spoken_text": "嗯", "scenario_id": sc_id, "dialogue_id": lines[-1][0]})

    def verdict(self, conclusion):
        return expect(self.client, "post", "/api/world/scenarios/the-missing-bill/solve", 200, headers=self.L.h,
                      json={"conclusion": conclusion})

    def solve(self):
        assert self.verdict(RIGHT_VERDICT)["solved"]

    def teach(self):
        with SessionLocal() as db:
            case = db.query(models.PetTeacherCase).join(models.HSKLevel).filter(models.HSKLevel.level <= 2).first()
            cid, fix, kws = case.id, case.correct_sentence, case.explanation_keywords or []
        r = expect(self.client, "post", f"/api/pet-teacher/lesson/{cid}/answer", 200, headers=self.L.h,
                   json={"correction": fix, "explanation": " ".join(kws) or "because"})
        assert r["success"], r

    def wrong_fix(self):
        with SessionLocal() as db:
            cid = db.query(models.PetTeacherCase).first().id
        expect(self.client, "post", f"/api/pet-teacher/lesson/{cid}/answer", 200, headers=self.L.h,
               json={"correction": "不对", "explanation": "不知道"})

    def vocab_round(self):
        s = expect(self.client, "post", "/api/practice/sessions", 201, headers=self.L.h,
                   json={"source": "vocab", "hsk_level": 1, "size": 10})
        with SessionLocal() as db:
            stored = db.get(models.PracticeSession, s["id"]).questions
        for i, q in enumerate(stored):
            expect(self.client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=self.L.h,
                   json={"index": i, "choice_id": q["item_id"]})

    def duel(self, win):
        c, L = self.client, self.L
        d = expect(c, "post", "/api/duels", 201, headers=L.h, json={"opponent_id": L.rival, "hsk_level": 1})
        expect(c, "post", f"/api/duels/{d['id']}/accept", 200, headers=L.rh)
        with SessionLocal() as db:
            qs = db.get(models.Duel, d["id"]).question_data["questions"]
        for headers, good in ((L.h, win), (L.rh, not win)):
            expect(c, "post", f"/api/duels/{d['id']}/start", 200, headers=headers)
            for i, q in enumerate(qs):
                choice = q["item_id"] if good else next(o for o in q["option_ids"] if o != q["item_id"])
                expect(c, "post", f"/api/duels/{d['id']}/answer", 200, headers=headers, json={"index": i, "choice_id": choice})

    def plan(self, slug):
        """(wrong attempt or None, the real activity) for a mission."""
        if slug in CONVERSATIONS:
            sc = CONVERSATIONS[slug]
            return (lambda: self.wrong_last_line(sc)), (lambda: self.play_conversation(sc))
        return {
            "listen-drill": (None, self.voice_turns),
            "solve-case": (lambda: self.verdict("不知道"), self.solve),
            "case-streak": (self.solve, self.solve),  # one solved case is not yet a streak of two
            "teach-your-friend": (self.wrong_fix, self.teach),
            "word-collector": (None, self.vocab_round),
            "first-duel": (lambda: self.duel(False), lambda: self.duel(True)),  # a lost duel doesn't count
        }[slug]


def test_every_seeded_mission_has_a_tested_activity(client):
    with SessionLocal() as db:
        all_slugs = {m.slug for m in db.query(models.Mission)}
    assert all_slugs == set(CONVERSATIONS) | OTHER_MISSIONS


def test_an_hsk2_learner_sees_every_mission_unlocked(client, hsk2):
    ms = missions(client, hsk2.h)
    with SessionLocal() as db:
        assert set(ms) == {m.slug for m in db.query(models.Mission)}
    assert not any(m["locked"] for m in ms.values()), {s: m["locked"] for s, m in ms.items()}


@pytest.mark.parametrize("slug", sorted(set(CONVERSATIONS) | OTHER_MISSIONS))
def test_a_mission_completes_only_through_its_real_activity(client, hsk2, slug):
    wrong, right = Activities(client, hsk2).plan(slug)
    before = xp(hsk2.uid)
    if wrong:
        wrong()
        assert missions(client, hsk2.h)[slug]["status"] != "completed", f"{slug} completed by a wrong attempt"
    right()
    m = missions(client, hsk2.h)[slug]
    assert m["status"] == "completed", (slug, m)
    assert xp(hsk2.uid) >= before + m["mission"]["reward_xp"], (slug, xp(hsk2.uid), before)


def test_repeating_a_completed_missions_activity_never_pays_again(client, hsk2):
    act = Activities(client, hsk2)
    act.solve()
    act.solve()
    act.voice_turns()
    ms = missions(client, hsk2.h)
    assert all(ms[s]["status"] == "completed" for s in ("solve-case", "case-streak", "listen-drill"))
    paid_coins = min(ms[s]["mission"]["reward_coins"] for s in ("solve-case", "case-streak", "listen-drill")
                     if ms[s]["mission"]["reward_coins"])
    with SessionLocal() as db:
        coins = db.get(models.User, hsk2.uid).coins
    act.solve()
    act.voice_turns(1)
    with SessionLocal() as db:
        # case/voice activity may earn quest progress, never a mission reward again
        assert db.get(models.User, hsk2.uid).coins - coins < paid_coins


def test_one_learners_activity_never_moves_another_learners_missions(client, hsk2):
    act = Activities(client, hsk2)
    act.solve()
    act.vocab_round()
    act.play_conversation("asking-directions")
    rm = missions(client, hsk2.rh)
    assert all(m["status"] != "completed" for m in rm.values()), {s: m["status"] for s, m in rm.items()}
