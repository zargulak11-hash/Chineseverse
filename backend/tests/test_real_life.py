"""Real Chinese scenes, One Sentence lessons, and the companion's learning
memory: real curriculum words, server grading, and memories only from
things the learner really did."""

from datetime import datetime, timedelta

import pytest

from app import models
from app.database import SessionLocal
from app.services.real_life_content import SCENES
from helpers import expect, register, unique_name

SENTENCE = "我昨天去了北京。"


def stored(sid):
    with SessionLocal() as db:
        s = db.get(models.PracticeSession, sid)
        return s.questions, s.answers


def set_skills(uid, mastery):
    with SessionLocal() as db:
        for us in db.query(models.UserSkill).filter_by(user_id=uid):
            us.mastery = mastery
        db.commit()


def skill(uid, code):
    with SessionLocal() as db:
        us = (db.query(models.UserSkill).join(models.Skill)
              .filter(models.UserSkill.user_id == uid, models.Skill.code == code).first())
        return us.mastery if us else 0.0


def pin_first_question(sid, qtype, target, wrong):
    """Make question 0 of a real round ask about `target` with `wrong` among
    the options (the round itself is what a learner gets)."""
    with SessionLocal() as db:
        sess = db.get(models.PracticeSession, sid)
        qq = list(sess.questions)
        qq[0] = {**qq[0], "type": qtype, "item_id": target,
                 "option_ids": [target, wrong] + [o for o in qq[0]["option_ids"] if o not in (target, wrong)][:2]}
        sess.questions = qq
        db.commit()


@pytest.fixture
def learner(client):
    uid, h = register(client, unique_name("scene"))
    expect(client, "get", "/api/dashboard", 200, headers=h)  # skill rows
    return uid, h


def start(client, h, **body):
    return expect(client, "post", "/api/practice/sessions", 201, headers=h, json=body)


def test_every_scene_exchanges_focus_word_is_in_the_curriculum(client):
    with SessionLocal() as db:
        for scene in SCENES:
            for _tier, exchanges in scene["tiers"].items():
                for ex in exchanges:
                    assert db.query(models.VocabularyWord).filter_by(simplified=ex["focus"]).first(), (scene["slug"], ex["focus"])


def test_scenes_memory_and_sentences_require_sign_in(client):
    expect(client, "get", "/api/real-life/scenes", 401)
    expect(client, "get", "/api/companion/memory", 401)
    expect(client, "post", "/api/sentence/analyze", 401, json={"text": "我是学生。"})


def test_a_new_learners_companion_invents_no_memories(client, learner):
    _, h = learner
    mem = expect(client, "get", "/api/companion/memory", 200, headers=h)
    assert [m["kind"] for m in mem["memories"]] == ["new_learner"], mem


def test_scene_list_and_preview_are_localized_and_tiered_by_level(client, learner):
    _, h = learner
    data = expect(client, "get", "/api/real-life/scenes", 200, headers=h)
    assert data["tier"] == "beginner" and len(data["scenes"]) == 10, data
    assert all(s["exchanges"] == 3 and s["completed"] == 0 for s in data["scenes"])
    ru = expect(client, "get", "/api/real-life/scenes", 200, headers={**h, "X-Locale": "ru"})
    assert ru["scenes"][0]["title"] == "Ресторан", ru["scenes"][0]
    zh = expect(client, "get", "/api/real-life/scenes", 200, headers={**h, "X-Locale": "zh"})
    assert zh["scenes"][0]["title"] == "餐厅"
    expect(client, "get", "/api/real-life/scenes/nope", 404, headers=h)
    prev = expect(client, "get", "/api/real-life/scenes/restaurant", 200, headers=h)
    assert prev["tier"] == "beginner" and prev["new_words"], prev


