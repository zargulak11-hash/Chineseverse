"""Achievements: every unlock comes from a real learning action, progress
is real, opening pages unlocks nothing, the unlock note is shown once
(server-side), nothing unlocks twice -- not even under a race -- and
earlier unlocks survive."""

from app import models
from app.database import SessionLocal
from app.services import achievements as svc
from helpers import bearer, expect, register, unique_name
from trace_helpers import hand_trace, start, stroke_data


def play(client, h, body, *, correct=True):
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json=body)
    with SessionLocal() as db:
        keys = db.get(models.PracticeSession, s["id"]).questions
    for q in s["questions"]:
        choice = keys[q["index"]]["item_id"] if correct else next(o for o in keys[q["index"]]["option_ids"]
                                                                   if o != keys[q["index"]]["item_id"])
        expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h,
               json={"index": q["index"], "choice_id": choice})
    return expect(client, "post", f"/api/practice/sessions/{s['id']}/complete", 200, headers=h)


def board(client, h):
    return {a["code"]: a for a in expect(client, "get", "/api/achievements", 200, headers=h)}


def unlocked(client, h):
    return {c for c, a in board(client, h).items() if a["unlocked"]}


def rows(uid):
    with SessionLocal() as db:
        return db.query(models.UserAchievement).filter_by(user_id=uid).count()


def test_achievement_endpoints_require_sign_in(client):
    expect(client, "get", "/api/achievements", 401)
    expect(client, "post", "/api/achievements/seen", 401, json={"ids": []})


def test_new_learner_sees_every_achievement_locked_and_pages_unlock_nothing(client):
    with SessionLocal() as db:
        codes = {a.code for a in db.query(models.Achievement)}
        open_places = db.query(models.Location).filter(models.Location.unlock_level <= 1).count()
    assert set(svc.BY_CODE) <= codes, set(svc.BY_CODE) - codes
    uid, h = register(client, unique_name())
    b = board(client, h)
    assert set(b) == set(svc.BY_CODE)
    for a in b.values():
        assert not a["unlocked"] and a["target"] >= 1 and a["unit"] and a["to"], a
        # The only head start is real: the World places HSK 1 already opens.
        assert a["progress"] == (open_places if a["code"] == "world_4" else 0), a

    for url in ("/api/dashboard", "/api/stories", "/api/journey", "/api/passport", "/api/achievements",
                "/api/lessons/path", "/api/hanzi", "/api/progress"):
        client.get(url, headers=h)
    assert rows(uid) == 0 and not unlocked(client, h)


