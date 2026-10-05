"""Chinese Stories as a reading library -- books, chapters, the reader,
help while reading, real progress.

Covers: auth and ownership, the library (levels, locking, recommended,
continue), chapters, the bookmark, finishing chapters and a book (once),
word lookups, listening, sentence explanations (book translation, AI
explanation with its cache, rate limit and offline fallback), the chapter
round, and that reading pages writes nothing."""

import pytest

from app import models
from app.database import SessionLocal
from app.services import ai_client, books
from app.services import stories as svc
from helpers import expect, register, unique_name

BOOK = "my-day"


def set_level(client, uid, h, level):
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


@pytest.fixture
def reader(client):
    return register(client, unique_name("reader"))


@pytest.fixture(scope="module")
def chapter1(client):
    """Chapter 1 of the book as a new HSK 1 reader sees it, as sentences."""
    _, h = register(client, "chapterviewer")
    ch1 = expect(client, "get", f"/api/stories/{BOOK}/chapters/1", 200, headers=h)
    return ch1, [s for p in ch1["paragraphs"] for s in p]


def explain(client, h, text, focus="explain", chapter=1, locale=None, expected=200):
    headers = {**h, "X-Locale": locale} if locale else h
    return expect(client, "post", f"/api/stories/{BOOK}/explain", expected, headers=headers,
                  json={"chapter": chapter, "text": text, "focus": focus})


def play_chapter_round(client, h, chapter):
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "story", "story": BOOK, "chapter": chapter})
    with SessionLocal() as db:
        keys = db.get(models.PracticeSession, s["id"]).questions
    for q in s["questions"]:
        expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h,
               json={"index": q["index"], "choice_id": keys[q["index"]]["item_id"]})
    expect(client, "post", f"/api/practice/sessions/{s['id']}/complete", 200, headers=h)
    return keys


def test_every_stories_endpoint_needs_a_signed_in_learner(client):
    for method, url in (("get", "/api/stories"), ("get", f"/api/stories/{BOOK}"), ("get", f"/api/stories/{BOOK}/chapters/1"),
                        ("put", f"/api/stories/{BOOK}/progress"), ("post", f"/api/stories/{BOOK}/chapters/1/finish"),
                        ("post", f"/api/stories/{BOOK}/explain"), ("post", f"/api/stories/{BOOK}/lookup"),
                        ("post", f"/api/stories/{BOOK}/listen")):
        kwargs = {} if method == "get" else {"json": {}}
        assert getattr(client, method)(url, **kwargs).status_code == 401, url


def test_a_new_reader_sees_hsk1_open_and_reading_writes_nothing(client, reader):
    uid, h = reader
    book = books.get(BOOK)
    assert book and len(book["chapters"]) == 4
    lib = expect(client, "get", "/api/stories", 200, headers=h)
    cards = {c["slug"]: c for c in lib["books"]}
    assert lib["level"] == 1 and lib["recommended"] == BOOK and lib["continue"] is None
    c = cards[BOOK]
    assert c["status"] == "new" and c["chapters"] == 4 and c["minutes"] > 0 and c["new_words"] > 0 and c["percent"] == 0
    assert c["difficulty"] in ("easy", "medium", "challenging") and c["topic"] == "daily"
    assert len(lib["levels"]) == 9 and not lib["levels"][0]["locked"] and all(lv["locked"] for lv in lib["levels"][1:])
    assert all(x["status"] == "locked" for x in lib["books"] if x["gate"] > 1)
    expect(client, "get", f"/api/stories/{BOOK}", 200, headers=h)
    expect(client, "get", f"/api/stories/{BOOK}/chapters/1", 200, headers=h)
    assert rows(uid) == (0, 0), "opening the library, a book or a chapter writes nothing"


def test_a_chapter_is_chinese_with_curriculum_pinyin_names_and_marked_words(client, reader, chapter1):
    _, h = reader
    ch1, sents = chapter1
    assert ch1["title_zh"] == "早上" and ch1["total"] == 4 and ch1["support"]["pinyin"] == "on"
    assert all(s["pinyin"] and "tr" not in s for s in sents)
    first = sents[0]["tokens"]
    assert any(t.get("name") == "Wáng Xiǎoyǔ" for t in first), first
    assert any(t.get("word_id") and t["state"] == "new" for t in first)
    assert sents[0]["pinyin"].startswith("wǒ jiào Wáng Xiǎoyǔ"), sents[0]["pinyin"]
    expect(client, "get", f"/api/stories/{BOOK}/chapters/5", 404, headers=h)
    expect(client, "get", f"/api/stories/{BOOK}/chapters/0", 404, headers=h)
    expect(client, "get", "/api/stories/no-such-book", 404, headers=h)


