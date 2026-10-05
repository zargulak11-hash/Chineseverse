"""The permanent companion reacts to REAL graded learning events.

Covers: the reaction always names the user's permanent companion (and a
Daily Voice Companion chat never replaces it), correct/incorrect answers,
session memory transitions (wrong, wrong, right, right, right), repeated
misses on the same item, high-performance and lesson-completion
celebrations, real vocabulary in the reaction focus, Hanzi writing and
self-check reactions, DNA-milestone reactions that report the real skill
value, and that reactions never create or inflate progress.
"""

import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app import models
from app.database import SessionLocal
from app.services import companion_reaction as cr
from app.services.practice import lesson_items
from helpers import expect, register, unique_name
from trace_helpers import trace as draw_trace

FRONTEND_SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"


def animal_id(slug):
    with SessionLocal() as db:
        return db.query(models.Animal).filter_by(slug=slug).one().id


def stored_questions(sid):
    with SessionLocal() as db:
        return db.get(models.PracticeSession, sid).questions


def wrong_choice(q_rendered, q_stored):
    return next(o["id"] for o in q_rendered["options"] if o["id"] != q_stored["item_id"])


def progress_snapshot(uid):
    """Everything a reaction must never touch on its own."""
    with SessionLocal() as db:
        u = db.get(models.User, uid)
        return {
            "xp": u.total_xp,
            "skills": {s.skill.code: s.mastery for s in u.user_skills if s.skill},
            "vocab": db.query(models.UserVocabulary).filter_by(user_id=uid).count(),
            "hanzi": db.query(models.UserHanzi).filter_by(user_id=uid).count(),
            "grammar": db.query(models.UserGrammar).filter_by(user_id=uid).count(),
            "progress": db.query(models.Progress).filter_by(user_id=uid).count(),
            "mistakes": db.query(models.LearningMistake).filter_by(user_id=uid).count(),
        }


def set_skill(uid, code, value):
    with SessionLocal() as db:
        us = (db.query(models.UserSkill).join(models.Skill)
              .filter(models.UserSkill.user_id == uid, models.Skill.code == code).one())
        us.mastery = value
        db.commit()


def skill(uid, code):
    with SessionLocal() as db:
        return (db.query(models.UserSkill).join(models.Skill)
                .filter(models.UserSkill.user_id == uid, models.Skill.code == code).one().mastery)


@pytest.fixture
def learner(client):
    """learner(companion_slug=None) -> (uid, headers), with skill rows."""
    def make(companion=None):
        uid, h = register(client, unique_name())
        expect(client, "get", "/api/dashboard", 200, headers=h)  # creates skill rows
        if companion:
            expect(client, "post", "/api/me/animal", 200, headers=h, json={"animal_id": animal_id(companion)})
        return uid, h
    return make


def start_round(client, h, **body):
    return expect(client, "post", "/api/practice/sessions", 201, headers=h, json=body)


def answer(client, h, sid, index, choice, response_ms=None):
    body = {"index": index, "choice_id": choice}
    if response_ms is not None:
        body["response_ms"] = response_ms
    return expect(client, "post", f"/api/practice/sessions/{sid}/answer", 200, headers=h, json=body)


def test_reactions_carry_each_learners_own_permanent_companion(client, learner):
    uid, h = learner("fox")
    _, ph = learner("panda")
    s = start_round(client, h, source="vocab", hsk_level=1, size=6)
    assert s["reaction"]["companion"] == {"slug": "fox"}, s["reaction"]
    assert s["reaction"]["mood"] == "neutral" and s["reaction"]["event"] == "session_start", s["reaction"]
    ps = start_round(client, ph, source="vocab", hsk_level=1, size=4)
    assert ps["reaction"]["companion"] == {"slug": "panda"}, ps["reaction"]

    # Daily Voice Companion: chatting with the wolf for one session must not
    # replace the fox anywhere.
    expect(client, "post", "/api/voice/companion-chat", 200, headers=h,
           json={"animal_id": animal_id("wolf"), "spoken_text": "你好，我是学生。"})
    assert expect(client, "get", "/api/dashboard", 200, headers=h)["animal"]["slug"] == "fox"
    with SessionLocal() as db:
        assert db.get(models.User, uid).animal_id == animal_id("fox")


