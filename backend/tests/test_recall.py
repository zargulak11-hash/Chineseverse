"""Active recall (services/recall.py): a word or character the learner
already recognises is asked from memory, the typed answer is graded exactly
and the reason for a wrong one is named only when the text shows it, and
"mastered" needs a recall -- picking an option or pressing "I know it" is
no longer enough (services/srs.py)."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app import models
from app.database import SessionLocal
from app.services import recall
from app.services.srs import apply_srs
from helpers import expect, register, unique_name

ROUNDS = "/api/practice/sessions"


# --------------------------------------------------------------------------- the checker

def w(i, simplified, pinyin, meanings, traditional=None):
    return SimpleNamespace(id=i, simplified=simplified, traditional=traditional, pinyin=pinyin, meanings=meanings)


@pytest.mark.parametrize("typed", ["nǐhǎo", "ni3 hao3", "Ni3Hao3", "nǐ hǎo", "ni3hao3 "])
def test_pinyin_with_marks_or_digits_is_the_same_answer(typed):
    assert recall.check_pinyin(typed, "nǐ hǎo")["kind"] == "exact"


def test_neutral_tones_need_no_mark_and_may_be_written_5():
    for typed in ("ma1ma", "ma1ma5", "māma", "ma1ma0"):
        assert recall.check_pinyin(typed, "māma")["correct"], typed
    assert recall.check_pinyin("lv4", "lǜ")["correct"] and recall.check_pinyin("lu:4", "lǜ")["correct"]


def test_wrong_tones_are_named_with_both_tone_sequences():
    r = recall.check_pinyin("ni2 hao3", "nǐ hǎo")
    assert r == {"kind": "tone", "correct": False, "tones_typed": "2-3", "tones_expected": "3-3"}


def test_no_tones_at_all_is_not_a_tone_mistake_but_missing_tones():
    assert recall.check_pinyin("nihao", "nǐ hǎo")["kind"] == "missing_tones"
    assert recall.check_pinyin("ni hao", "nǐ hǎo")["correct"] is False


def test_other_syllables_or_nothing_typed():
    assert recall.check_pinyin("ni3 men", "nǐ hǎo")["kind"] == "wrong"
    assert recall.check_pinyin("  ", "nǐ hǎo")["kind"] == "unknown"


def test_a_typed_word_is_exact_a_synonym_or_another_word():
    like = w(1, "喜欢", "xǐhuan", "to like; to be fond of")
    love = w(2, "爱", "ài", "to love; to be fond of")
    eat = w(3, "吃", "chī", "to eat")
    words = [like, love, eat]
    assert recall.check_word("喜欢", like, words)["kind"] == "exact"
    assert recall.check_word("xi3huan", like, words)["kind"] == "exact"
    alt = recall.check_word("爱", like, words)
    assert alt["kind"] == "alternative" and alt["correct"] and alt["other"] is love
    other = recall.check_word("chi1", like, words)
    assert other["kind"] == "other_word" and not other["correct"] and other["other"] is eat
    assert recall.check_word("xi2huan", like, words)["kind"] == "tone"
    assert recall.check_word("飞机", like, words)["kind"] == "wrong"
    assert recall.check_word("", like, words)["kind"] == "unknown"


def test_pinyin_shared_by_several_words_names_no_word():
    he, she = w(1, "他", "tā", "he, him"), w(2, "她", "tā", "she, her")
    eat = w(3, "吃", "chī", "to eat")
    # Typed "ta1" for 吃: two words read tā, so which one was meant is unknown.
    assert recall.check_word("ta1", eat, [he, she, eat]) == {"kind": "wrong", "correct": False}


# --------------------------------------------------------------------------- mastery needs recall

def rec(mastery=80.0, status="reviewing", recalled=0):
    return SimpleNamespace(mastery=mastery, times_seen=5, times_missed=0, times_recalled=recalled, status=status,
                           next_review_at=None, last_reviewed_at=None)


def test_recognition_alone_never_masters_a_word():
    r = rec()
    for _ in range(5):
        apply_srs(r, True, SimpleNamespace(animal=None))
    assert r.mastery == 100.0 and r.status == "reviewing" and r.times_recalled == 0


def test_one_recall_lets_mastery_count():
    r = rec()
    apply_srs(r, True, SimpleNamespace(animal=None), recall=True)
    assert r.status == "mastered" and r.times_recalled == 1
    # A wrong recall is not a recall.
    r2 = rec()
    apply_srs(r2, False, SimpleNamespace(animal=None), recall=True)
    assert r2.times_recalled == 0


def test_a_word_mastered_before_the_rule_is_not_demoted_by_a_right_answer():
    r = rec(mastery=90.0, status="mastered")
    apply_srs(r, True, SimpleNamespace(animal=None))
    assert r.status == "mastered"


# --------------------------------------------------------------------------- through the API

@pytest.fixture
def learner(client):
    return register(client, unique_name("recaller"))


def stored(sid):
    with SessionLocal() as db:
        s = db.get(models.PracticeSession, sid)
        return s.questions, s.answers


def level1_word(simplified):
    with SessionLocal() as db:
        lvl = db.query(models.HSKLevel).filter_by(level=1).one()
        return db.query(models.VocabularyWord).filter_by(hsk_level_id=lvl.id, simplified=simplified).one().id


def recognise(uid, word_id, mastery=60.0, recalled=0, due=True):
    """The learner already recognises this word (due for review, or not yet)."""
    with SessionLocal() as db:
        db.add(models.UserVocabulary(user_id=uid, word_id=word_id, status="reviewing", mastery=mastery, times_seen=6,
                                     times_missed=0, times_recalled=recalled,
                                     last_reviewed_at=datetime.utcnow() - timedelta(days=3),
                                     next_review_at=datetime.utcnow() + timedelta(hours=-1 if due else 48)))
        db.commit()


def round_for(client, h, word_id, locale="en"):
    s = expect(client, "post", ROUNDS, 201, headers={**h, "X-Locale": locale},
               json={"source": "vocab", "hsk_level": 1, "size": 4})
    qs, _ = stored(s["id"])
    i = next(i for i, q in enumerate(qs) if q["item_id"] == word_id)
    return s, i


def say(client, h, sid, index, text, status=200, locale="en"):
    return expect(client, "post", f"{ROUNDS}/{sid}/answer", status, headers={**h, "X-Locale": locale},
                  json={"index": index, "text": text, "response_ms": 3000})


def user_word(uid, word_id):
    with SessionLocal() as db:
        return db.query(models.UserVocabulary).filter_by(user_id=uid, word_id=word_id).one()


def test_a_recognised_word_is_asked_from_memory(client, learner):
    uid, h = learner
    eat = level1_word("吃")
    recognise(uid, eat)
    s, i = round_for(client, h, eat)
    q = s["questions"][i]
    assert q["type"] == "type_word" and q["options"] == [] and q["prompt"]["text"], q
    # Neither the word nor its sound is sent before the answer.
    assert "吃" not in q["prompt"]["text"] and not q["prompt"].get("speak") and not q["prompt"].get("pinyin"), q
    # A new word in the same round is still recognition.
    assert any(x["options"] for x in s["questions"]), s["questions"]


def test_typing_the_word_is_a_recall_and_counts(client, learner):
    uid, h = learner
    eat = level1_word("吃")
    recognise(uid, eat, mastery=80.0)
    s, i = round_for(client, h, eat)
    r = say(client, h, s["id"], i, "chi1")
    assert r["correct"] and r["check"]["kind"] == "exact" and r["card"]["hanzi"] == "吃", r
    rec_ = user_word(uid, eat)
    assert rec_.times_recalled == 1 and rec_.status == "mastered", (rec_.times_recalled, rec_.status)
    # The answer is stored with what was typed; a re-render shows the same.
    again = expect(client, "get", f"{ROUNDS}/{s['id']}", 200, headers=h)["questions"][i]["answer"]
    assert again["typed"] == "chi1" and again["check"]["kind"] == "exact", again


def test_wrong_tones_are_explained_and_kept_as_a_tone_mistake(client, learner):
    uid, h = learner
    eat = level1_word("吃")
    recognise(uid, eat)
    s, i = round_for(client, h, eat)
    r = say(client, h, s["id"], i, "chi4")
    assert not r["correct"] and r["check"] == {"kind": "tone", "typed": "chi4", "tones_typed": "4",
                                               "tones_expected": "1", "other": None}, r["check"]
    assert user_word(uid, eat).times_recalled == 0
    notebook = expect(client, "get", "/api/mistakes", 200, headers=h)
    m = next(m for m in notebook if m["reference"] == "吃")
    assert m["mistake_type"] == "tone" and m["answer_given"] == "chi4", m


def test_missing_tones_are_asked_for_once_before_they_count(client, learner):
    uid, h = learner
    eat = level1_word("吃")
    recognise(uid, eat)
    s, i = round_for(client, h, eat)
    first = say(client, h, s["id"], i, "chi")
    assert first == {"retry": "missing_tones", "typed": "chi"}
    _, answers = stored(s["id"])
    assert answers[i] is None and user_word(uid, eat).times_seen == 6  # nothing graded yet
    second = say(client, h, s["id"], i, "chi")
    assert not second["correct"] and second["check"]["kind"] == "missing_tones", second


def test_typing_another_word_is_a_real_mix_up(client, learner):
    uid, h = learner
    eat, drink = level1_word("吃"), level1_word("喝")
    recognise(uid, eat)
    s, i = round_for(client, h, eat)
    r = say(client, h, s["id"], i, "喝")
    assert not r["correct"] and r["check"]["kind"] == "other_word", r
    assert r["check"]["other"]["hanzi"] == "喝" and r["check"]["other"]["meaning"], r["check"]
    _, answers = stored(s["id"])
    assert answers[i]["choice_id"] == drink  # what the mix-up memory reads


def test_a_synonym_is_accepted_and_credited_to_the_word_typed(client, learner):
    uid, h = learner
    # Two HSK 1 words sharing a sense, with different readings.
    with SessionLocal() as db:
        lvl = db.query(models.HSKLevel).filter_by(level=1).one()
        words = [x for x in db.query(models.VocabularyWord).filter_by(hsk_level_id=lvl.id)
                 if x.meanings and x.pinyin]
        pair = next(((a.id, b.id, b.simplified) for a in words for b in words
                     if a.id != b.id and a.simplified != b.simplified
                     and recall.glosses(a.meanings) & recall.glosses(b.meanings)
                     and recall.pinyin_key(a.pinyin)[:2] != recall.pinyin_key(b.pinyin)[:2]), None)
    if pair is None:
        pytest.skip("no two HSK 1 words share a sense in this curriculum")
    target, other, other_text = pair
    recognise(uid, target)
    s, i = round_for(client, h, target)
    r = say(client, h, s["id"], i, other_text)
    assert r["correct"] and r["check"]["kind"] == "alternative" and r["check"]["other"]["hanzi"] == other_text, r
    assert user_word(uid, target).times_seen == 6  # the asked word: neither credited nor penalised
    assert user_word(uid, other).times_recalled == 1


def test_i_dont_know_is_an_honest_answer(client, learner):
    uid, h = learner
    eat = level1_word("吃")
    recognise(uid, eat)
    s, i = round_for(client, h, eat)
    r = say(client, h, s["id"], i, "")
    assert not r["correct"] and r["check"]["kind"] == "unknown" and r["card"]["hanzi"] == "吃", r


def test_the_answer_must_fit_the_question(client, learner):
    uid, h = learner
    eat = level1_word("吃")
    recognise(uid, eat)
    s, i = round_for(client, h, eat)
    expect(client, "post", f"{ROUNDS}/{s['id']}/answer", 422, headers=h, json={"index": i, "choice_id": eat})
    mc = next(j for j, q in enumerate(s["questions"]) if q["options"])
    expect(client, "post", f"{ROUNDS}/{s['id']}/answer", 422, headers=h, json={"index": mc, "text": "chi1"})


def test_a_wrong_pick_shows_the_word_that_was_picked(client, learner):
    _, h = learner
    s = expect(client, "post", ROUNDS, 201, headers=h, json={"source": "vocab", "hsk_level": 1, "size": 4})
    qs, _ = stored(s["id"])
    q = qs[0]
    wrong = next(o for o in q["option_ids"] if o != q["item_id"])
    r = expect(client, "post", f"{ROUNDS}/{s['id']}/answer", 200, headers=h, json={"index": 0, "choice_id": wrong})
    assert r["check"]["kind"] == "picked" and r["check"]["other"]["hanzi"], r["check"]


def test_a_russian_prompt_is_russian(client, learner):
    uid, h = learner
    eat = level1_word("吃")
    recognise(uid, eat)
    s, i = round_for(client, h, eat, locale="ru")
    q = s["questions"][i]
    assert q["type"] == "type_word" and any("а" <= c.lower() <= "я" for c in q["prompt"]["text"]), q


def test_a_character_is_read_aloud_from_memory(client, learner):
    uid, h = learner
    with SessionLocal() as db:
        lvl = db.query(models.HSKLevel).filter_by(level=1).one()
        char = db.query(models.Hanzi).filter_by(hsk_level_id=lvl.id, character="好").one()
        db.add(models.UserHanzi(user_id=uid, hanzi_id=char.id, status="reviewing", mastery=80.0, times_seen=6,
                                times_missed=0, next_review_at=datetime.utcnow() - timedelta(hours=1)))
        db.commit()
        cid = char.id
    s = expect(client, "post", ROUNDS, 201, headers=h, json={"source": "hanzi", "hsk_level": 1, "size": 4})
    qs, _ = stored(s["id"])
    i = next(i for i, q in enumerate(qs) if q["item_id"] == cid)
    assert s["questions"][i]["type"] == "type_pinyin" and s["questions"][i]["prompt"]["text"] == "好"
    r = say(client, h, s["id"], i, "hao3")
    assert r["correct"] and r["check"]["kind"] == "exact", r
    with SessionLocal() as db:
        assert db.query(models.UserHanzi).filter_by(user_id=uid, hanzi_id=cid).one().status == "mastered"


def test_self_checks_alone_never_master_a_character(client, learner):
    uid, h = learner
    with SessionLocal() as db:
        lvl = db.query(models.HSKLevel).filter_by(level=1).one()
        cid = db.query(models.Hanzi).filter_by(hsk_level_id=lvl.id).order_by(models.Hanzi.id).first().id
    for _ in range(12):
        with SessionLocal() as db:
            r = db.query(models.UserHanzi).filter_by(user_id=uid, hanzi_id=cid).first()
            if r is not None:
                r.next_review_at = datetime.utcnow() - timedelta(minutes=1)
                db.commit()
        v = expect(client, "post", f"/api/hanzi/{cid}/review", 200, headers=h, json={"correct": True})
    assert v["mastery"] >= 85 and v["status"] == "reviewing", v


# --------------------------------------------------------------------------- the recall round and the plan

def level1_words(n, skip=()):
    with SessionLocal() as db:
        lvl = db.query(models.HSKLevel).filter_by(level=1).one()
        rows = (db.query(models.VocabularyWord).filter_by(hsk_level_id=lvl.id).order_by(models.VocabularyWord.id).all())
        from app.services.practice import _usable

        return [r.id for r in rows if _usable("vocab", r) and r.simplified not in skip][:n]


def test_nothing_to_recall_is_a_real_empty_state(client, learner):
    _, h = learner
    s = expect(client, "post", ROUNDS, 200, headers=h, json={"source": "recall"})
    assert s["empty"] == "nothing_due" and s["questions"] == []


def test_the_recall_round_asks_only_what_was_never_recalled(client, learner):
    uid, h = learner
    eat, drink = level1_word("吃"), level1_word("喝")
    recognise(uid, eat, mastery=90.0, due=False)  # recognised, never recalled
    recognise(uid, drink, recalled=2, due=False)  # already recalled
    s = expect(client, "post", ROUNDS, 201, headers=h, json={"source": "recall"})
    assert [(q["type"], q["options"]) for q in s["questions"]] == [("type_word", [])], s["questions"]
    assert stored(s["id"])[0][0]["item_id"] == eat
    r = say(client, h, s["id"], 0, "吃")
    assert r["correct"]
    # Recalled now: the queue is empty again.
    assert expect(client, "post", ROUNDS, 200, headers=h, json={"source": "recall"})["empty"] == "nothing_due"


def test_a_tajik_learner_is_not_asked_by_an_english_meaning(client, learner):
    uid, h = learner
    eat = level1_word("吃")
    recognise(uid, eat, due=False)
    with SessionLocal() as db:
        db.query(models.ContentTranslation).filter_by(content_type="vocab_word", content_key=str(eat),
                                                      locale="tg").delete()
        db.commit()
    s = expect(client, "post", ROUNDS, 200, headers={**h, "X-Locale": "tg"}, json={"source": "recall"})
    assert s["empty"] == "nothing_due"
    assert expect(client, "get", "/api/journey", 200, headers={**h, "X-Locale": "tg"})["unrecalled"] == 0
    assert expect(client, "get", "/api/journey", 200, headers=h)["unrecalled"] == 1


@pytest.fixture
def placed(client):
    """A learner past the beginner foundation (HSK 2), as in test_next_action."""
    uid, h = register(client, unique_name("recallnext"))
    expect(client, "get", "/api/journey", 200, headers=h)
    with SessionLocal() as db:
        for s in db.get(models.User, uid).user_skills:
            s.mastery = 20.0
        db.commit()
    return uid, h


def test_a_few_unrecalled_words_are_a_task_for_today(client, placed):
    uid, h = placed
    for wid in level1_words(5):
        recognise(uid, wid, due=False)
    j = expect(client, "get", "/api/journey", 200, headers=h)
    assert j["unrecalled"] == 5 and j["next"]["kind"] != "recall", j["next"]
    task = next(t for t in j["today"]["tasks"] if t["key"] == "recall")
    assert task == {"key": "recall", "to": "/practice?source=recall", "count": 5, "done": False}


def test_a_large_backlog_of_unrecalled_words_comes_before_new_material(client, placed):
    uid, h = placed
    for wid in level1_words(20):
        recognise(uid, wid, due=False)
    nxt = expect(client, "get", "/api/journey", 200, headers=h)["next"]
    assert nxt == {"kind": "recall", "key": "recall", "to": "/practice?source=recall", "count": 20}, nxt


# --------------------------------------------------------------------------- what the learner knows

def test_knowledge_puts_each_word_in_one_honest_stage(client, learner):
    uid, h = learner
    w = level1_words(6)
    with SessionLocal() as db:
        for wid, status, mastery, recalled in ((w[0], "learning", 20.0, 0), (w[1], "reviewing", 60.0, 0),
                                               (w[2], "reviewing", 70.0, 1), (w[3], "mastered", 95.0, 2),
                                               # mastered before recall existed: recognised, not mastered
                                               (w[4], "mastered", 90.0, 0)):
            db.add(models.UserVocabulary(user_id=uid, word_id=wid, status=status, mastery=mastery, times_seen=5,
                                         times_missed=0, times_recalled=recalled,
                                         next_review_at=datetime.utcnow() + timedelta(days=2)))
        # Known and five days past its review: due, and fading.
        db.add(models.UserVocabulary(user_id=uid, word_id=w[5], status="reviewing", mastery=60.0, times_seen=5,
                                     times_missed=0, times_recalled=1,
                                     next_review_at=datetime.utcnow() - timedelta(days=5)))
        db.commit()
    k = expect(client, "get", "/api/analytics/knowledge", 200, headers=h)
    assert k["vocab"] == {"learning": 1, "recognised": 2, "recalled": 2, "mastered": 1, "due": 1, "slipping": 1,
                          "met": 6}, k["vocab"]
    assert k["hanzi"]["met"] == 0 and k["recall"] == {"answered": 0, "correct": 0, "days": 30}


def test_knowledge_counts_answers_from_memory(client, learner):
    uid, h = learner
    eat = level1_word("吃")
    recognise(uid, eat)
    s, i = round_for(client, h, eat)
    say(client, h, s["id"], i, "chi1")
    k = expect(client, "get", "/api/analytics/knowledge", 200, headers=h)
    assert k["recall"]["answered"] == 1 and k["recall"]["correct"] == 1, k["recall"]
    assert k["vocab"]["mastered"] + k["vocab"]["recalled"] >= 1


def test_knowledge_is_private(client):
    expect(client, "get", "/api/analytics/knowledge", 401)
