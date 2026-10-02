"""The permanent companion reacts to REAL graded learning events.

Covers: the reaction always names the user's permanent companion (and a
Daily Voice Companion chat never replaces it), correct/incorrect answers,
session memory transitions (wrong, wrong, right, right, right), repeated
misses on the same item, high-performance and lesson-completion
celebrations, real vocabulary in the reaction focus, Hanzi writing and
self-check reactions, DNA-milestone reactions that report the real skill
value, and that reactions never create or inflate progress.
"""

import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/companion.db"
os.environ["AI_API_KEY"] = ""  # voice chat must use its offline fallback here

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services import companion_reaction as cr  # noqa: E402
from app.services.practice import lesson_items  # noqa: E402

FRONTEND = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend", "src")


def expect(client, method, url, expected, **kwargs):
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == expected, f"{method.upper()} {url} -> {resp.status_code} (expected {expected}): {resp.text}"
    return resp.json() if resp.content else None


def register(client, name):
    data = expect(client, "post", "/api/auth/register", 201,
                  json={"username": name, "email": f"{name}@example.com", "password": "secret1"})
    return data["user"]["id"], {"Authorization": f"Bearer {data['access_token']}"}


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


with TestClient(app) as client:
    uid, h = register(client, "foxlearner")
    pid, ph = register(client, "pandalearner")
    oid, oh = register(client, "outsider")
    for hdr in (h, ph, oh):
        expect(client, "get", "/api/dashboard", 200, headers=hdr)  # creates skill rows

    # ------------------------------------------------ permanent companion identity
    expect(client, "post", "/api/me/animal", 200, headers=h, json={"animal_id": animal_id("fox")})
    expect(client, "post", "/api/me/animal", 200, headers=ph, json={"animal_id": animal_id("panda")})
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "vocab", "hsk_level": 1, "size": 6})
    assert s["reaction"]["companion"] == {"slug": "fox"}, s["reaction"]
    assert s["reaction"]["mood"] == "neutral" and s["reaction"]["event"] == "session_start", s["reaction"]
    ps = expect(client, "post", "/api/practice/sessions", 201, headers=ph, json={"source": "vocab", "hsk_level": 1, "size": 4})
    assert ps["reaction"]["companion"] == {"slug": "panda"}, ps["reaction"]
    print("[PASS] reactions carry each learner's own permanent companion (fox vs panda)")

    # Daily Voice Companion: chatting with the wolf for one session must not
    # replace the fox anywhere.
    expect(client, "post", "/api/voice/companion-chat", 200, headers=h,
           json={"animal_id": animal_id("wolf"), "spoken_text": "你好，我是学生。"})
    assert expect(client, "get", "/api/dashboard", 200, headers=h)["animal"]["slug"] == "fox"
    with SessionLocal() as db:
        assert db.get(models.User, uid).animal_id == animal_id("fox")
    print("[PASS] Daily Voice Companion chat leaves the permanent companion untouched")

    # ------------------------------------------------ start reactions change nothing
    before = progress_snapshot(uid)
    sid, rendered = s["id"], s["questions"]
    stored = stored_questions(sid)
    expect(client, "get", f"/api/practice/sessions/{sid}", 200, headers=h)
    assert progress_snapshot(uid) == before, "starting/reading a round must not create progress"
    print("[PASS] starting a round (and its greeting) creates no progress, XP or DNA")

    # ------------------------------------------------ session memory transitions
    # wrong, wrong, right, right, right -> encouraging, worried, encouraging, happy, proud
    moods = []
    vocab_before = skill(uid, "vocabulary")
    for i, correct in enumerate([False, False, True, True, True]):
        choice = stored[i]["item_id"] if correct else wrong_choice(rendered[i], stored[i])
        r = expect(client, "post", f"/api/practice/sessions/{sid}/answer", 200, headers=h,
                   json={"index": i, "choice_id": choice, "response_ms": 9000})
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
    print(f"[PASS] session memory: {' -> '.join(m for m, _ in moods)}")

    # correct -> wrong -> wrong : happy/.. -> encouraging -> worried
    s2 = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "hanzi", "hsk_level": 1, "size": 4})
    st2 = stored_questions(s2["id"])
    seq = []
    for i, correct in enumerate([True, False, False, False]):
        choice = st2[i]["item_id"] if correct else wrong_choice(s2["questions"][i], st2[i])
        r = expect(client, "post", f"/api/practice/sessions/{s2['id']}/answer", 200, headers=h,
                   json={"index": i, "choice_id": choice, "response_ms": 9000})
        seq.append(r["reaction"]["mood"])
        assert r["reaction"]["focus"]["item_type"] == "hanzi"
    assert seq[0] in ("happy", "proud") and seq[1] == "encouraging" and seq[2] == "worried" and seq[3] == "worried", seq
    done = expect(client, "post", f"/api/practice/sessions/{s2['id']}/complete", 200, headers=h)
    assert done["reaction"]["mood"] == "worried" and done["reaction"]["cause"] == "needs_review", done["reaction"]
    assert done["reaction"]["focus"] and done["reaction"]["focus"]["item_type"] == "hanzi", done["reaction"]
    print(f"[PASS] correct -> wrong -> wrong: {' -> '.join(seq)}; weak round ends worried + review focus")

    # four misses in a row -> the companion is sad WITH the learner (never shaming)
    s3 = expect(client, "post", "/api/practice/sessions", 201, headers=oh, json={"source": "grammar", "hsk_level": 1, "size": 5})
    st3 = stored_questions(s3["id"])
    for i in range(4):
        r = expect(client, "post", f"/api/practice/sessions/{s3['id']}/answer", 200, headers=oh,
                   json={"index": i, "choice_id": wrong_choice(s3["questions"][i], st3[i])})
    assert r["reaction"]["mood"] == "sad" and r["reaction"]["cause"] == "long_slump", r["reaction"]
    print("[PASS] repeated mistakes -> supportive worried/sad states")

    # ------------------------------------------------ high performance
    s4 = expect(client, "post", "/api/practice/sessions", 201, headers=ph, json={"source": "vocab", "hsk_level": 2, "size": 6})
    st4 = stored_questions(s4["id"])
    moods4 = []
    for i, q in enumerate(st4):
        r = expect(client, "post", f"/api/practice/sessions/{s4['id']}/answer", 200, headers=ph,
                   json={"index": i, "choice_id": q["item_id"], "response_ms": 9000})
        moods4.append(r["reaction"]["mood"])
    # vocabulary DNA goes 2, 4, 6, 8, 10 over the vocabulary-type questions:
    # the 5th answer genuinely crosses the 10-point step (question 3 is a
    # listening one), and the 6th in a row is a hot streak.
    assert moods4[2] == "proud" and moods4[4] == "proud" and moods4[5] == "excited", moods4
    done = expect(client, "post", f"/api/practice/sessions/{s4['id']}/complete", 200, headers=ph)
    assert done["reaction"]["mood"] == "celebrating" and done["reaction"]["cause"] == "outstanding", done["reaction"]
    assert done["reaction"]["skill"]["code"] == "vocabulary" or done["reaction"]["skill"]["code"] == "listening"
    assert done["reaction"]["skill"]["value"] == round(skill(pid, done["reaction"]["skill"]["code"]), 1)
    print(f"[PASS] high performance: {' -> '.join(moods4)} -> celebrating; trained skill reports the real DNA value")

    # ------------------------------------------------ lesson start + completion
    # The learner's current lesson on the path: the only lesson both fresh
    # learners here may practice and complete.
    current_id = expect(client, "get", "/api/lessons/path", 200, headers=h)["current_lesson_id"]
    with SessionLocal() as db:
        lesson = db.get(models.Lesson, current_id)
        assert lesson is not None and lesson_items(db, lesson)["vocab"], "current lesson teaches no words"
        lesson_words = {w.simplified for w in lesson_items(db, lesson)["vocab"]}
        lesson_id = lesson.id
    ls = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "lesson", "lesson_id": lesson_id})
    start = ls["reaction"]
    assert start["event"] == "lesson_start" and start["words"], start
    assert {w["hanzi"] for w in start["words"]} <= lesson_words, (start["words"], lesson_words)
    lq = stored_questions(ls["id"])
    for i, q in enumerate(lq):
        expect(client, "post", f"/api/practice/sessions/{ls['id']}/answer", 200, headers=h, json={"index": i, "choice_id": q["item_id"]})
    done = expect(client, "post", f"/api/practice/sessions/{ls['id']}/complete", 200, headers=h)
    assert done["reaction"]["event"] == "lesson_complete" and done["reaction"]["mood"] == "celebrating", done["reaction"]
    # practicing the already-completed lesson again badly is NOT another celebration
    ls2 = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "lesson", "lesson_id": lesson_id})
    lq2 = stored_questions(ls2["id"])
    expect(client, "post", f"/api/practice/sessions/{ls2['id']}/answer", 200, headers=h,
           json={"index": 0, "choice_id": wrong_choice(ls2["questions"][0], lq2[0])})
    again = expect(client, "post", f"/api/practice/sessions/{ls2['id']}/complete", 200, headers=h)
    assert again["lesson_status"] == "completed" and again["reaction"]["event"] == "complete", again["reaction"]
    assert again["reaction"]["mood"] != "celebrating"
    print("[PASS] lesson start previews its real words; completion celebrates once, re-practice does not")

    # ------------------------------------------------ the same item missed again and again
    lw = expect(client, "post", "/api/practice/sessions", 201, headers=oh, json={"source": "lesson", "lesson_id": lesson_id})
    target = stored_questions(lw["id"])[0]["item_id"]
    causes = []
    for _ in range(3):
        sess = expect(client, "post", "/api/practice/sessions", 201, headers=oh, json={"source": "lesson", "lesson_id": lesson_id})
        st = stored_questions(sess["id"])
        idx = next(i for i, q in enumerate(st) if q["item_id"] == target and q["item_type"] == "vocab")
        r = expect(client, "post", f"/api/practice/sessions/{sess['id']}/answer", 200, headers=oh,
                   json={"index": idx, "choice_id": wrong_choice(sess["questions"][idx], st[idx])})
        causes.append((r["reaction"]["mood"], r["reaction"]["cause"]))
    assert causes == [("encouraging", "miss"), ("serious", "repeat_item"), ("frustrated", "tricky_item")], causes
    assert "再练习" in cr.zh_line("repeat_item", "vocab")
    print(f"[PASS] repeated failure on one word: {causes}")

    # ------------------------------------------------ DNA milestone reacts to the real value
    set_skill(pid, "vocabulary", 9.0)  # test setup only: position the skill below a boundary
    s5 = expect(client, "post", "/api/practice/sessions", 201, headers=ph, json={"source": "vocab", "hsk_level": 3, "size": 4})
    st5 = stored_questions(s5["id"])
    assert st5[0]["type"] == "meaning_to_word"
    r = expect(client, "post", f"/api/practice/sessions/{s5['id']}/answer", 200, headers=ph,
               json={"index": 0, "choice_id": st5[0]["item_id"], "response_ms": 9000})
    assert r["reaction"]["cause"] == "skill_up" and r["reaction"]["skill"]["code"] == "vocabulary", r["reaction"]
    assert r["reaction"]["skill"]["value"] == skill(pid, "vocabulary") == 11.0, (r["reaction"], skill(pid, "vocabulary"))
    print("[PASS] a real DNA step (9 -> 11 vocabulary) triggers a skill reaction with the true value, +2 only")

    # ------------------------------------------------ writing + self-check reactions
    with SessionLocal() as db:
        hz = db.query(models.Hanzi).filter(models.Hanzi.stroke_data.isnot(None)).order_by(models.Hanzi.id).first()
        hz_id = hz.id
        word_id = db.query(models.VocabularyWord).order_by(models.VocabularyWord.id).first().id
        topic_id = db.query(models.GrammarTopic).order_by(models.GrammarTopic.id).first().id
    w = expect(client, "post", f"/api/hanzi/{hz_id}/write", 200, headers=h, json={"total_mistakes": 0})
    assert w["reaction"]["event"] == "hanzi_write" and w["reaction"]["mood"] == "proud" and w["reaction"]["cause"] == "clean_trace", w
    assert w["reaction"]["focus"]["hanzi"] == hz.character
    w = expect(client, "post", f"/api/hanzi/{hz_id}/write", 200, headers=h, json={"total_mistakes": 6})
    assert w["reaction"]["mood"] == "encouraging" and w["reaction"]["cause"] == "shaky_trace", w
    # writing mastery so far 25 + 8 = 33; +25 -> 58, +25 -> 83, +25 -> 100 (>= 85: mastered)
    trace = [expect(client, "post", f"/api/hanzi/{hz_id}/write", 200, headers=h, json={"total_mistakes": 0}) for _ in range(3)]
    assert [t["writing_status"] for t in trace] == ["practicing", "practicing", "mastered"], trace
    assert trace[2]["reaction"]["mood"] == "celebrating" and trace[2]["reaction"]["milestone"] == "writing_mastered", trace[2]
    print("[PASS] Hanzi tracing: clean -> proud, shaky -> encouraging, writing mastered -> celebrating")

    # A Hanzi "got it" is a self-check, so it only counts when the card is due
    # (a client-sent "delta" never chooses the step). Time passing is
    # simulated by moving the schedule back between reviews.
    from datetime import datetime, timedelta

    def make_due():
        with SessionLocal() as db:
            rec = db.query(models.UserHanzi).filter_by(user_id=uid, hanzi_id=hz_id).one()
            rec.next_review_at = datetime.utcnow() - timedelta(minutes=1)
            db.commit()

    make_due()  # this character was already reviewed above
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
    assert hr["reaction"]["focus"]["hanzi"] == hz.character
    print("[PASS] Hanzi self-checks react (mastered -> proud milestone); an early 'got it' changes nothing")

    # ------------------------------------------------ review
    rv = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "review"})
    assert rv["reaction"]["event"] == "review_start" and rv["reaction"]["mood"] == "serious", rv["reaction"]
    fresh_id, fresh = register(client, "freshlearner")
    empty = expect(client, "post", "/api/practice/sessions", 200, headers=fresh, json={"source": "review"})
    assert empty["reaction"]["event"] == "review_clear" and empty["reaction"]["mood"] == "happy", empty
    print("[PASS] review start is focused; an empty queue gets a calm, happy reaction")

    # ------------------------------------------------ authorization is unchanged
    expect(client, "post", "/api/practice/sessions", 401, json={"source": "vocab", "hsk_level": 1})
    expect(client, "post", f"/api/practice/sessions/{sid}/answer", 404, headers=oh, json={"index": 5, "choice_id": stored[5]["item_id"]})
    expect(client, "post", f"/api/practice/sessions/{sid}/complete", 404, headers=oh)
    expect(client, "post", f"/api/hanzi/{hz_id}/write", 401, json={"total_mistakes": 0})
    expect(client, "post", f"/api/hanzi/{hz_id}/review", 401, json={"correct": True})
    # the old self-graded vocab/grammar endpoints are gone
    assert client.post(f"/api/vocab/{word_id}/review", headers=h, json={"correct": True}).status_code in (404, 405)
    assert client.post(f"/api/grammar/{topic_id}/practice", headers=h, json={"correct": True}).status_code in (404, 405)
    print("[PASS] reactions stay behind the same auth/ownership checks (401/404)")

    # ------------------------------------------------ frontend species map covers the real roster
    with SessionLocal() as db:
        slugs = {a.slug for a in db.query(models.Animal)}
    species_src = open(os.path.join(FRONTEND, "companionSpecies.js"), encoding="utf-8").read()
    mapped = set(re.findall(r'^\s*"?([a-z-]+)"?:\s*\{\s*motion:', species_src, re.M))
    assert slugs <= mapped, f"species without a visual profile: {slugs - mapped}"
    moods_src = set(re.findall(r'^\s*([a-z]+):\s*\{\s*face:', species_src, re.M))
    assert set(cr.MOODS) <= moods_src, f"moods without a visual state: {set(cr.MOODS) - moods_src}"
    print(f"[PASS] every one of the {len(slugs)} companions has its own species profile; every mood has a visual")

print("ALL COMPANION REACTION TESTS PASSED")