def test_a_book_above_the_level_is_refused_everywhere(client, reader):
    _, h = reader
    lib = expect(client, "get", "/api/stories", 200, headers=h)
    locked = next(x["slug"] for x in lib["books"] if x["status"] == "locked")
    expect(client, "get", f"/api/stories/{locked}", 403, headers=h)
    expect(client, "get", f"/api/stories/{locked}/chapters/1", 403, headers=h)
    expect(client, "put", f"/api/stories/{locked}/progress", 403, headers=h, json={"chapter": 1, "position": 0})
    expect(client, "post", f"/api/stories/{locked}/chapters/1/finish", 403, headers=h)
    expect(client, "post", f"/api/stories/{locked}/explain", 403, headers=h, json={"chapter": 1, "text": "我"})
    expect(client, "post", "/api/practice/sessions", 403, headers=h, json={"source": "story", "story": locked})


def test_the_bookmark_reopens_where_the_reader_stopped_and_is_their_own(client, reader):
    _, h = reader
    expect(client, "put", f"/api/stories/{BOOK}/progress", 422, headers=h, json={"chapter": 2, "position": 99})
    expect(client, "put", f"/api/stories/{BOOK}/progress", 404, headers=h, json={"chapter": 9, "position": 0})
    expect(client, "put", f"/api/stories/{BOOK}/progress", 200, headers=h, json={"chapter": 2, "position": 3})
    lib = expect(client, "get", "/api/stories", 200, headers=h)
    c = next(x for x in lib["books"] if x["slug"] == BOOK)
    assert lib["continue"] == BOOK and c["status"] == "in_progress" and c["chapter"] == 2 and 0 < c["percent"] < 25, c
    v = expect(client, "get", f"/api/stories/{BOOK}", 200, headers=h)
    assert v["progress"]["chapter"] == 2 and v["progress"]["position"] == 3 and not v["progress"]["completed"]
    assert expect(client, "get", f"/api/stories/{BOOK}/chapters/2", 200, headers=h)["position"] == 3
    assert expect(client, "get", f"/api/stories/{BOOK}/chapters/1", 200, headers=h)["position"] == 0
    # someone else's reading is their own
    _, h2 = register(client, unique_name("reader_other"))
    lib2 = expect(client, "get", "/api/stories", 200, headers=h2)
    assert lib2["continue"] is None and next(x for x in lib2["books"] if x["slug"] == BOOK)["status"] == "new"


def test_word_lookups_are_counted_for_words_of_the_book_only(client, reader, chapter1):
    _, h = reader
    wid = next(t["word_id"] for t in chapter1[1][0]["tokens"] if t.get("word_id"))
    for k in (1, 2, 3):
        assert expect(client, "post", f"/api/stories/{BOOK}/lookup", 200, headers=h, json={"word_id": wid})["times"] == k
    with SessionLocal() as db:
        foreign = db.query(models.VocabularyWord).filter(models.VocabularyWord.simplified == "飞机").first().id
    expect(client, "post", f"/api/stories/{BOOK}/lookup", 404, headers=h, json={"word_id": foreign})


def test_sentence_help_uses_the_curriculum_and_the_books_translation_offline(client, reader, chapter1):
    _, h = reader
    sents = chapter1[1]
    s0 = sents[0]["zh"]
    ex = explain(client, h, s0, locale="ru")
    assert ex["translation"] == {"text": "Меня зовут Ван Сяоюй, в этом году мне восемнадцать.", "source": "book"}
    assert ex["pinyin"].startswith("wǒ jiào Wáng Xiǎoyǔ") and ex["ai"] is None and ex["ai_status"] == "offline"
    w = {x["text"]: x for x in ex["words"]}
    assert w["叫"]["pinyin"] == "jiào" and w["叫"]["meaning"] and w["叫"]["level"] == 1 and w["王小雨"]["name"]
    ex2 = explain(client, h, sents[2]["zh"] + sents[3]["zh"], focus="translate", locale="tg")
    assert ex2["translation"]["source"] == "book" and ex2["translation"]["text"].startswith("Субҳ ман"), ex2["translation"]
    part = explain(client, h, "六点半", focus="translate")
    assert part["translation"] == {"text": None, "source": None}, "offline: no invented translation of a fragment"
    assert explain(client, h, s0, focus="translate", locale="zh")["translation"]["text"] is None
    # only text of that chapter, a known focus
    explain(client, h, "你好吗", expected=422)
    explain(client, h, s0, chapter=2, expected=422)
    explain(client, h, "abc", expected=422)
    explain(client, h, s0, focus="hack", expected=422)