def test_session_memory_moves_with_real_answers_and_adds_no_progress(client, learner):
    uid, h = learner("fox")
    s = start_round(client, h, source="vocab", hsk_level=1, size=6)
    before = progress_snapshot(uid)
    sid, rendered = s["id"], s["questions"]
    stored = stored_questions(sid)
    expect(client, "get", f"/api/practice/sessions/{sid}", 200, headers=h)
    assert progress_snapshot(uid) == before, "starting/reading a round must not create progress"

    # wrong, wrong, right, right, right -> encouraging, worried, encouraging, happy, proud
    moods = []
    vocab_before = skill(uid, "vocabulary")
    for i, correct in enumerate([False, False, True, True, True]):
        choice = stored[i]["item_id"] if correct else wrong_choice(rendered[i], stored[i])
        r = answer(client, h, sid, i, choice, 9000)
        assert r["correct"] is correct
        rx = r["reaction"]
        assert rx["mood"] in cr.MOODS and rx["zh"] and rx["companion"] == {"slug": "fox"}, rx
        moods.append((rx["mood"], rx["cause"]))
        # the reaction's focus is the REAL curriculum word just asked about
        with SessionLocal() as db:
            word = db.get(models.VocabularyWord, stored[i]["item_id"])
        assert rx["focus"]["hanzi"] == word.simplified and rx["focus"]["pinyin"] == word.pinyin, rx["focus"]
        if word.example:
            assert rx["focus"]["example"] == word.example
    assert [m for m, _ in moods] == ["encouraging", "worried", "encouraging", "happy", "proud"], moods
    assert moods[2][1] == "recovering" and moods[4][1] == "streak", moods
    # the DNA moved exactly as practice always moves it (2 misses at -0.3,
    # clamped at 0, then 3 hits at +2) -- the reactions added nothing
    expected = max(0.0, max(0.0, vocab_before - 0.3) - 0.3) + 6.0
    assert abs(skill(uid, "vocabulary") - expected) < 0.01, (skill(uid, "vocabulary"), expected)


def test_a_weak_round_ends_worried_with_a_review_focus(client, learner):
    _, h = learner("fox")
    s2 = start_round(client, h, source="hanzi", hsk_level=1, size=4)
    st2 = stored_questions(s2["id"])
    seq = []
    for i, correct in enumerate([True, False, False, False]):
        choice = st2[i]["item_id"] if correct else wrong_choice(s2["questions"][i], st2[i])
        r = answer(client, h, s2["id"], i, choice, 9000)
        seq.append(r["reaction"]["mood"])
        assert r["reaction"]["focus"]["item_type"] == "hanzi"
    assert seq[0] in ("happy", "proud") and seq[1] == "encouraging" and seq[2] == "worried" and seq[3] == "worried", seq
    done = expect(client, "post", f"/api/practice/sessions/{s2['id']}/complete", 200, headers=h)
    assert done["reaction"]["mood"] == "worried" and done["reaction"]["cause"] == "needs_review", done["reaction"]
    assert done["reaction"]["focus"] and done["reaction"]["focus"]["item_type"] == "hanzi", done["reaction"]


def test_a_long_slump_makes_the_companion_sad_with_the_learner(client, learner):
    _, oh = learner()
    s3 = start_round(client, oh, source="grammar", hsk_level=1, size=5)
    st3 = stored_questions(s3["id"])
    for i in range(4):
        r = answer(client, oh, s3["id"], i, wrong_choice(s3["questions"][i], st3[i]))
    assert r["reaction"]["mood"] == "sad" and r["reaction"]["cause"] == "long_slump", r["reaction"]


def test_high_performance_celebrates_with_the_real_dna_value(client, learner):
    pid, ph = learner("panda")
    s4 = start_round(client, ph, source="vocab", hsk_level=2, size=6)
    moods4 = [answer(client, ph, s4["id"], i, q["item_id"], 9000)["reaction"]["mood"]
              for i, q in enumerate(stored_questions(s4["id"]))]
    # vocabulary DNA goes 2, 4, 6, 8, 10 over the vocabulary-type questions:
    # the 5th answer genuinely crosses the 10-point step (question 3 is a
    # listening one), and the 6th in a row is a hot streak.
    assert moods4[2] == "proud" and moods4[4] == "proud" and moods4[5] == "excited", moods4
    done = expect(client, "post", f"/api/practice/sessions/{s4['id']}/complete", 200, headers=ph)
    assert done["reaction"]["mood"] == "celebrating" and done["reaction"]["cause"] == "outstanding", done["reaction"]
    assert done["reaction"]["skill"]["code"] in ("vocabulary", "listening")
    assert done["reaction"]["skill"]["value"] == round(skill(pid, done["reaction"]["skill"]["code"]), 1)


def test_a_dna_step_reacts_with_the_true_value(client, learner):
    pid, ph = learner("panda")
    set_skill(pid, "vocabulary", 9.0)  # test setup only: position the skill below a boundary
    s5 = start_round(client, ph, source="vocab", hsk_level=3, size=4)
    st5 = stored_questions(s5["id"])
    assert st5[0]["type"] == "meaning_to_word"
    r = answer(client, ph, s5["id"], 0, st5[0]["item_id"], 9000)
    assert r["reaction"]["cause"] == "skill_up" and r["reaction"]["skill"]["code"] == "vocabulary", r["reaction"]
    assert r["reaction"]["skill"]["value"] == skill(pid, "vocabulary") == 11.0, (r["reaction"], skill(pid, "vocabulary"))


