"""Real Chinese scenes, One Sentence lessons, and the companion's learning
memory -- end to end on a fresh database."""

import os
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/real_life.db"
os.environ["AI_PROVIDER"] = "offline"

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services.real_life_content import SCENES  # noqa: E402


def expect(client, method, url, expected, **kwargs):
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == expected, f"{method.upper()} {url} -> {resp.status_code} (expected {expected}): {resp.text}"
    return resp.json() if resp.content else None


def register(client, name):
    data = expect(client, "post", "/api/auth/register", 201,
                  json={"username": name, "email": f"{name}@example.com", "password": "secret1"})
    return data["user"]["id"], {"Authorization": f"Bearer {data['access_token']}"}


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


with TestClient(app) as client:
    # --- content: every scene's focus words are real curriculum rows
    with SessionLocal() as db:
        for scene in SCENES:
            for tier, exchanges in scene["tiers"].items():
                for ex in exchanges:
                    assert db.query(models.VocabularyWord).filter_by(simplified=ex["focus"]).first(), (scene["slug"], ex["focus"])
    print("[PASS] every scene exchange's focus word exists in the curriculum")

    uid, h = register(client, "scenelearner")
    _, other = register(client, "otherscene")
    expect(client, "get", "/api/real-life/scenes", 401)
    expect(client, "get", "/api/companion/memory", 401)
    expect(client, "post", "/api/sentence/analyze", 401, json={"text": "我是学生。"})

    # --- empty/new user: memory has a real "new learner" state, nothing invented
    mem = expect(client, "get", "/api/companion/memory", 200, headers=h)
    assert [m["kind"] for m in mem["memories"]] == ["new_learner"], mem
    print("[PASS] a brand-new learner's companion invents no memories")

    # --- scene list at the learner's real level (new learner -> beginner)
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
    print("[PASS] scene list/preview localized and tiered from the learner's level")

    # --- play a beginner scene
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "scene", "scene": "restaurant"})
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
    print("[PASS] beginner scene: 3 exchanges, 3 replies with pinyin, no answer key sent")

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
    assert expect(client, "get", "/api/me", 200, headers=h)["user"]["total_xp"] > xp0
    assert skill(uid, "reading") > reading0
    with SessionLocal() as db:
        focus_ids = [q["focus_id"] for q in qs if q.get("focus_id")]
        recs = db.query(models.UserVocabulary).filter(models.UserVocabulary.user_id == uid,
                                                      models.UserVocabulary.word_id.in_(focus_ids)).all()
        assert len(recs) == len(set(focus_ids)) and all(r.next_review_at for r in recs)
    print("[PASS] scene answers graded server-side: XP, DNA and SRS on the exchanges' real focus words")

    say = expect(client, "post", f"/api/practice/sessions/{sid}/speak", 200, headers=h,
                 json={"index": i0, "spoken_text": qs[i0]["reply"]["zh"]})
    assert say["target"] == qs[i0]["reply"]["zh"] and say["scores"]["relevance"] >= 55, say
    for _ in range(2):
        expect(client, "post", f"/api/practice/sessions/{sid}/speak", 200, headers=h, json={"index": i0, "spoken_text": "你好"})
    expect(client, "post", f"/api/practice/sessions/{sid}/speak", 409, headers=h, json={"index": i0, "spoken_text": "你好"})
    with SessionLocal() as db:
        assert db.query(models.VoiceAttempt).filter_by(user_id=uid, prompt_text=qs[i0]["reply"]["zh"]).count() == 3
    print("[PASS] speaking a reply is graded against the stored line, stored as VoiceAttempts, capped")

    done = expect(client, "post", f"/api/practice/sessions/{sid}/complete", 200, headers=h)
    assert done["score"] == 100 and done["reaction"]["event"] == "scene_complete", done
    with SessionLocal() as db:
        assert db.query(models.ActivityEvent).filter_by(user_id=uid, action_type="real_life_scene").count() == 1
    data = expect(client, "get", "/api/real-life/scenes", 200, headers=h)
    rest = next(x for x in data["scenes"] if x["slug"] == "restaurant")
    assert rest["completed"] == 1 and rest["best_score"] == 100
    print("[PASS] completing a scene logs activity and shows in the learner's scene history")

    # --- a wrong reply is a mistake on the focus word (Review brings it back)
    s2 = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "scene", "scene": "convenience-store"})
    qs2, _ = stored(s2["id"])
    q = next(q for q in s2["questions"] if q["type"] == "scene_reply")
    wrong = next(o["id"] for o in q["options"] if o["id"] != qs2[q["index"]]["item_id"])
    r = expect(client, "post", f"/api/practice/sessions/{s2['id']}/answer", 200, headers=h,
               json={"index": q["index"], "choice_id": wrong})
    assert not r["correct"] and r["reaction"]["mood"] in ("encouraging", "worried", "serious")
    with SessionLocal() as db:
        word = db.get(models.VocabularyWord, qs2[q["index"]]["focus_id"])
        assert db.query(models.LearningMistake).filter_by(user_id=uid, reference=word.simplified).first()
    print("[PASS] a wrong reply records a supportive reaction and a reviewable mistake")

    # --- an advanced learner gets a different, harder scene
    aid, ah = register(client, "advancedlearner")
    expect(client, "get", "/api/dashboard", 200, headers=ah)
    set_skills(aid, 80.0)
    a = expect(client, "post", "/api/practice/sessions", 201, headers=ah, json={"source": "scene", "scene": "restaurant"})
    assert a["context"]["tier"] == "advanced"
    a_replies = [q for q in a["questions"] if q["type"] == "scene_reply"]
    assert len(a_replies) == 5 and all(len(q["options"]) == 4 for q in a_replies)
    assert all(q["prompt"]["text"] is None and q["options"][0]["pinyin"] is None for q in a_replies)
    # 2 listening checks at the advanced tier, +1 for a strong listener (DNA 80).
    assert sum(1 for q in a["questions"] if q["type"] == "scene_listen") == 3
    beginner_lines = {q["prompt"]["text"] for q in replies}
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
    print("[PASS] advanced learner: 5 exchanges, 4 replies, audio-first lines, 2 listening checks (localized)")

    # --- One Sentence -> lesson
    expect(client, "post", "/api/sentence/analyze", 422, headers=h, json={"text": "hello world"})
    expect(client, "post", "/api/sentence/analyze", 422, headers=h, json={"text": "我"})
    an = expect(client, "post", "/api/sentence/analyze", 200, headers=h, json={"text": "我昨天去了北京。"})
    words = [t["text"] for t in an["tokens"] if t["kind"] == "word"]
    assert "昨天" in words and "北京" in words, an["tokens"]
    assert any("了" in g["title"] for g in an["grammar"]), an["grammar"]
    assert len(an["characters"]) == 7 and an["pinyin"] and an["translation"] is None
    assert an["level"]["tier"] == "beginner"
    an_ru = expect(client, "post", "/api/sentence/analyze", 200, headers={**h, "X-Locale": "ru"}, json={"text": "我昨天去了北京。"})
    assert an_ru["tokens"][0]["meaning"] != "", an_ru["tokens"][0]
    sug = expect(client, "get", "/api/sentence/suggestions", 200, headers=h)["suggestions"]
    assert sug and all(x["text"] for x in sug)
    print("[PASS] sentence analysis: real words, characters, grammar, pinyin; suggestions are real examples")

    ss = expect(client, "post", "/api/practice/sessions", 201, headers=h,
                json={"source": "sentence", "sentence": "我昨天去了北京。"})
    types = {q["type"] for q in ss["questions"]}
    assert {"sentence_listen", "sentence_order", "sentence_word"} <= types, types
    assert ss["context"]["kind"] == "sentence" and ss["context"]["text"] == "我昨天去了北京。"
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
    print("[PASS] sentence lesson round: listening, word order, comprehension, speaking -> SRS + activity")

    # --- companion memory from real events
    with SessionLocal() as db:
        db.add(models.ActivityEvent(user_id=uid, section="practice", action_type="practice_answer", minutes=0.4,
                                    created_at=datetime.utcnow() - timedelta(days=6)))
        # Everything else today happened "before": shift today's events back
        # so the 6-day gap is the latest activity before today.
        for ev in db.query(models.ActivityEvent).filter(models.ActivityEvent.user_id == uid,
                                                       models.ActivityEvent.created_at >= datetime.utcnow() - timedelta(hours=23)):
            ev.created_at = datetime.utcnow() - timedelta(days=6, hours=1)
        db.commit()
    mem = expect(client, "get", "/api/companion/memory", 200, headers=h)
    kinds = [m["kind"] for m in mem["memories"]]
    assert mem["headline"]["kind"] == "welcome_back" and mem["headline"]["data"]["days"] == 6, mem["headline"]
    start = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "vocab", "hsk_level": 1, "size": 4})
    assert start["reaction"]["cause"] == "welcome_back", start["reaction"]
    print("[PASS] coming back after 6 days: welcome-back memory and a welcoming start reaction")

    # confusion pair: pick the same wrong word for the same target twice
    cid, ch = register(client, "confuser")
    expect(client, "get", "/api/dashboard", 200, headers=ch)
    causes = []
    for attempt in range(2):
        cs = expect(client, "post", "/api/practice/sessions", 201, headers=ch, json={"source": "vocab", "hsk_level": 1, "size": 4})
        cq, _ = stored(cs["id"])
        if attempt == 0:
            target, wrong = cq[0]["item_id"], next(o for o in cq[0]["option_ids"] if o != cq[0]["item_id"])
            qtype = cq[0]["type"]
        with SessionLocal() as db:
            sess = db.get(models.PracticeSession, cs["id"])
            qq = list(sess.questions)
            qq[0] = {**qq[0], "type": qtype, "item_id": target,
                     "option_ids": [target, wrong] + [o for o in qq[0]["option_ids"] if o not in (target, wrong)][:2]}
            sess.questions = qq
            db.commit()
        r = expect(client, "post", f"/api/practice/sessions/{cs['id']}/answer", 200, headers=ch,
                   json={"index": 0, "choice_id": wrong})
        causes.append(r["reaction"]["cause"])
    assert causes[0] != "confused_pair" and causes[1] == "confused_pair", causes
    print("[PASS] the companion recognizes a confusion the learner has really made before")

    # mastering a word that was missed repeatedly is celebrated
    with SessionLocal() as db:
        rec = db.query(models.UserVocabulary).filter_by(user_id=cid, word_id=target).first()
        rec.mastery, rec.times_missed, rec.status = 80.0, 3, "reviewing"
        db.commit()
    ms = expect(client, "post", "/api/practice/sessions", 201, headers=ch, json={"source": "vocab", "hsk_level": 1, "size": 4})
    mq, _ = stored(ms["id"])
    idx = next((i for i, q in enumerate(mq) if q["item_id"] == target), None)
    if idx is not None:
        r = expect(client, "post", f"/api/practice/sessions/{ms['id']}/answer", 200, headers=ch,
                   json={"index": idx, "choice_id": target})
        assert r["reaction"]["cause"] == "mastered_hard", r["reaction"]
        mem = expect(client, "get", "/api/companion/memory", 200, headers=ch)
        kinds = [m["kind"] for m in mem["memories"]]
        assert "mastered_hard" in kinds and "new_learner" not in kinds, kinds
        print("[PASS] mastering a hard word: celebrating reaction + remembered in companion memory")
    else:
        print("[SKIP] hard word not in the round (prioritization) -- covered by companion_reaction unit path")

    mem = expect(client, "get", "/api/companion/memory", 200, headers={**ch, "X-Locale": "ru"})
    assert all(m["zh"] for m in mem["memories"]) and mem["companion"] is None  # no companion chosen yet
    print("ALL REAL-LIFE / SENTENCE / MEMORY TESTS PASSED")
