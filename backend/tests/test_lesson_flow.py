"""A lesson as a guided sequence (services/lesson_flow.py): the lesson's own
phrases with their translations, server-graded steps (listen, build, recall,
apply) whose answers are honest and whose wrong answers say what differed,
records read back from the learner's rounds, the lesson completed only by
its own check, and the help adapted to the learner's level."""

import random

import pytest

from app import models
from app.database import SessionLocal
from app.services import lesson_flow as lf
from helpers import expect, register, unique_name

ROUNDS = "/api/practice/sessions"


def lesson_id(title):
    with SessionLocal() as db:
        return db.query(models.Lesson).filter_by(title=title).first().id


def stored(sid):
    with SessionLocal() as db:
        return db.get(models.PracticeSession, sid).questions


def learner(client, level=None):
    uid, h = register(client, unique_name("lf"))
    expect(client, "get", "/api/journey", 200, headers=h)  # creates the skill rows
    if level:
        with SessionLocal() as db:
            for s in db.get(models.User, uid).user_skills:
                s.mastery = level * 15 - 0.5
            db.commit()
    return uid, {**h, "X-Locale": "tg"}


def step(client, h, lid, name):
    return expect(client, "post", ROUNDS, 201, headers=h, json={"source": "lesson_step", "lesson_id": lid, "step": name})


def answer(client, h, s, q, right=True):
    k = stored(s["id"])[q["index"]]
    if k["type"] == "phrase_build":
        order = k["answer_order"] if right else list(reversed(k["answer_order"]))
        body = {"index": q["index"], "order": order}
    elif k["type"] == "type_word":
        with SessionLocal() as db:
            word = db.get(models.VocabularyWord, k["item_id"]).simplified
        body = {"index": q["index"], "text": word if right else ""}
    else:
        body = {"index": q["index"], "choice_id": k["item_id"] if right else next(o for o in k["option_ids"] if o != k["item_id"])}
    return expect(client, "post", f"{ROUNDS}/{s['id']}/answer", 200, headers=h, json={**body, "response_ms": 2500})


# --------------------------------------------------------------------------- reading the lesson

def test_entries_are_read_with_their_pinyin_meaning_and_reply():
    text = ("你好 (nǐ hǎo) = hello.\n你好吗？(nǐ hǎo ma?) = How are you? — Answer: 我很好，谢谢。\n"
            "米饭 mǐfàn = rice, 茶 chá = tea,\n我吃了饭。 = I ate (the food). 他来了。 = He came.")
    got = [(e["zh"], e["py"], e["gloss"], e["reply"]) for e in lf.parse_entries(text)]
    assert got == [("你好", "nǐ hǎo", "hello", None), ("你好吗？", "nǐ hǎo ma?", "How are you?", "我很好，谢谢。"),
                   ("米饭", "mǐfàn", "rice", None), ("茶", "chá", "tea", None),
                   ("我吃了饭。", None, "I ate (the food)", None), ("他来了。", None, "He came", None)]


def test_the_flow_teaches_the_lessons_own_phrases_in_tajik(client):
    _, h = learner(client)
    lid = lesson_id("Greetings")
    f = expect(client, "get", f"/api/lessons/{lid}/flow", 200, headers=h)
    by_zh = {p["zh"]: p for p in f["phrases"]}
    assert by_zh["你好"]["meaning"] == "салом" and by_zh["你好"]["pinyin"] == "nǐ hǎo"
    assert by_zh["你好吗？"]["reply"] == "我很好，谢谢。"
    assert [w["text"] for w in by_zh["早上好"]["words"]] == ["早上", "好"]
    assert all(w["meaning"] for w in by_zh["早上好"]["words"])
    assert f["words"] and f["hints"] == "full" and f["pinyin_first"] is True and f["known_level"] is False
    assert [s["key"] for s in f["stages"]] == list(lf.STAGES) and all(s["available"] for s in f["stages"])
    assert f["check"] == {"status": "not_started", "score": None, "practicable": True}
    # The zh "translation" of a line repeats the Chinese: no meaning is claimed, English is used.
    zh = expect(client, "get", f"/api/lessons/{lid}/flow", 200, headers={**h, "X-Locale": "zh"})
    assert {p["zh"]: p["meaning"] for p in zh["phrases"]}["你好"] == "hello"