def current_lesson_id(client, h):
    return expect(client, "get", "/api/lessons/path", 200, headers=h)["current_lesson_id"]


def test_lesson_start_previews_real_words_and_completion_celebrates_once(client, learner):
    _, h = learner("fox")
    lesson_id = current_lesson_id(client, h)
    with SessionLocal() as db:
        lesson = db.get(models.Lesson, lesson_id)
        assert lesson is not None and lesson_items(db, lesson)["vocab"], "current lesson teaches no words"
        lesson_words = {w.simplified for w in lesson_items(db, lesson)["vocab"]}
    ls = start_round(client, h, source="lesson", lesson_id=lesson_id)
    start = ls["reaction"]
    assert start["event"] == "lesson_start" and start["words"], start
    assert {w["hanzi"] for w in start["words"]} <= lesson_words, (start["words"], lesson_words)
    for i, q in enumerate(stored_questions(ls["id"])):
        answer(client, h, ls["id"], i, q["item_id"])
    done = expect(client, "post", f"/api/practice/sessions/{ls['id']}/complete", 200, headers=h)
    assert done["reaction"]["event"] == "lesson_complete" and done["reaction"]["mood"] == "celebrating", done["reaction"]

    # practicing the already-completed lesson again badly is NOT another celebration
    ls2 = start_round(client, h, source="lesson", lesson_id=lesson_id)
    lq2 = stored_questions(ls2["id"])
    answer(client, h, ls2["id"], 0, wrong_choice(ls2["questions"][0], lq2[0]))
    again = expect(client, "post", f"/api/practice/sessions/{ls2['id']}/complete", 200, headers=h)
    assert again["lesson_status"] == "completed" and again["reaction"]["event"] == "complete", again["reaction"]
    assert again["reaction"]["mood"] != "celebrating"


def test_the_same_word_missed_again_and_again(client, learner):
    _, oh = learner()
    lesson_id = current_lesson_id(client, oh)
    lw = start_round(client, oh, source="lesson", lesson_id=lesson_id)
    target = stored_questions(lw["id"])[0]["item_id"]
    causes = []
    for _ in range(3):
        sess = start_round(client, oh, source="lesson", lesson_id=lesson_id)
        st = stored_questions(sess["id"])
        idx = next(i for i, q in enumerate(st) if q["item_id"] == target and q["item_type"] == "vocab")
        r = answer(client, oh, sess["id"], idx, wrong_choice(sess["questions"][idx], st[idx]))
        causes.append((r["reaction"]["mood"], r["reaction"]["cause"]))
    assert causes == [("encouraging", "miss"), ("serious", "repeat_item"), ("frustrated", "tricky_item")], causes
    assert "再练习" in cr.zh_line("repeat_item", "vocab")


