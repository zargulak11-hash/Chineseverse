"""Chinese Stories as a reading library -- books, chapters, the reader,
help while reading, real progress -- end to end on a fresh SQLite database.

Covers: auth and ownership, the library (levels, locking, recommended,
continue), chapters, the bookmark, finishing chapters and a book (once),
word lookups, listening, sentence explanations (book translation, AI
explanation with its cache, rate limit and offline fallback), the chapter
round, and that reading pages writes nothing."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/library.db"
os.environ["AI_PROVIDER"] = "offline"

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services import ai_client, books  # noqa: E402
from app.services import stories as svc  # noqa: E402

BOOK = "my-day"


def expect(client, method, url, expected, **kwargs):
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == expected, f"{method.upper()} {url} -> {resp.status_code} (expected {expected}): {resp.text}"
    return resp.json() if resp.content else None


def register(client, name):
    data = expect(client, "post", "/api/auth/register", 201,
                  json={"username": name, "email": f"{name}@example.com", "password": "secret1"})
    return data["user"]["id"], {"Authorization": f"Bearer {data['access_token']}"}


def set_level(uid, h, level):
    expect(client, "get", "/api/dashboard", 200, headers=h)  # creates the skill rows
    with SessionLocal() as db:
        for us in db.query(models.UserSkill).filter_by(user_id=uid):
            us.mastery = (level - 1) * 15 + 0.5
        db.commit()


def rows(uid):
    with SessionLocal() as db:
        return (db.query(models.StoryProgress).filter_by(user_id=uid).count(),
                db.query(models.ActivityEvent).filter_by(user_id=uid).count())


def events(uid, kind):
    with SessionLocal() as db:
        return db.query(models.ActivityEvent).filter_by(user_id=uid, action_type=kind).count()


with TestClient(app) as client:
    book = books.get(BOOK)
    assert book and len(book["chapters"]) == 4
    for method, url in (("get", "/api/stories"), ("get", f"/api/stories/{BOOK}"), ("get", f"/api/stories/{BOOK}/chapters/1"),
                        ("put", f"/api/stories/{BOOK}/progress"), ("post", f"/api/stories/{BOOK}/chapters/1/finish"),
                        ("post", f"/api/stories/{BOOK}/explain"), ("post", f"/api/stories/{BOOK}/lookup"),
                        ("post", f"/api/stories/{BOOK}/listen")):
        kwargs = {} if method == "get" else {"json": {}}
        assert getattr(client, method)(url, **kwargs).status_code == 401, url
    print("[PASS] every Stories endpoint needs a signed-in learner")

    # ---- a fresh HSK 1 learner: the library, nothing written by looking
    uid, h = register(client, "reader1")
    lib = expect(client, "get", "/api/stories", 200, headers=h)
    cards = {c["slug"]: c for c in lib["books"]}
    assert lib["level"] == 1 and lib["recommended"] == BOOK and lib["continue"] is None
    c = cards[BOOK]
    assert c["status"] == "new" and c["chapters"] == 4 and c["minutes"] > 0 and c["new_words"] > 0 and c["percent"] == 0
    assert c["difficulty"] in ("easy", "medium", "challenging") and c["topic"] == "daily"
    assert len(lib["levels"]) == 9 and not lib["levels"][0]["locked"] and all(lv["locked"] for lv in lib["levels"][1:])
    assert all(x["status"] == "locked" for x in lib["books"] if x["gate"] > 1)
    expect(client, "get", f"/api/stories/{BOOK}", 200, headers=h)
    ch1 = expect(client, "get", f"/api/stories/{BOOK}/chapters/1", 200, headers=h)
    assert rows(uid) == (0, 0), "opening the library, a book or a chapter writes nothing"
    print("[PASS] new learner: HSK 1 open, 2-9 locked, 《我的一天》 recommended; reading pages writes nothing")

    # ---- chapters: Chinese, curriculum pinyin, names, words marked; no translations
    sents = [s for p in ch1["paragraphs"] for s in p]
    assert ch1["title_zh"] == "早上" and ch1["total"] == 4 and ch1["support"]["pinyin"] == "on"
    assert all(s["pinyin"] and "tr" not in s for s in sents)
    first = sents[0]["tokens"]
    assert any(t.get("name") == "Wáng Xiǎoyǔ" for t in first), first
    assert any(t.get("word_id") and t["state"] == "new" for t in first)
    assert sents[0]["pinyin"].startswith("wǒ jiào Wáng Xiǎoyǔ"), sents[0]["pinyin"]
    expect(client, "get", f"/api/stories/{BOOK}/chapters/5", 404, headers=h)
    expect(client, "get", f"/api/stories/{BOOK}/chapters/0", 404, headers=h)
    expect(client, "get", "/api/stories/no-such-book", 404, headers=h)
    print("[PASS] a chapter: Chinese with curriculum pinyin, names read as names, words marked new; bad chapters 404")

    # ---- locking: every endpoint refuses a book above the level
    locked = next(x["slug"] for x in lib["books"] if x["status"] == "locked")
    expect(client, "get", f"/api/stories/{locked}", 403, headers=h)
    expect(client, "get", f"/api/stories/{locked}/chapters/1", 403, headers=h)
    expect(client, "put", f"/api/stories/{locked}/progress", 403, headers=h, json={"chapter": 1, "position": 0})
    expect(client, "post", f"/api/stories/{locked}/chapters/1/finish", 403, headers=h)
    expect(client, "post", f"/api/stories/{locked}/explain", 403, headers=h, json={"chapter": 1, "text": "我"})
    expect(client, "post", "/api/practice/sessions", 403, headers=h, json={"source": "story", "story": locked})
    print("[PASS] a book above the learner's level is refused by the reader, progress, help and the round (403)")

    # ---- the bookmark and "Continue reading"
    expect(client, "put", f"/api/stories/{BOOK}/progress", 422, headers=h, json={"chapter": 2, "position": 99})
    expect(client, "put", f"/api/stories/{BOOK}/progress", 404, headers=h, json={"chapter": 9, "position": 0})
    expect(client, "put", f"/api/stories/{BOOK}/progress", 200, headers=h, json={"chapter": 2, "position": 3})
    lib = expect(client, "get", "/api/stories", 200, headers=h)
    c = next(x for x in lib["books"] if x["slug"] == BOOK)
    assert lib["continue"] == BOOK and c["status"] == "in_progress" and c["chapter"] == 2 and 0 < c["percent"] < 25, c
    v = expect(client, "get", f"/api/stories/{BOOK}", 200, headers=h)
    assert v["progress"]["chapter"] == 2 and v["progress"]["position"] == 3 and not v["progress"]["completed"]
    ch2 = expect(client, "get", f"/api/stories/{BOOK}/chapters/2", 200, headers=h)
    assert ch2["position"] == 3
    assert expect(client, "get", f"/api/stories/{BOOK}/chapters/1", 200, headers=h)["position"] == 0
    print("[PASS] the bookmark is saved and returned: 'Continue reading' reopens chapter 2 at sentence 4")

    # ---- someone else's reading is their own
    uid2, h2 = register(client, "reader2")
    lib2 = expect(client, "get", "/api/stories", 200, headers=h2)
    assert lib2["continue"] is None and next(x for x in lib2["books"] if x["slug"] == BOOK)["status"] == "new"
    print("[PASS] progress belongs to its reader")

    # ---- words: lookups counted (only words of the book)
    wid = next(t["word_id"] for t in first if t.get("word_id"))
    for k in (1, 2, 3):
        assert expect(client, "post", f"/api/stories/{BOOK}/lookup", 200, headers=h, json={"word_id": wid})["times"] == k
    with SessionLocal() as db:
        foreign = db.query(models.VocabularyWord).filter(models.VocabularyWord.simplified == "飞机").first().id
    expect(client, "post", f"/api/stories/{BOOK}/lookup", 404, headers=h, json={"word_id": foreign})
    print("[PASS] word lookups are counted for words of the book only")

    # ---- help with a sentence: curriculum data + the book's translation, no AI needed
    s0 = sents[0]["zh"]
    ex = expect(client, "post", f"/api/stories/{BOOK}/explain", 200, headers={**h, "X-Locale": "ru"},
                json={"chapter": 1, "text": s0, "focus": "explain"})
    assert ex["translation"] == {"text": "Меня зовут Ван Сяоюй, в этом году мне восемнадцать.", "source": "book"}
    assert ex["pinyin"].startswith("wǒ jiào Wáng Xiǎoyǔ") and ex["ai"] is None and ex["ai_status"] == "offline"
    w = {x["text"]: x for x in ex["words"]}
    assert w["叫"]["pinyin"] == "jiào" and w["叫"]["meaning"] and w["叫"]["level"] == 1 and w["王小雨"]["name"]
    two = sents[2]["zh"] + sents[3]["zh"]
    ex2 = expect(client, "post", f"/api/stories/{BOOK}/explain", 200, headers={**h, "X-Locale": "tg"},
                 json={"chapter": 1, "text": two, "focus": "translate"})
    assert ex2["translation"]["source"] == "book" and ex2["translation"]["text"].startswith("Субҳ ман"), ex2["translation"]
    part = expect(client, "post", f"/api/stories/{BOOK}/explain", 200, headers=h,
                  json={"chapter": 1, "text": "六点半", "focus": "translate"})
    assert part["translation"] == {"text": None, "source": None}, "offline: no invented translation of a fragment"
    assert expect(client, "post", f"/api/stories/{BOOK}/explain", 200, headers={**h, "X-Locale": "zh"},
                  json={"chapter": 1, "text": s0, "focus": "translate"})["translation"]["text"] is None
    expect(client, "post", f"/api/stories/{BOOK}/explain", 422, headers=h, json={"chapter": 1, "text": "你好吗", "focus": "explain"})
    expect(client, "post", f"/api/stories/{BOOK}/explain", 422, headers=h, json={"chapter": 2, "text": s0, "focus": "explain"})
    expect(client, "post", f"/api/stories/{BOOK}/explain", 422, headers=h, json={"chapter": 1, "text": "abc", "focus": "explain"})
    expect(client, "post", f"/api/stories/{BOOK}/explain", 422, headers=h, json={"chapter": 1, "text": s0, "focus": "hack"})
    print("[PASS] explain: curriculum pinyin/words, the book's own RU/TG translation; offline nothing is invented; "
          "only text of that chapter")

    # ---- AI explanation: only on request, cached for everyone, limited, offline-safe
    calls = []

    def fake(text, locale, level, glossary, grammar):
        calls.append((text, locale, level))
        return {"translation": "T", "meaning": "M", "points": [{"title": "了", "body": "done"}], "example": None}

    real = ai_client.explain_reading
    ai_client.explain_reading = fake
    try:
        s1 = sents[1]["zh"]
        a = expect(client, "post", f"/api/stories/{BOOK}/explain", 200, headers=h, json={"chapter": 1, "text": s1, "focus": "explain"})
        assert a["ai_status"] == "ok" and a["ai"]["meaning"] == "M" and len(calls) == 1
        assert a["translation"]["source"] == "book", "the book's translation wins over the AI's"
        b = expect(client, "post", f"/api/stories/{BOOK}/explain", 200, headers=h2, json={"chapter": 1, "text": s1, "focus": "grammar"})
        assert b["ai_status"] == "cached" and b["ai"] == a["ai"] and len(calls) == 1, "same text, same help -> no second call"
        expect(client, "post", f"/api/stories/{BOOK}/explain", 200, headers={**h, "X-Locale": "ru"},
               json={"chapter": 1, "text": s1, "focus": "explain"})
        assert len(calls) == 2, "another language is another explanation"
        p = expect(client, "post", f"/api/stories/{BOOK}/explain", 200, headers=h, json={"chapter": 1, "text": s1, "focus": "pinyin"})
        assert p["ai_status"] == "skipped" and len(calls) == 2, "pinyin/words never call the AI"
        old = svc.AI_PER_HOUR
        svc.AI_PER_HOUR = 0
        lim = expect(client, "post", f"/api/stories/{BOOK}/explain", 200, headers=h,
                     json={"chapter": 1, "text": sents[4]["zh"], "focus": "explain"})
        assert lim["ai_status"] == "limit" and lim["ai"] is None and lim["words"], "over the limit: curriculum help still works"
        svc.AI_PER_HOUR = old
    finally:
        ai_client.explain_reading = real
    with SessionLocal() as db:
        assert db.query(models.AIExplanation).count() == 2
    print("[PASS] AI help only when asked; one cached answer serves every learner; per-learner limit; "
          "curriculum help never depends on it")

    # ---- listening
    assert expect(client, "post", f"/api/stories/{BOOK}/listen", 200, headers=h, json={"chapter": 1})["listened"] == 1
    assert events(uid, "story_listen") == 1
    print("[PASS] listening is counted and logged")

    # ---- a chapter round: that chapter's questions; finishing it finishes the chapter
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "story", "story": BOOK, "chapter": 2})
    with SessionLocal() as db:
        keys = db.get(models.PracticeSession, s["id"]).questions
    qs = [q["q"] for q in keys if q["type"] == "story_q"]
    assert qs == [q["q"] for q in book["chapters"][1]["questions"]], qs
    for q in s["questions"]:
        expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h,
               json={"index": q["index"], "choice_id": keys[q["index"]]["item_id"]})
    expect(client, "post", f"/api/practice/sessions/{s['id']}/complete", 200, headers=h)
    v = expect(client, "get", f"/api/stories/{BOOK}", 200, headers=h)
    assert [c["done"] for c in v["chapters"]] == [False, True, False, False]
    expect(client, "post", "/api/practice/sessions", 404, headers=h, json={"source": "story", "story": BOOK, "chapter": 7})
    print("[PASS] the chapter-2 round uses chapter 2's questions; completing it finishes chapter 2")

    # ---- finishing chapters, then the book (once)
    r = expect(client, "post", f"/api/stories/{BOOK}/chapters/1/finish", 200, headers=h)
    assert r["chapters_done"] == 2 and not r["book_completed"] and r["next_chapter"] == 2
    expect(client, "post", f"/api/stories/{BOOK}/chapters/3/finish", 200, headers=h)
    assert expect(client, "get", "/api/achievements", 200, headers=h) is not None
    r = expect(client, "post", f"/api/stories/{BOOK}/chapters/4/finish", 200, headers=h)
    assert r["book_completed"] and r["just_completed"] and r["next_chapter"] is None
    st = r["stats"]
    assert st["chapters"] == 4 and st["chapters_total"] == 4 and st["listened"] == 1 and st["looked_up"] == 1
    assert st["explained"] >= 6 and st["rounds"] == 1 and st["words_total"] > 0
    assert r["next"] and books.get(r["next"]["slug"])["level"] == 1 and r["next"]["slug"] != BOOK
    again = expect(client, "post", f"/api/stories/{BOOK}/chapters/4/finish", 200, headers=h)
    assert again["book_completed"] and not again["just_completed"]
    assert events(uid, "story_chapter") == 3 and events(uid, "story_book") == 1, "chapters/book count once"
    lib = expect(client, "get", "/api/stories", 200, headers=h)
    c = next(x for x in lib["books"] if x["slug"] == BOOK)
    assert c["status"] == "completed" and c["percent"] == 100 and lib["continue"] is None
    assert BOOK in svc.read_slugs(SessionLocal(), SessionLocal().get(models.User, uid))
    print("[PASS] finishing the last chapter completes the book once, with real numbers and the next book")

    # ---- the rest of ChineseVerse sees it
    ach = {a["code"]: a for a in expect(client, "get", "/api/achievements", 200, headers=h)}
    assert ach["first_story"]["unlocked"]
    pp = expect(client, "get", "/api/passport", 200, headers=h)
    assert any(e["kind"] == "first_story" for e in pp["timeline"])
    j = expect(client, "get", "/api/journey", 200, headers=h)
    assert next(x for x in j["foundation"]["steps"] if x["key"] == "story")["status"] == "done"
    mem = expect(client, "get", "/api/companion/memory", 200, headers=h)
    reading = [m for m in mem["memories"] if m["kind"] == "reading_word"]
    assert reading and reading[0]["data"]["word_id"] == wid and reading[0]["data"]["count"] == 3, mem["memories"]
    print("[PASS] the finished book unlocks 'First Story', reaches the Passport and Journey; "
          "the companion notices the word looked up 3 times")

    # ---- an advanced learner: the 7-9 band opens, support fades, other languages
    uid7, h7 = register(client, "reader7")
    set_level(uid7, h7, 7)
    lib7 = expect(client, "get", "/api/stories", 200, headers={**h7, "X-Locale": "tg"})
    assert all(x["status"] != "locked" for x in lib7["books"]) and not any(lv["locked"] for lv in lib7["levels"]), (
        lib7["level"], [(x["slug"], x["status"]) for x in lib7["books"] if x["status"] == "locked"], lib7["levels"])
    adv = next(x for x in lib7["books"] if x["level"] == 9)
    va = expect(client, "get", f"/api/stories/{adv['slug']}", 200, headers={**h7, "X-Locale": "tg"})
    assert va["support"]["pinyin"] == "off" and va["title"] == books.get(adv["slug"])["title"]["tg"]
    vz = expect(client, "get", f"/api/stories/{adv['slug']}", 200, headers={**h7, "X-Locale": "zh"})
    assert vz["title"] == vz["title_zh"]
    print("[PASS] at HSK 7 every book opens; HSK 9 reads without pinyin; titles in TG and ZH")

print("ALL STORY LIBRARY TESTS PASSED")