def test_a_locked_lesson_has_no_flow_and_no_steps(client):
    _, h = learner(client)
    lid = lesson_id("Introduce yourself")
    assert expect(client, "get", f"/api/lessons/{lid}/flow", 403, headers=h)["code"] == "lesson_locked"
    assert client.post(ROUNDS, headers=h, json={"source": "lesson_step", "lesson_id": lid, "step": "listen"}).status_code == 403
    expect(client, "post", ROUNDS, 422, headers=h, json={"source": "lesson_step", "lesson_id": lesson_id("Greetings"), "step": "sing"})


# --------------------------------------------------------------------------- the steps

@pytest.mark.parametrize("name", lf.STAGES)
def test_every_step_is_honest_and_sends_no_answer(client, name):
    _, h = learner(client)
    s = step(client, h, lesson_id("Greetings"), name)
    assert s["context"]["kind"] == "lesson_step" and s["context"]["stage"] == name
    keys = stored(s["id"])
    for q, k in zip(s["questions"], keys):
        assert "item_id" not in q and "answer_order" not in q
        if k["type"] == "phrase_build":
            pieces = [x["zh"] for x in k["pieces"]]
            assert "".join(pieces[i] for i in k["answer_order"]) == k["phrase"]["zh"]
            assert [x["zh"] for x in q["prompt"]["pieces"]] == pieces, "shown shuffled, as stored"
        elif k["item_type"] == "phrase":
            right = k["options"][k["item_id"]]
            if k["type"] in ("phrase_listen", "phrase_meaning", "phrase_situation"):
                assert right["zh"] == k["phrase"]["zh"]
            if k["type"] == "phrase_listen" and k["by"] == "meaning":
                # Heard, answered by meaning: no Chinese option to read off.
                assert all(not any("一" <= c <= "鿿" for c in o["label"]) for o in q["options"])
            if k["type"] == "phrase_gap":
                assert q["prompt"]["text"].replace("＿＿", right["zh"]) == k["phrase"]["zh"]
        if k["type"] == "char_to_pinyin":
            assert q["prompt"]["speak"] == q["prompt"]["text"], "tones are heard"


def test_building_a_phrase_is_graded_on_the_server(client):
    uid, h = learner(client)
    s = step(client, h, lesson_id("Greetings"), "build")
    build = next(q for q in s["questions"] if q["type"] == "phrase_build")
    k = stored(s["id"])[build["index"]]
    n = len(k["pieces"])
    # Not every piece once: refused, nothing stored.
    expect(client, "post", f"{ROUNDS}/{s['id']}/answer", 422, headers=h, json={"index": build["index"], "order": [0] * n})
    expect(client, "post", f"{ROUNDS}/{s['id']}/answer", 422, headers=h, json={"index": build["index"], "choice_id": 0})
    r = answer(client, h, s, build, right=False)
    assert not r["correct"]
    c = r["check"]
    assert c["kind"] == "order" and c["expected"] == k["phrase"]["zh"] and c["given"] != c["expected"]
    with SessionLocal() as db:
        assert db.get(models.PracticeSession, s["id"]).answers[build["index"]]["order"]


def test_a_right_build_is_right_and_moves_the_word(client):
    uid, h = learner(client)
    s = step(client, h, lesson_id("Greetings"), "build")
    build = next(q for q in s["questions"] if q["type"] == "phrase_build")
    k = stored(s["id"])[build["index"]]
    r = answer(client, h, s, build)
    assert r["correct"] and r["card"]["hanzi"] == k["phrase"]["zh"]
    with SessionLocal() as db:
        rec = db.query(models.UserVocabulary).filter_by(user_id=uid, word_id=k["focus_id"]).first()
        assert rec is not None and rec.mastery > 0