def test_a_beginner_scene_is_graded_spoken_and_recorded(client, learner):
    uid, h = learner
    _, other = register(client, unique_name("otherscene"))
    s = start(client, h, source="scene", scene="restaurant")
    sid = s["id"]
    assert s["context"]["kind"] == "scene" and s["context"]["tier"] == "beginner"
    qs, _ = stored(sid)
    replies = [q for q in s["questions"] if q["type"] == "scene_reply"]
    assert len(replies) == 3 and not any(q["type"] == "scene_listen" for q in s["questions"])
    for q in replies:
        assert len(q["options"]) == 3 and q["prompt"]["text"] and q["prompt"]["pinyin"]
        assert all(o["pinyin"] for o in q["options"]), q  # beginners read pinyin on replies
        assert "item_id" not in q and q["answer"] is None
    expect(client, "post", "/api/practice/sessions", 404, headers=h, json={"source": "scene", "scene": "moon"})

    # speaking before answering is refused; the key is the stored line
    i0 = replies[0]["index"]
    expect(client, "post", f"/api/practice/sessions/{sid}/speak", 409, headers=h, json={"index": i0, "spoken_text": "两位"})
    xp0 = expect(client, "get", "/api/me", 200, headers=h)["user"]["total_xp"]
    reading0 = skill(uid, "reading")
    for q in s["questions"]:
        right = qs[q["index"]]["item_id"]
        expect(client, "post", f"/api/practice/sessions/{sid}/answer", 404, headers=other,
               json={"index": q["index"], "choice_id": right})
        r = expect(client, "post", f"/api/practice/sessions/{sid}/answer", 200, headers=h,
                   json={"index": q["index"], "choice_id": right, "response_ms": 3000})
        assert r["correct"], r
        if q["type"] == "scene_reply":
            assert r["say"] and r["card"]["meaning"], r
    # graded server-side: XP, DNA and SRS on the exchanges' real focus words
    assert expect(client, "get", "/api/me", 200, headers=h)["user"]["total_xp"] > xp0
    assert skill(uid, "reading") > reading0
    with SessionLocal() as db:
        focus_ids = [q["focus_id"] for q in qs if q.get("focus_id")]
        recs = db.query(models.UserVocabulary).filter(models.UserVocabulary.user_id == uid,
                                                      models.UserVocabulary.word_id.in_(focus_ids)).all()
        assert len(recs) == len(set(focus_ids)) and all(r.next_review_at for r in recs)

    # speaking a reply is graded against the stored line, stored as VoiceAttempts, capped
    say = expect(client, "post", f"/api/practice/sessions/{sid}/speak", 200, headers=h,
                 json={"index": i0, "spoken_text": qs[i0]["reply"]["zh"]})
    assert say["target"] == qs[i0]["reply"]["zh"] and say["scores"]["relevance"] >= 55, say
    for _ in range(2):
        expect(client, "post", f"/api/practice/sessions/{sid}/speak", 200, headers=h, json={"index": i0, "spoken_text": "你好"})
    expect(client, "post", f"/api/practice/sessions/{sid}/speak", 409, headers=h, json={"index": i0, "spoken_text": "你好"})
    with SessionLocal() as db:
        assert db.query(models.VoiceAttempt).filter_by(user_id=uid, prompt_text=qs[i0]["reply"]["zh"]).count() == 3

    # completing it logs activity and shows in the learner's scene history
    done = expect(client, "post", f"/api/practice/sessions/{sid}/complete", 200, headers=h)
    assert done["score"] == 100 and done["reaction"]["event"] == "scene_complete", done
    with SessionLocal() as db:
        assert db.query(models.ActivityEvent).filter_by(user_id=uid, action_type="real_life_scene").count() == 1
    data = expect(client, "get", "/api/real-life/scenes", 200, headers=h)
    rest = next(x for x in data["scenes"] if x["slug"] == "restaurant")
    assert rest["completed"] == 1 and rest["best_score"] == 100


def test_a_wrong_reply_is_a_supportive_reaction_and_a_reviewable_mistake(client, learner):
    uid, h = learner
    s2 = start(client, h, source="scene", scene="convenience-store")
    qs2, _ = stored(s2["id"])
    q = next(q for q in s2["questions"] if q["type"] == "scene_reply")
    wrong = next(o["id"] for o in q["options"] if o["id"] != qs2[q["index"]]["item_id"])
    r = expect(client, "post", f"/api/practice/sessions/{s2['id']}/answer", 200, headers=h,
               json={"index": q["index"], "choice_id": wrong})
    assert not r["correct"] and r["reaction"]["mood"] in ("encouraging", "worried", "serious")
    with SessionLocal() as db:
        word = db.get(models.VocabularyWord, qs2[q["index"]]["focus_id"])
        assert db.query(models.LearningMistake).filter_by(user_id=uid, reference=word.simplified).first()