def test_writing_and_self_check_reactions(client, learner):
    uid, h = learner("fox")
    with SessionLocal() as db:
        hz = db.query(models.Hanzi).filter(models.Hanzi.stroke_data.isnot(None)).order_by(models.Hanzi.id).first()
        hz_id, character = hz.id, hz.character

    # Real traces drawn over the character's stroke data (tests/trace_helpers.py);
    # the server re-checks every stroke and counts the misses itself.
    def traced(mistakes=0, seed=1):
        r = draw_trace(client, h, hz_id, mistakes=mistakes, seed=seed)
        assert r.status_code == 200, r.text
        return r.json()

    w = traced()
    assert w["reaction"]["event"] == "hanzi_write" and w["reaction"]["mood"] == "proud" and w["reaction"]["cause"] == "clean_trace", w
    assert w["reaction"]["focus"]["hanzi"] == character
    w = traced(mistakes=6, seed=2)
    assert w["reaction"]["mood"] == "encouraging" and w["reaction"]["cause"] == "shaky_trace", w
    # writing mastery so far 25 + 8 = 33; +25 -> 58, +25 -> 83, +25 -> 100 (>= 85: mastered)
    trace = [traced(seed=3 + i) for i in range(3)]
    assert [t["writing_status"] for t in trace] == ["practicing", "practicing", "mastered"], trace
    assert trace[2]["reaction"]["mood"] == "celebrating" and trace[2]["reaction"]["milestone"] == "writing_mastered", trace[2]

    # A Hanzi "got it" is a self-check, so it only counts when the card is due
    # (a client-sent "delta" never chooses the step). Time passing is
    # simulated by moving the schedule back between reviews.
    def make_due():
        with SessionLocal() as db:
            rec = db.query(models.UserHanzi).filter_by(user_id=uid, hanzi_id=hz_id).one()
            rec.next_review_at = datetime.utcnow() - timedelta(minutes=1)
            db.commit()

    make_due()  # this character was already reviewed by the tracing above
    v = expect(client, "post", f"/api/hanzi/{hz_id}/review", 200, headers=h, json={"correct": True, "delta": 100})
    assert v["counted"] and v["status"] != "mastered" and v["mastery"] <= 20, v
    assert v["reaction"]["event"] == "self_check" and v["reaction"]["companion"] == {"slug": "fox"}, v["reaction"]
    early = expect(client, "post", f"/api/hanzi/{hz_id}/review", 200, headers=h, json={"correct": True})
    assert not early["counted"] and early["mastery"] == v["mastery"] and early["reaction"] is None, early
    for _ in range(10):
        if v["status"] == "mastered":
            break
        make_due()
        v = expect(client, "post", f"/api/hanzi/{hz_id}/review", 200, headers=h, json={"correct": True})
    assert v["status"] == "mastered" and v["reaction"]["milestone"] == "mastered" and v["reaction"]["mood"] == "proud", v["reaction"]
    hr = expect(client, "post", f"/api/hanzi/{hz_id}/review", 200, headers=h, json={"correct": False})
    assert hr["counted"] and hr["reaction"]["mood"] in ("encouraging", "serious"), hr["reaction"]
    assert hr["reaction"]["focus"]["hanzi"] == character


def test_review_start_is_focused_and_an_empty_queue_is_calm(client, learner):
    _, h = learner("fox")
    s = start_round(client, h, source="vocab", hsk_level=1, size=4)
    st = stored_questions(s["id"])
    answer(client, h, s["id"], 0, wrong_choice(s["questions"][0], st[0]))
    rv = start_round(client, h, source="review")
    assert rv["reaction"]["event"] == "review_start" and rv["reaction"]["mood"] == "serious", rv["reaction"]
    _, fresh = learner()
    empty = expect(client, "post", "/api/practice/sessions", 200, headers=fresh, json={"source": "review"})
    assert empty["reaction"]["event"] == "review_clear" and empty["reaction"]["mood"] == "happy", empty


def test_reactions_stay_behind_the_same_auth_and_ownership_checks(client, learner):
    _, h = learner("fox")
    _, oh = learner()
    s = start_round(client, h, source="vocab", hsk_level=1, size=6)
    stored = stored_questions(s["id"])
    with SessionLocal() as db:
        hz_id = db.query(models.Hanzi).filter(models.Hanzi.stroke_data.isnot(None)).order_by(models.Hanzi.id).first().id
        word_id = db.query(models.VocabularyWord).order_by(models.VocabularyWord.id).first().id
        topic_id = db.query(models.GrammarTopic).order_by(models.GrammarTopic.id).first().id
    expect(client, "post", "/api/practice/sessions", 401, json={"source": "vocab", "hsk_level": 1})
    expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 404, headers=oh, json={"index": 5, "choice_id": stored[5]["item_id"]})
    expect(client, "post", f"/api/practice/sessions/{s['id']}/complete", 404, headers=oh)
    expect(client, "post", f"/api/hanzi/{hz_id}/write/start", 401)
    expect(client, "post", f"/api/hanzi/{hz_id}/write", 401, json={"attempt_id": 1, "strokes": [{"points": [[0, 0], [1, 1]], "matched": True}]})
    expect(client, "post", f"/api/hanzi/{hz_id}/review", 401, json={"correct": True})
    # the old self-graded vocab/grammar endpoints are gone
    assert client.post(f"/api/vocab/{word_id}/review", headers=h, json={"correct": True}).status_code in (404, 405)
    assert client.post(f"/api/grammar/{topic_id}/practice", headers=h, json={"correct": True}).status_code in (404, 405)


def test_every_companion_and_mood_has_a_frontend_visual(client):
    with SessionLocal() as db:
        slugs = {a.slug for a in db.query(models.Animal)}
    species_src = (FRONTEND_SRC / "companionSpecies.js").read_text(encoding="utf-8")
    mapped = set(re.findall(r'^\s*"?([a-z-]+)"?:\s*\{\s*motion:', species_src, re.M))
    assert slugs <= mapped, f"species without a visual profile: {slugs - mapped}"
    moods_src = set(re.findall(r'^\s*([a-z]+):\s*\{\s*face:', species_src, re.M))
    assert set(cr.MOODS) <= moods_src, f"moods without a visual state: {set(cr.MOODS) - moods_src}"