def test_a_wrong_word_names_both_meanings_and_goes_to_the_notebook(client):
    uid, h = learner(client)
    s = step(client, h, lesson_id("Greetings"), "build")
    gap = next(q for q in s["questions"] if q["type"] == "phrase_gap")
    k = stored(s["id"])[gap["index"]]
    r = answer(client, h, s, gap, right=False)
    c = r["check"]
    assert c["kind"] == "gap" and c["answer"] == k["options"][k["item_id"]]["zh"]
    assert c["picked_meaning"] and c["answer_meaning"] and c["picked"] != c["answer"]
    with SessionLocal() as db:
        word = db.get(models.VocabularyWord, k["focus_id"]).simplified
        assert db.query(models.LearningMistake).filter_by(user_id=uid, reference=word).count() == 1


def test_a_reply_and_a_situation_come_from_the_lesson(client):
    _, h = learner(client)
    s = step(client, h, lesson_id("Greetings"), "apply")
    keys = stored(s["id"])
    reply = next(k for k in keys if k["type"] == "phrase_reply")
    assert reply["phrase"]["zh"] == "你好吗？" and reply["options"][reply["item_id"]]["zh"] == "我很好，谢谢。"
    q = next(q for q in s["questions"] if q["type"] == "phrase_reply")
    r = answer(client, h, s, q, right=False)
    assert r["check"]["kind"] == "reply" and r["check"]["asked"] == "你好吗？" and r["check"]["answer"] == "我很好，谢谢。"
    assert any(k["type"] == "phrase_build" and k.get("final") for k in keys), "ends with an independent task"
    final = next(q for q in s["questions"] if q["type"] == "phrase_build" and q["prompt"]["final"])
    assert all(p["py"] is None and p["meaning"] is None for p in final["prompt"]["pieces"]), "no hints"


def test_a_step_is_recorded_but_never_completes_the_lesson(client):
    uid, h = learner(client)
    lid = lesson_id("Greetings")
    s = step(client, h, lid, "recall")
    for q in s["questions"]:
        answer(client, h, s, q)
    summary = expect(client, "post", f"{ROUNDS}/{s['id']}/complete", 200, headers=h)
    assert summary["score"] == 100.0 and summary["lesson_status"] is None
    f = expect(client, "get", f"/api/lessons/{lid}/flow", 200, headers=h)
    recall = next(x for x in f["stages"] if x["key"] == "recall")
    assert recall == {"key": "recall", "available": True, "played": 1, "best": 100.0, "done": True}
    assert f["check"]["status"] == "not_started"
    with SessionLocal() as db:
        assert db.query(models.Progress).filter_by(user_id=uid, lesson_id=lid).first() is None
        assert db.query(models.ActivityEvent).filter_by(user_id=uid, action_type="lesson_step").count() == 1


# --------------------------------------------------------------------------- the learner's level

def test_the_help_follows_the_learners_level(client):
    assert (lf.hints_for(1), lf.hints_for(2), lf.hints_for(3), lf.hints_for(6)) == ("full", "some", "none", "none")
    _, h = learner(client, level=3)
    lid = lesson_id("Greetings")
    f = expect(client, "get", f"/api/lessons/{lid}/flow", 200, headers=h)
    assert f["hints"] == "none" and f["known_level"] is True and f["pinyin_first"] is False
    s = step(client, h, lid, "build")
    builds = [q for q in s["questions"] if q["type"] == "phrase_build"]
    # The first build gets one level more help ("some": meanings, no pinyin); then none.
    assert builds[0]["prompt"]["hints"] == "some"
    assert all(p["py"] is None for b in builds for p in b["prompt"]["pieces"])


# --------------------------------------------------------------------------- feedback rules