def test_an_advanced_learner_gets_a_different_harder_scene(client, learner):
    _, h = learner
    beginner = start(client, h, source="scene", scene="restaurant")
    beginner_lines = {q["prompt"]["text"] for q in beginner["questions"] if q["type"] == "scene_reply"}
    aid, ah = register(client, unique_name("advanced"))
    expect(client, "get", "/api/dashboard", 200, headers=ah)
    set_skills(aid, 80.0)
    a = start(client, ah, source="scene", scene="restaurant")
    assert a["context"]["tier"] == "advanced"
    a_replies = [q for q in a["questions"] if q["type"] == "scene_reply"]
    assert len(a_replies) == 5 and all(len(q["options"]) == 4 for q in a_replies)
    assert all(q["prompt"]["text"] is None and q["options"][0]["pinyin"] is None for q in a_replies)
    # 2 listening checks at the advanced tier, +1 for a strong listener (DNA 80).
    assert sum(1 for q in a["questions"] if q["type"] == "scene_listen") == 3
    aq, _ = stored(a["id"])
    assert not beginner_lines & {q["npc"]["zh"] for q in aq if q.get("npc")}
    listen = next(q for q in a["questions"] if q["type"] == "scene_listen")
    listening0 = skill(aid, "listening")
    expect(client, "post", f"/api/practice/sessions/{a['id']}/answer", 200, headers=ah,
           json={"index": listen["index"], "choice_id": aq[listen["index"]]["item_id"]})
    assert skill(aid, "listening") > listening0
    ru_a = expect(client, "get", f"/api/practice/sessions/{a['id']}", 200, headers={**ah, "X-Locale": "ru"})
    lq = ru_a["questions"][listen["index"]]
    assert any(any("а" <= ch <= "я" for ch in o["label"].lower()) for o in lq["options"]), lq


def test_one_sentence_analysis_uses_real_words_characters_and_grammar(client, learner):
    _, h = learner
    expect(client, "post", "/api/sentence/analyze", 422, headers=h, json={"text": "hello world"})
    expect(client, "post", "/api/sentence/analyze", 422, headers=h, json={"text": "我"})
    an = expect(client, "post", "/api/sentence/analyze", 200, headers=h, json={"text": SENTENCE})
    words = [t["text"] for t in an["tokens"] if t["kind"] == "word"]
    assert "昨天" in words and "北京" in words, an["tokens"]
    assert any("了" in g["title"] for g in an["grammar"]), an["grammar"]
    assert len(an["characters"]) == 7 and an["pinyin"] and an["translation"] is None
    assert an["level"]["tier"] == "beginner"
    an_ru = expect(client, "post", "/api/sentence/analyze", 200, headers={**h, "X-Locale": "ru"}, json={"text": SENTENCE})
    assert an_ru["tokens"][0]["meaning"] != "", an_ru["tokens"][0]
    sug = expect(client, "get", "/api/sentence/suggestions", 200, headers=h)["suggestions"]
    assert sug and all(x["text"] for x in sug)


def test_a_sentence_lesson_round_feeds_review_and_activity(client, learner):
    uid, h = learner
    ss = start(client, h, source="sentence", sentence=SENTENCE)
    types = {q["type"] for q in ss["questions"]}
    assert {"sentence_listen", "sentence_order", "sentence_word"} <= types, types
    assert ss["context"]["kind"] == "sentence" and ss["context"]["text"] == SENTENCE
    expect(client, "post", "/api/practice/sessions", 422, headers=h, json={"source": "sentence", "sentence": "abc"})
    sq, _ = stored(ss["id"])
    for q in ss["questions"]:
        expect(client, "post", f"/api/practice/sessions/{ss['id']}/answer", 200, headers=h,
               json={"index": q["index"], "choice_id": sq[q["index"]]["item_id"]})
    order = next(q for q in ss["questions"] if q["type"] == "sentence_order")
    expect(client, "post", f"/api/practice/sessions/{ss['id']}/speak", 200, headers=h,
           json={"index": order["index"], "spoken_text": "我昨天去了北京"})
    fin = expect(client, "post", f"/api/practice/sessions/{ss['id']}/complete", 200, headers=h)
    assert fin["score"] == 100 and fin["reaction"]["event"] == "sentence_complete"
    with SessionLocal() as db:
        assert db.query(models.ActivityEvent).filter_by(user_id=uid, action_type="sentence_lesson").count() == 1
        drilled = {q["item_id"] for q in sq if q["item_type"] == "vocab"}
        assert drilled and db.query(models.UserVocabulary).filter(
            models.UserVocabulary.user_id == uid, models.UserVocabulary.word_id.in_(drilled)).count() == len(drilled)


