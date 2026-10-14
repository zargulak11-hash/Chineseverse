"""AI roleplay (services/roleplay.py). The model is replaced by a fake that
answers like Gemini would (JSON), so every rule around it is tested for
real: honest unavailability, validation of what the model returns,
corrections reaching the notebook, XP/DNA from real verdicts only, saved
words linked to the curriculum, ownership, limits and the summary."""

import json

import pytest

from app import models
from app.database import SessionLocal
from app.services import ai_client, roleplay
from helpers import expect, register, unique_name

BASE = "/api/roleplay"


@pytest.fixture
def learner(client):
    return register(client, unique_name("roleplayer"))


class FakeModel:
    """Replies by what the prompt asks for; records every call."""

    def __init__(self):
        self.calls = []
        self.turn_replies = []
        self.fail = False

    def __call__(self, messages, max_tokens=200, temperature=0.8, json_mode=False):
        self.calls.append(messages)
        if self.fail:
            raise ValueError("model unavailable")
        system = messages[0]["content"]
        if "Suggest ONE" in system:
            return json.dumps({"zh": "我要一杯茶。", "pinyin": "Wǒ yào yì bēi chá.", "translation": "I'd like a cup of tea."})
        if "kind Mandarin teacher" in system:
            return json.dumps({"summary": "You ordered food clearly.", "strengths": ["Clear requests"],
                               "next": ["Try using 一碗"]})
        return json.dumps(self.turn_replies.pop(0))