@pytest.mark.parametrize("expected,given,rule", [
    (["你好", "吗？"], ["吗？", "你好"], "particle_end"),
    (["我", "是", "学生。"], ["是", "我", "学生。"], "subject_first"),
    (["我", "不", "去。"], ["我", "去。", "不"], "bu_before"),
    (["我", "很", "好"], ["我", "好", "很"], "hen_before"),
    (["我", "明天", "去。"], ["我", "去。", "明天"], "time_early"),
    (["我", "的", "书"], ["的", "我", "书"], "de_between"),
    (["我", "吃", "了", "饭。"], ["我", "了", "吃", "饭。"], "le_after"),
    (["学生", "很", "多"], ["很", "学生", "多"], "hen_before"),
    (["一", "碗", "面"], ["碗", "一", "面"], None),  # no rule the orders show: none is claimed
])
def test_a_word_order_rule_is_named_only_when_the_orders_show_it(expected, given, rule):
    assert lf._order_rule(expected, given)[0] == rule


def test_polyphones_never_get_a_guessed_reading(client):
    with SessionLocal() as db:
        from app.services import sentence as sent

        toks = sent.segment(db, "我得走了。")
        assert lf._derived_pinyin(toks) is None
        assert lf._derived_pinyin(sent.segment(db, "我是学生。")) is not None


def test_the_food_lesson_says_noodles_in_tajik(client):
    _, h = learner(client)
    with SessionLocal() as db:
        rows = db.query(models.ContentTranslation).filter_by(locale="tg").all()
        assert not any("решаи гӯшти" in (r.text or "") or "реша бо гӯшти" in (r.text or "") for r in rows)
        word = db.query(models.VocabularyWord).filter_by(simplified="牛肉面").first()
        tg = db.query(models.ContentTranslation).filter_by(content_type="vocab_word", content_key=str(word.id),
                                                           field="meanings", locale="tg").first()
        assert tg.text == "угрои гӯшти гов"


# --------------------------------------------------------------------------- the lesson played through

def play(client, h, lid):
    return expect(client, "post", ROUNDS, 201, headers=h, json={"source": "lesson_play", "lesson_id": lid})


def finish(client, h, s, right=True, skip_teach=False):
    for q in s["questions"]:
        if q["type"] == "teach":
            if not skip_teach:
                expect(client, "post", f"{ROUNDS}/{s['id']}/answer", 200, headers=h, json={"index": q["index"], "choice_id": 0})
            continue
        answer(client, h, s, q, right=right)
    return expect(client, "post", f"{ROUNDS}/{s['id']}/complete", 200, headers=h)


def test_a_played_lesson_teaches_each_phrase_then_practises_it(client):
    _, h = learner(client)
    s = play(client, h, lesson_id("Greetings"))
    keys = stored(s["id"])
    types = [k["type"] for k in keys]
    assert types[0] == "teach" and s["context"]["kind"] == "lesson_play"
    taught = []
    for i, k in enumerate(keys):
        if k["type"] != "teach":
            continue
        taught.append(k["phrase"]["zh"])
        # Practised at once: the next screen is about what was just taught.
        nxt = keys[i + 1]
        assert nxt["type"] != "teach"
        if nxt["item_type"] == "phrase" and k["kind"] == "phrase":
            assert nxt["phrase"]["zh"] == k["phrase"]["zh"]
    # A taught phrase comes back later (recycled), and the lesson ends with a no-help build.
    later = [k["phrase"]["zh"] for k in keys if k["type"] == "phrase_meaning"]
    assert later and all(z in taught for z in later)
    assert keys[-1]["type"] == "phrase_build" and keys[-1]["final"]
    assert sum(1 for t in types if t != "teach") >= lf.PLAY_MIN_GRADED
    # The teaching screen as the browser sees it: the phrase, pinyin, Tajik meaning, its words.
    teach = s["questions"][0]["prompt"]
    assert teach["kind"] == "teach" and teach["zh"] == "你好" and teach["meaning"] == "салом" and teach["pinyin"] == "nǐ hǎo"
    assert [w["text"] for w in teach["words"]] == ["你", "好"] and all(w["meaning"] for w in teach["words"])
    assert s["questions"][0]["options"] == []