def test_ai_help_is_on_request_cached_for_everyone_and_limited(client, reader, chapter1, monkeypatch):
    _, h = reader
    _, h2 = register(client, unique_name("reader_cache"))
    sents = chapter1[1]
    calls = []

    def fake(text, locale, level, glossary, grammar):
        calls.append((text, locale, level))
        return {"translation": "T", "meaning": "M", "points": [{"title": "了", "body": "done"}], "example": None}

    monkeypatch.setattr(ai_client, "explain_reading", fake)
    with SessionLocal() as db:
        cached_before = db.query(models.AIExplanation).count()
    s1 = sents[1]["zh"]
    a = explain(client, h, s1)
    assert a["ai_status"] == "ok" and a["ai"]["meaning"] == "M" and len(calls) == 1
    assert a["translation"]["source"] == "book", "the book's translation wins over the AI's"
    b = explain(client, h2, s1, focus="grammar")
    assert b["ai_status"] == "cached" and b["ai"] == a["ai"] and len(calls) == 1, "same text, same help -> no second call"
    explain(client, h, s1, locale="ru")
    assert len(calls) == 2, "another language is another explanation"
    p = explain(client, h, s1, focus="pinyin")
    assert p["ai_status"] == "skipped" and len(calls) == 2, "pinyin/words never call the AI"
    monkeypatch.setattr(svc, "AI_PER_HOUR", 0)
    lim = explain(client, h, sents[4]["zh"])
    assert lim["ai_status"] == "limit" and lim["ai"] is None and lim["words"], "over the limit: curriculum help still works"
    with SessionLocal() as db:
        assert db.query(models.AIExplanation).count() == cached_before + 2


def test_listening_is_counted_and_logged(client, reader):
    uid, h = reader
    assert expect(client, "post", f"/api/stories/{BOOK}/listen", 200, headers=h, json={"chapter": 1})["listened"] == 1
    assert events(uid, "story_listen") == 1


def test_a_chapter_round_uses_that_chapter_and_finishes_it(client, reader):
    _, h = reader
    keys = play_chapter_round(client, h, 2)
    qs = [q["q"] for q in keys if q["type"] == "story_q"]
    assert qs == [q["q"] for q in books.get(BOOK)["chapters"][1]["questions"]], qs
    v = expect(client, "get", f"/api/stories/{BOOK}", 200, headers=h)
    assert [c["done"] for c in v["chapters"]] == [False, True, False, False]
    expect(client, "post", "/api/practice/sessions", 404, headers=h, json={"source": "story", "story": BOOK, "chapter": 7})


def test_finishing_the_book_counts_once_with_real_numbers_and_reaches_the_app(client, reader, chapter1):
    uid, h = reader
    sents = chapter1[1]
    wid = next(t["word_id"] for t in sents[0]["tokens"] if t.get("word_id"))
    # A real reading: listen once, look one word up three times, ask for
    # help on six sentences, play the chapter-2 round.
    expect(client, "post", f"/api/stories/{BOOK}/listen", 200, headers=h, json={"chapter": 1})
    for _ in range(3):
        expect(client, "post", f"/api/stories/{BOOK}/lookup", 200, headers=h, json={"word_id": wid})
    for s in sents[:6]:
        explain(client, h, s["zh"])
    play_chapter_round(client, h, 2)

    r = expect(client, "post", f"/api/stories/{BOOK}/chapters/1/finish", 200, headers=h)
    assert r["chapters_done"] == 2 and not r["book_completed"] and r["next_chapter"] == 2
    expect(client, "post", f"/api/stories/{BOOK}/chapters/3/finish", 200, headers=h)
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
    with SessionLocal() as db:
        assert BOOK in svc.read_slugs(db, db.get(models.User, uid))

    # the rest of ChineseVerse sees it
    ach = {a["code"]: a for a in expect(client, "get", "/api/achievements", 200, headers=h)}
    assert ach["first_story"]["unlocked"]
    pp = expect(client, "get", "/api/passport", 200, headers=h)
    assert any(e["kind"] == "first_story" for e in pp["timeline"])
    j = expect(client, "get", "/api/journey", 200, headers=h)
    assert next(x for x in j["foundation"]["steps"] if x["key"] == "story")["status"] == "done"
    mem = expect(client, "get", "/api/companion/memory", 200, headers=h)
    reading = [m for m in mem["memories"] if m["kind"] == "reading_word"]
    assert reading and reading[0]["data"]["word_id"] == wid and reading[0]["data"]["count"] == 3, mem["memories"]


def test_at_hsk7_every_book_opens_and_support_fades(client, reader):
    uid7, h7 = reader
    set_level(client, uid7, h7, 7)
    lib7 = expect(client, "get", "/api/stories", 200, headers={**h7, "X-Locale": "tg"})
    assert all(x["status"] != "locked" for x in lib7["books"]) and not any(lv["locked"] for lv in lib7["levels"]), (
        lib7["level"], [(x["slug"], x["status"]) for x in lib7["books"] if x["status"] == "locked"], lib7["levels"])
    adv = next(x for x in lib7["books"] if x["level"] == 9)
    va = expect(client, "get", f"/api/stories/{adv['slug']}", 200, headers={**h7, "X-Locale": "tg"})
    assert va["support"]["pinyin"] == "off" and va["title"] == books.get(adv["slug"])["title"]["tg"]
    vz = expect(client, "get", f"/api/stories/{adv['slug']}", 200, headers={**h7, "X-Locale": "zh"})
    assert vz["title"] == vz["title_zh"]