@pytest.fixture
def ai(monkeypatch):
    fake = FakeModel()
    monkeypatch.setattr(ai_client.settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(ai_client.settings, "ai_provider", "auto")
    monkeypatch.setattr(ai_client, "_gemini_chat", fake)
    return fake


def good(zh="好的，你想喝什么？", goals=(0,), words=()):
    return {"reply": {"zh": zh, "pinyin": "Hǎo de, nǐ xiǎng hē shénme?", "translation": "OK, what would you like to drink?"},
            "feedback": {"ok": True, "corrected": "", "explanation": "", "kind": "grammar"},
            "words": list(words), "goals_met": list(goals)}


def wrong(corrected="我要一碗米饭。", explanation="Rice is counted with 碗 (bowl), not 个."):
    return {"reply": {"zh": "好的，一碗米饭。还要别的吗？", "pinyin": "Hǎo de, yì wǎn mǐfàn. Hái yào bié de ma?",
                      "translation": "OK, one bowl of rice. Anything else?"},
            "feedback": {"ok": False, "corrected": corrected, "explanation": explanation, "kind": "word"},
            "words": [{"zh": "米饭", "pinyin": "mǐfàn", "meaning": "rice"}], "goals_met": [0]}


def start(client, h, scenario="restaurant", status=201):
    return expect(client, "post", f"{BASE}/sessions", status, headers=h, json={"scenario": scenario})


def say(client, h, sid, text, status=200, locale="en"):
    return expect(client, "post", f"{BASE}/sessions/{sid}/turn", status, headers={**h, "X-Locale": locale},
                  json={"text": text})


def test_without_ai_the_feature_says_so_instead_of_faking_a_partner(client, learner):
    _, h = learner
    lst = expect(client, "get", f"{BASE}/scenarios", 200, headers=h)
    assert lst["ai_available"] is False and len(lst["scenarios"]) == len(roleplay.SCENARIOS)
    r = start(client, h, status=503)
    assert "not available" in r["detail"]


def test_scenarios_are_localized_and_gated_by_level(client, learner, ai):
    _, h = learner
    lst = expect(client, "get", f"{BASE}/scenarios", 200, headers={**h, "X-Locale": "tg"})
    rest = next(s for s in lst["scenarios"] if s["slug"] == "restaurant")
    assert rest["title"] == "Дар тарабхона" and rest["unlocked"] and len(rest["goals"]) == 3
    # The partner's name is Chinese on every screen -- never translated.
    assert rest["role"] == "服务员"
    bank = next(s for s in lst["scenarios"] if s["slug"] == "bank")
    assert bank["unlocked"] is False
    assert "HSK 3" in start(client, h, "bank", status=403)["detail"]
    start(client, h, "no-such-place", status=404)


def test_a_conversation_corrects_the_learner_and_remembers_it(client, learner, ai):
    uid, h = learner
    s = start(client, h)
    assert s["turns"][0]["role"] == "partner" and s["turns"][0]["zh"].startswith("你好")
    assert s["turns"][0]["pinyin"] and s["turns"][0]["translation"]
    with SessionLocal() as db:
        xp0 = db.get(models.User, uid).total_xp

    ai.turn_replies.append(wrong())
    r = say(client, h, s["id"], "我要一个米饭")
    learner_turn, partner = r["turns"][-2], r["turns"][-1]
    assert learner_turn["text"] == "我要一个米饭"
    assert learner_turn["feedback"]["corrected"] == "我要一碗米饭。" and "碗" in learner_turn["feedback"]["explanation"]
    assert partner["zh"].startswith("好的") and partner["translation"]
    # The word the partner suggested is the curriculum's own, savable to review.
    rice = partner["words"][0]
    assert rice["zh"] == "米饭" and rice["word_id"]
    expect(client, "post", f"/api/vocab/{rice['word_id']}/track", 200, headers=h)
    assert r["goals"][0]["met"] and not r["goals"][1]["met"]

    notebook = expect(client, "get", "/api/mistakes", 200, headers=h)
    m = next(m for m in notebook if m["answer_given"] == "我要一个米饭")
    assert m["correct_answer"] == "我要一碗米饭。"

    ai.turn_replies.append(good(goals=(0, 1)))
    r = say(client, h, s["id"], "我要一碗米饭")
    assert r["turns"][-2]["feedback"] is None and r["goals"][1]["met"]
    with SessionLocal() as db:
        assert db.get(models.User, uid).total_xp == xp0 + roleplay.XP_PER_GOOD_TURN
    # The model saw the whole conversation, ending with the new message.
    assert "我要一个米饭" in ai.calls[-1][1]["content"] and ai.calls[-1][1]["content"].endswith("我要一碗米饭")


@pytest.mark.parametrize("bad", [
    "not json at all",
    json.dumps({"reply": {"zh": "OK, what do you want?"}, "feedback": {"ok": True}}),  # not Chinese
    json.dumps({"reply": {"zh": "好的 hello"}, "feedback": {"ok": True}}),  # mixed languages
    json.dumps(["a list"]),
])
def test_unusable_model_output_is_refused_and_nothing_is_stored(client, learner, ai, monkeypatch, bad):
    _, h = learner
    s = start(client, h)
    monkeypatch.setattr(ai_client, "_gemini_chat", lambda *a, **k: bad)
    r = say(client, h, s["id"], "你好", status=503)
    assert "again" in r["detail"]
    assert len(expect(client, "get", f"{BASE}/sessions/{s['id']}", 200, headers=h)["turns"]) == 1


def test_a_wrong_verdict_without_a_correction_is_not_counted_against_the_learner(client, learner, ai):
    _, h = learner
    s = start(client, h)
    ai.turn_replies.append(wrong(corrected="", explanation=""))
    r = say(client, h, s["id"], "我要米饭")
    assert r["turns"][-2]["feedback"] is None


def test_translations_are_kept_per_language(client, learner, ai):
    _, h = learner
    s = start(client, h)
    reply = good()
    reply["reply"]["translation"] = "Хорошо, что вы будете пить?"
    ai.turn_replies.append(reply)
    say(client, h, s["id"], "我要米饭", locale="ru")
    en = expect(client, "get", f"{BASE}/sessions/{s['id']}", 200, headers=h)["turns"][-1]
    ru = expect(client, "get", f"{BASE}/sessions/{s['id']}", 200, headers={**h, "X-Locale": "ru"})["turns"][-1]
    assert en["translation"] == "" and ru["translation"]
    zh = expect(client, "get", f"{BASE}/sessions/{s['id']}", 200, headers={**h, "X-Locale": "zh"})["turns"][0]
    assert zh["translation"] == ""  # the opening line too: no translation on a Chinese screen


def test_limits_and_ownership(client, learner, ai, monkeypatch):
    _, h = learner
    s = start(client, h)
    assert "200" in say(client, h, s["id"], "好" * 201, status=422)["detail"]
    _, other = register(client, unique_name("snoop"))
    expect(client, "get", f"{BASE}/sessions/{s['id']}", 404, headers=other)
    say(client, other, s["id"], "你好", status=404)
    expect(client, "get", f"{BASE}/sessions/{s['id']}", 401)
    monkeypatch.setattr(roleplay, "MAX_LEARNER_TURNS", 1)
    ai.turn_replies.append(good())
    say(client, h, s["id"], "你好")
    assert "finish" in say(client, h, s["id"], "再见", status=409)["detail"]


def test_hints_come_from_the_model_or_from_the_scenario(client, learner, ai):
    _, h = learner
    s = start(client, h)
    hint = expect(client, "post", f"{BASE}/sessions/{s['id']}/hint", 200, headers=h)
    assert hint["line"]["zh"] == "我要一杯茶。" and hint["goal"] and any(w["word_id"] for w in hint["words"])
    ai.fail = True
    offline = expect(client, "post", f"{BASE}/sessions/{s['id']}/hint", 200, headers=h)
    assert offline["line"] is None and offline["goal"] and offline["words"]


def test_the_summary_counts_what_really_happened(client, learner, ai):
    uid, h = learner
    s = start(client, h)
    expect(client, "post", f"{BASE}/sessions/{s['id']}/finish", 422, headers=h)  # nothing said yet
    ai.turn_replies += [wrong(), good(goals=(0, 1)), good(goals=(2,))]
    for text in ("我要一个米饭", "我要一碗米饭", "多少钱？"):
        say(client, h, s["id"], text)
    done = expect(client, "post", f"{BASE}/sessions/{s['id']}/finish", 200, headers=h)
    sm = done["summary"]
    assert (sm["messages"], sm["accepted"], sm["goals_met"], sm["goals_total"]) == (3, 2, 3, 3)
    assert sm["corrections"] == [{"text": "我要一个米饭", "corrected": "我要一碗米饭。",
                                  "explanation": "Rice is counted with 碗 (bowl), not 个."}]
    assert sm["feedback"]["summary"] == "You ordered food clearly." and sm["xp"] == roleplay.XP_FINISH
    assert done["status"] == "finished"
    say(client, h, s["id"], "再见", status=409)
    # Finishing twice changes nothing.
    again = expect(client, "post", f"{BASE}/sessions/{s['id']}/finish", 200, headers=h)
    assert again["summary"] == sm
    assert expect(client, "get", f"{BASE}/scenarios", 200, headers=h)["scenarios"][0]["played"] == 1


def test_the_summary_stands_without_the_model(client, learner, ai):
    _, h = learner
    s = start(client, h)
    ai.turn_replies.append(good())
    say(client, h, s["id"], "我要米饭")
    ai.fail = True
    sm = expect(client, "post", f"{BASE}/sessions/{s['id']}/finish", 200, headers=h)["summary"]
    assert sm["feedback"] is None and sm["messages"] == 1 and sm["xp"] == 0  # one message is not a played scenario


def test_a_deleted_learner_takes_their_conversations_along(client, learner, ai):
    uid, h = learner
    start(client, h)
    from app.crud import delete_user_cascade_safe

    with SessionLocal() as db:
        delete_user_cascade_safe(db, db.get(models.User, uid))
        db.commit()
        assert db.query(models.RoleplaySession).filter_by(user_id=uid).count() == 0


def test_a_tajik_translation_in_latin_letters_is_repaired_or_dropped(client, learner, ai):
    """Seen live: Gemini returned "Хub, yak kosasa guruch..." for Tajik."""
    _, h = learner
    s = start(client, h)
    half = good()
    half["reply"]["translation"] = "Хub, чой."  # one word half Latin: repaired
    latin = good()
    latin["reply"]["translation"] = "Хub, yak kosasa guruch."  # whole words in Latin: dropped
    ai.turn_replies += [half, latin]
    r1 = say(client, h, s["id"], "我要茶", locale="tg")
    assert r1["turns"][-1]["translation"] == "Хуб, чой."
    r2 = say(client, h, s["id"], "我要米饭", locale="tg")
    assert r2["turns"][-1]["translation"] == ""