def test_a_teaching_screen_is_seen_not_graded(client):
    uid, h = learner(client)
    s = play(client, h, lesson_id("Greetings"))
    expect(client, "post", f"{ROUNDS}/{s['id']}/answer", 422, headers=h, json={"index": 0, "choice_id": 1})
    r = expect(client, "post", f"{ROUNDS}/{s['id']}/answer", 200, headers=h, json={"index": 0, "choice_id": 0})
    assert r["seen"] and r["xp_gained"] == 0
    with SessionLocal() as db:
        assert db.query(models.UserVocabulary).filter_by(user_id=uid).count() == 0, "reading is not knowing"
        assert db.get(models.User, uid).total_xp == 0
    # Reading every teaching screen and answering nothing completes nothing.
    expect(client, "post", f"{ROUNDS}/{s['id']}/complete", 422, headers=h)


def test_passing_the_played_lesson_completes_it_and_opens_the_next(client):
    uid, h = learner(client)
    lid = lesson_id("Greetings")
    s = play(client, h, lid)
    summary = finish(client, h, s)
    assert summary["score"] == 100.0 and summary["lesson_status"] == "completed"
    assert summary["total"] == sum(1 for q in s["questions"] if q["type"] != "teach")
    nxt = summary["next_lesson_id"]
    assert nxt and nxt != lid
    p = expect(client, "get", "/api/lessons/path", 200, headers=h)
    assert p["current_lesson_id"] == nxt
    f = expect(client, "get", f"/api/lessons/{lid}/flow", 200, headers=h)
    assert f["check"]["status"] == "completed" and f["play"]["played"] == 1 and f["play"]["best"] == 100.0
    with SessionLocal() as db:
        assert db.get(models.User, uid).total_xp > 0
        assert db.query(models.ActivityEvent).filter_by(user_id=uid, action_type="lesson_complete").count() == 1


def test_a_learner_who_makes_mistakes_is_not_passed_and_meets_them_in_review(client):
    uid, h = learner(client)
    lid = lesson_id("Greetings")
    s = play(client, h, lid)
    summary = finish(client, h, s, right=False)
    assert summary["score"] == 0.0 and summary["lesson_status"] != "completed" and summary["next_lesson_id"] is None
    assert summary["missed"], "what was missed is listed"
    with SessionLocal() as db:
        assert db.query(models.LearningMistake).filter_by(user_id=uid).count() >= 3
        prog = db.query(models.Progress).filter_by(user_id=uid, lesson_id=lid).first()
        assert prog is None or prog.status != "completed"
    review = expect(client, "get", "/api/practice/review/summary", 200, headers=h)
    assert review["mistakes"] >= 1


def test_a_locked_lesson_cannot_be_played(client):
    _, h = learner(client)
    assert client.post(ROUNDS, headers=h, json={"source": "lesson_play", "lesson_id": lesson_id("Introduce yourself")}).status_code == 403


def test_the_start_screen_offers_the_played_lesson(client):
    _, h = learner(client)
    f = expect(client, "get", f"/api/lessons/{lesson_id('Greetings')}/flow", 200, headers=h)
    assert f["play"]["available"] and f["play"]["taught"] >= 3 and f["play"]["played"] == 0 and f["play"]["best"] is None
    assert f["play"]["screens"] > f["play"]["taught"]


def test_an_hsk3_learner_is_offered_the_test_and_gets_fewer_hints(client):
    uid, h = learner(client, level=3)
    lid = lesson_id("Greetings")
    f = expect(client, "get", f"/api/lessons/{lid}/flow", 200, headers=h)
    assert f["known_level"] and f["hints"] == "none"
    s = play(client, h, lid)
    builds = [q for q in s["questions"] if q["type"] == "phrase_build"]
    assert builds and all(p["py"] is None for b in builds for p in b["prompt"]["pieces"])
    # The lesson's test completes it directly when passed (no shortcut: graded on the server).
    t = expect(client, "post", ROUNDS, 201, headers=h, json={"source": "lesson", "lesson_id": lid})
    for q in t["questions"]:
        answer(client, h, t, q)
    assert expect(client, "post", f"{ROUNDS}/{t['id']}/complete", 200, headers=h)["lesson_status"] == "completed"
