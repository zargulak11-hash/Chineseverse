"""Chinese Stories (HSK 1-9) and the beginner journey -- end to end on a
fresh database: real content, real gates, progress only from real rounds."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/stories.db"
os.environ["AI_PROVIDER"] = "offline"

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services import books as books_lib  # noqa: E402
from app.services import stories as stories_svc  # noqa: E402


def expect(client, method, url, expected, **kwargs):
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == expected, f"{method.upper()} {url} -> {resp.status_code} (expected {expected}): {resp.text}"
    return resp.json() if resp.content else None


def register(client, name):
    data = expect(client, "post", "/api/auth/register", 201,
                  json={"username": name, "email": f"{name}@example.com", "password": "secret1"})
    h = {"Authorization": f"Bearer {data['access_token']}"}
    expect(client, "get", "/api/dashboard", 200, headers=h)
    return data["user"]["id"], h


def set_level(uid, level):
    with SessionLocal() as db:
        for us in db.query(models.UserSkill).filter_by(user_id=uid):
            us.mastery = (level - 1) * 15 + 0.5
        db.commit()


def play(client, h, body, *, correct=True):
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json=body)
    with SessionLocal() as db:
        keys = db.get(models.PracticeSession, s["id"]).questions
    for q in s["questions"]:
        choice = keys[q["index"]]["item_id"] if correct else next(o for o in keys[q["index"]]["option_ids"]
                                                                   if o != keys[q["index"]]["item_id"])
        expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h,
               json={"index": q["index"], "choice_id": choice})
    done = expect(client, "post", f"/api/practice/sessions/{s['id']}/complete", 200, headers=h)
    return s, keys, done


def count_rows(uid):
    with SessionLocal() as db:
        return tuple(db.query(m).filter_by(user_id=uid).count() for m in (
            models.PracticeSession, models.UserVocabulary, models.ActivityEvent, models.VoiceAttempt))


with TestClient(app) as client:
    expect(client, "get", "/api/stories", 401)
    expect(client, "get", "/api/journey", 401)

    # ---- content: every level, every translation, words within the level
    BOOKS = books_lib.all_books()
    with SessionLocal() as db:
        assert sorted({b["level"] for b in BOOKS}) == list(range(1, 10))
        for b in BOOKS:
            assert all(b["title"].get(k) for k in ("zh", "en", "ru", "tg")), b["slug"]
            assert all(b["summary"].get(k) for k in ("zh", "en", "ru", "tg")), b["slug"]
            for ch in b["chapters"]:
                for s in ch["sentences"]:
                    assert all(s.get(k) for k in ("zh", "en", "ru", "tg")), (b["slug"], s["zh"])
                for q in ch["questions"]:
                    assert 0 <= q["answer"] < len(q["options"])
                    if b["level"] <= 3:
                        assert all((q["tr"] or {}).get(k) for k in ("en", "ru", "tg")), (b["slug"], q["q"])
            rep = stories_svc.vocabulary_report(db, b)
            assert rep["ok"], (b["slug"], rep)
        avg = {lvl: sum(b["characters"] for b in BOOKS if b["level"] == lvl) / sum(b["sentence_count"] for b in BOOKS if b["level"] == lvl)
               for lvl in range(1, 10)}
        # Sentences get longer at every level, and the advanced band reads
        # far longer sentences than HSK 1.
        assert all(avg[k] < avg[k + 1] for k in range(1, 9)) and avg[9] > 2.5 * avg[1], avg
    print(f"[PASS] {len(BOOKS)} books cover HSK 1-9; every sentence translated (EN/RU/TG); "
          "every book within its level's vocabulary; sentences grow with the level")

    # ---- a brand-new learner: the foundation, step 1, nothing claimed
    uid, h = register(client, "beginner")
    before = count_rows(uid)
    j = expect(client, "get", "/api/journey", 200, headers=h)
    assert j["level"] == 1 and j["stage"] == "foundation"
    assert j["next"] == {"kind": "foundation", "key": "tones", "to": "/foundation"}, j["next"]
    assert [s["status"] for s in j["foundation"]["steps"]] == ["current"] + ["todo"] * 7
    assert j["foundation"]["done"] == 0 and j["levels"][0]["status"] == "current"
    lib = expect(client, "get", "/api/stories", 200, headers=h)
    status = {s["slug"]: s["status"] for s in lib["books"]}
    assert status["my-family"] == "new" and status["rainy-day"] == "locked" and status["night-courier"] == "locked"
    assert books_lib.get(lib["recommended"])["level"] == 1 and lib["continue"] is None
    assert count_rows(uid) == before, "reading the journey or the library must not write progress"
    print("[PASS] new learner: the foundation, step 1 'tones' is next, nothing done; only HSK 1 stories open")

    # ---- locked stories are refused by the reader AND the round
    expect(client, "get", "/api/stories/rainy-day", 403, headers=h)
    expect(client, "get", "/api/stories/rainy-day/chapters/1", 403, headers=h)
    expect(client, "post", "/api/practice/sessions", 403, headers=h, json={"source": "story", "story": "rainy-day"})
    expect(client, "get", "/api/stories/no-such-story", 404, headers=h)
    print("[PASS] a story above the learner's level is refused by the reader and by the practice round (403)")

    # ---- step 1: a passed tones round completes it, and only it
    s, keys, done = play(client, h, {"source": "tones"})
    types = {q["type"] for q in keys}
    assert types == {"char_to_pinyin", "listen_to_word"}, types
    j = expect(client, "get", "/api/journey", 200, headers=h)
    st = {s["key"]: s["status"] for s in j["foundation"]["steps"]}
    assert st["tones"] == "done" and st["characters"] == "current" and j["next"]["key"] == "characters"
    print("[PASS] the tones round (pinyin among other tones + words by ear) completes step 1; step 2 is next")

    # ---- a failed round doesn't count
    uid2, h2 = register(client, "struggler")
    play(client, h2, {"source": "tones"}, correct=False)
    j2 = expect(client, "get", "/api/journey", 200, headers=h2)
    assert j2["foundation"]["steps"][0]["status"] == "current", "a failed round must not complete a step"
    print("[PASS] a failed tones round leaves the step open")

    # ---- the reader: Chinese with curriculum pinyin, words marked; translation only on request
    v = expect(client, "get", "/api/stories/my-family", 200, headers={**h, "X-Locale": "ru"})
    assert v["support"]["pinyin"] == "on" and v["title"] == "Моя семья" and v["counts"]["new"] > 0
    c = expect(client, "get", "/api/stories/my-family/chapters/1", 200, headers={**h, "X-Locale": "ru"})
    sents = [s for p in c["paragraphs"] for s in p]
    assert all(s["pinyin"] and "tr" not in s for s in sents), "no translation laid over the text"
    assert any(t.get("state") == "new" for t in sents[0]["tokens"])
    ex = expect(client, "post", "/api/stories/my-family/explain", 200, headers={**h, "X-Locale": "ru"},
                json={"chapter": 1, "text": sents[0]["zh"], "focus": "translate"})
    assert ex["translation"] == {"text": "Меня зовут Сяомин.", "source": "book"}
    vz = expect(client, "get", "/api/stories/my-family", 200, headers={**h, "X-Locale": "zh"})
    assert vz["title"] == "我的家"
    print("[PASS] the reader: curriculum pinyin and word states, no translation until asked; then the book's own (RU)")

    # ---- a story round: graded, recorded, the journey moves
    before = count_rows(uid)
    s, keys, done = play(client, h, {"source": "story", "story": "my-family"})
    types = [q["type"] for q in keys]
    assert types.count("story_q") == 3 and types.count("story_listen") == 1
    assert any(t in ("meaning_to_word", "word_to_meaning", "listen_to_word") for t in types), types
    assert done["score"] == 100.0
    lib = expect(client, "get", "/api/stories", 200, headers=h)
    assert next(x for x in lib["books"] if x["slug"] == "my-family")["status"] == "completed"
    j = expect(client, "get", "/api/journey", 200, headers=h)
    assert next(x for x in j["foundation"]["steps"] if x["key"] == "story")["status"] == "done"
    assert j["levels"][0]["stories_read"] == 1
    pp = expect(client, "get", "/api/passport", 200, headers=h)
    assert any(m.get("kind") == "first_story" for m in pp.get("timeline", pp.get("milestones", []))), "first_story milestone"
    with SessionLocal() as db:
        assert db.query(models.ActivityEvent).filter_by(user_id=uid, action_type="story_read").count() == 1
    print("[PASS] a story round (3 comprehension, 1 heard line, word cards) marks it read, counts on the "
          "roadmap, records the Passport milestone and the activity")

    # ---- say the heard line aloud: a real voice attempt completes 'speak'
    listen = next(q for q in keys if q["type"] == "story_listen")
    idx = keys.index(listen)
    expect(client, "post", f"/api/practice/sessions/{s['id']}/speak", 200, headers=h,
           json={"index": idx, "spoken_text": listen["speak"]})
    j = expect(client, "get", "/api/journey", 200, headers=h)
    assert next(x for x in j["foundation"]["steps"] if x["key"] == "speak")["status"] == "done"
    print("[PASS] saying the story's line aloud stores a voice attempt and completes the 'speak' step")

    # ---- a learner placed at HSK 3: no foundation detour, the HSK path is next
    uid3, h3 = register(client, "placedhsk3")
    set_level(uid3, 3)
    j3 = expect(client, "get", "/api/journey", 200, headers=h3)
    assert j3["level"] == 3 and j3["stage"] == "growing" and j3["foundation"]["past"]
    assert all(s["status"] == "past" for s in j3["foundation"]["steps"]), "past, never claimed as done"
    assert j3["next"]["kind"] in ("lesson", "review", "exam", "stories")
    lib3 = {x["slug"]: x["status"] for x in expect(client, "get", "/api/stories", 200, headers=h3)["books"]}
    assert lib3["first-metro-ride"] == "new" and lib3["the-interview"] == "locked"
    print("[PASS] a learner at HSK 3 skips the foundation (shown as 'past', not 'done'); HSK 1-3 stories open, HSK 4 locked")

    # ---- HSK 7-9 is one band: all three advanced stories open at level 7
    uid7, h7 = register(client, "advanced7")
    set_level(uid7, 7)
    lib7 = {x["slug"]: x["status"] for x in expect(client, "get", "/api/stories", 200, headers=h7)["books"]}
    assert all(lib7[k] == "new" for k in ("night-courier", "last-bookshop", "echoes-of-the-silk-road"))
    v9 = expect(client, "get", "/api/stories/echoes-of-the-silk-road", 200, headers=h7)
    assert v9["support"] == {"pinyin": "off", "rate": 1.0}
    print("[PASS] at HSK 7 the 7-9 band's three stories open; HSK 9 support is minimal (no pinyin, translation on request)")

    print("ALL STORIES / JOURNEY TESTS PASSED")