def test_coming_back_after_six_days_is_remembered_and_welcomed(client, learner):
    uid, h = learner
    s = start(client, h, source="vocab", hsk_level=1, size=4)
    qs, _ = stored(s["id"])
    expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h,
           json={"index": 0, "choice_id": qs[0]["item_id"]})
    with SessionLocal() as db:
        # Everything so far happened "before": shift today's events back so a
        # 6-day gap is the latest activity before today.
        db.add(models.ActivityEvent(user_id=uid, section="practice", action_type="practice_answer", minutes=0.4,
                                    created_at=datetime.utcnow() - timedelta(days=6)))
        for ev in db.query(models.ActivityEvent).filter(models.ActivityEvent.user_id == uid,
                                                       models.ActivityEvent.created_at >= datetime.utcnow() - timedelta(hours=23)):
            ev.created_at = datetime.utcnow() - timedelta(days=6, hours=1)
        db.commit()
    mem = expect(client, "get", "/api/companion/memory", 200, headers=h)
    assert mem["headline"]["kind"] == "welcome_back" and mem["headline"]["data"]["days"] == 6, mem["headline"]
    again = start(client, h, source="vocab", hsk_level=1, size=4)
    assert again["reaction"]["cause"] == "welcome_back", again["reaction"]


@pytest.fixture
def confused(client, learner):
    """A learner who twice picked the same wrong word for the same target."""
    cid, ch = learner
    causes = []
    for attempt in range(2):
        cs = start(client, ch, source="vocab", hsk_level=1, size=4)
        cq, _ = stored(cs["id"])
        if attempt == 0:
            target, wrong = cq[0]["item_id"], next(o for o in cq[0]["option_ids"] if o != cq[0]["item_id"])
            qtype = cq[0]["type"]
        pin_first_question(cs["id"], qtype, target, wrong)
        r = expect(client, "post", f"/api/practice/sessions/{cs['id']}/answer", 200, headers=ch,
                   json={"index": 0, "choice_id": wrong})
        causes.append(r["reaction"]["cause"])
    return cid, ch, target, wrong, qtype, causes


def test_the_companion_recognizes_a_confusion_really_made_before(confused):
    causes = confused[-1]
    assert causes[0] != "confused_pair" and causes[1] == "confused_pair", causes


def test_mastering_a_repeatedly_missed_word_is_celebrated_and_remembered(client, confused):
    cid, ch, target, wrong, qtype, _ = confused
    with SessionLocal() as db:
        rec = db.query(models.UserVocabulary).filter_by(user_id=cid, word_id=target).first()
        rec.mastery, rec.times_missed, rec.status = 80.0, 3, "reviewing"
        db.commit()
    ms = start(client, ch, source="vocab", hsk_level=1, size=4)
    pin_first_question(ms["id"], qtype, target, wrong)
    r = expect(client, "post", f"/api/practice/sessions/{ms['id']}/answer", 200, headers=ch,
               json={"index": 0, "choice_id": target})
    assert r["reaction"]["cause"] == "mastered_hard", r["reaction"]
    mem = expect(client, "get", "/api/companion/memory", 200, headers=ch)
    kinds = [m["kind"] for m in mem["memories"]]
    assert "mastered_hard" in kinds and "new_learner" not in kinds, kinds
    ru = expect(client, "get", "/api/companion/memory", 200, headers={**ch, "X-Locale": "ru"})
    assert all(m["zh"] for m in ru["memories"]) and ru["companion"] is None  # no companion chosen yet