def test_each_learning_action_unlocks_its_own_achievement(client):
    uid, h = register(client, unique_name())

    # A finished tones round unlocks First Tones only among the round firsts.
    play(client, h, {"source": "tones"})
    got = unlocked(client, h)
    assert "first_tones" in got and "first_story" not in got and "first_lesson" not in got, got

    # Vocabulary: first word, and real progress toward 10 words.
    play(client, h, {"source": "vocab", "hsk_level": 1, "size": 6})
    b = board(client, h)
    with SessionLocal() as db:
        learned = db.query(models.UserVocabulary).filter(models.UserVocabulary.user_id == uid,
                                                         models.UserVocabulary.mastery > 0).count()
    assert b["first_word"]["unlocked"] and b["first_word"]["progress"] == 1
    assert 1 <= learned < 10 and b["words_10"]["progress"] == learned and not b["words_10"]["unlocked"], (learned, b["words_10"])
    assert b["reading_50"]["progress"] > 0

    # The unlock note: listed once, marked seen on the server, own-only.
    d = expect(client, "get", "/api/dashboard", 200, headers=h)
    new = {a["code"] for a in d["new_achievements"]}
    assert {"first_tones", "first_word"} <= new, new
    assert all(a["unlocked"] for a in d["achievements"]) and len(d["achievements"]) == rows(uid)
    assert d["next_achievements"] and not any(a["unlocked"] for a in d["next_achievements"])
    _, oh = register(client, unique_name("bystander"))
    ids = [a["id"] for a in d["new_achievements"]]
    assert expect(client, "post", "/api/achievements/seen", 200, headers=oh, json={"ids": ids})["marked"] == 0
    assert expect(client, "post", "/api/achievements/seen", 200, headers=h, json={"ids": ids})["marked"] == len(ids)
    assert expect(client, "post", "/api/achievements/seen", 200, headers=h, json={"ids": ids})["marked"] == 0
    assert expect(client, "get", "/api/dashboard", 200, headers=h)["new_achievements"] == []
    expect(client, "post", "/api/achievements/seen", 422, headers=h, json={"ids": list(range(500))})

    # Lesson, story, review, Real Chinese and Internet each unlock their first.
    path = expect(client, "get", "/api/lessons/path", 200, headers=h)
    play(client, h, {"source": "lesson", "lesson_id": path["current_lesson_id"]})
    play(client, h, {"source": "story", "story": "my-family"})
    play(client, h, {"source": "vocab", "hsk_level": 1, "size": 4}, correct=False)
    play(client, h, {"source": "review"})
    play(client, h, {"source": "scene", "scene": "restaurant"})
    play(client, h, {"source": "internet", "item": "hotpot-review"})
    got = unlocked(client, h)
    for code in ("first_lesson", "first_story", "first_review", "first_real_chinese", "first_internet"):
        assert code in got, (code, got)
    assert "first_trace" not in got and "first_voice" not in got and "case_solver" not in got

    # Tracing and speaking.
    with SessionLocal() as db:
        hid = db.query(models.Hanzi).filter(models.Hanzi.character == "好").first().id
    aid = start(client, h, hid)
    r = client.post(f"/api/hanzi/{hid}/write", headers=h, json={"attempt_id": aid, "strokes": hand_trace(stroke_data(hid))})
    assert r.status_code == 200, r.text
    expect(client, "post", "/api/voice/attempt", 200, headers=h,
           json={"spoken_text": "我要一碗牛肉面", "prompt_text": "Say you want noodles", "expected_keywords": ["面"]})
    got = unlocked(client, h)
    assert {"first_trace", "first_voice"} <= got, got
    b = board(client, h)
    assert b["speaking_10"]["progress"] == 1 and b["traces_10"]["progress"] == 1

    # Repeated checks add nothing.
    n = rows(uid)
    for _ in range(3):
        board(client, h)
        expect(client, "get", "/api/dashboard", 200, headers=h)
    assert rows(uid) == n


def test_a_lost_race_is_rolled_back_not_a_500_or_a_duplicate(client, monkeypatch):
    uid, h = register(client, unique_name())
    lesson_id = expect(client, "get", "/api/lessons/path", 200, headers=h)["current_lesson_id"]
    with SessionLocal() as db:
        db.add(models.Progress(user_id=uid, lesson_id=lesson_id, status="completed"))
        db.commit()
        first_lesson_id = db.query(models.Achievement).filter_by(code="first_lesson").one().id

    class RacingFacts(svc.Facts):
        def __init__(self, db, user):
            super().__init__(db, user)
            with SessionLocal() as other:  # the other request commits first
                other.add(models.UserAchievement(user_id=user.id, achievement_id=first_lesson_id))
                other.commit()

    with monkeypatch.context() as m:
        m.setattr(svc, "Facts", RacingFacts)
        with SessionLocal() as db:
            assert svc.check(db, db.get(models.User, uid)) == []
    with SessionLocal() as db:
        assert db.query(models.UserAchievement).filter_by(user_id=uid, achievement_id=first_lesson_id).count() == 1
        assert svc.check(db, db.get(models.User, uid)) == []


def test_unlocks_persist_across_login_and_are_never_taken_away(client):
    name = unique_name()
    uid, h = register(client, name)
    play(client, h, {"source": "vocab", "hsk_level": 1, "size": 6})
    before = {c: a["unlocked_at"] for c, a in board(client, h).items() if a["unlocked"]}
    assert before
    with SessionLocal() as db:
        duel = db.query(models.Achievement).filter_by(code="duel_win").one()
        db.add(models.UserAchievement(user_id=uid, achievement_id=duel.id))
        db.commit()
    tok = expect(client, "post", "/api/auth/login", 200, json={"username": name, "password": "secret1"})
    h2 = bearer(tok["access_token"])
    after_board = board(client, h2)
    after = {c: a["unlocked_at"] for c, a in after_board.items() if a["unlocked"]}
    assert all(after.get(c) == at for c, at in before.items()), "unlock dates changed"
    assert "duel_win" in after, "an unlock made under the old rules was taken away"

    # Progress stays within 0..target, and a met condition is always unlocked.
    for a in after_board.values():
        assert 0 <= a["progress"] <= a["target"], a
        assert a["unlocked"] or a["progress"] < a["target"], a
