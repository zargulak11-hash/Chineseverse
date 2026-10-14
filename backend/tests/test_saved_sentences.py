"""Line-by-line reading (StoryReader) saves hard sentences: the text is the
book's own, saving is idempotent and per learner, the list carries the
book's translation, and a line's translation comes from the book (no AI)."""

import pytest

from app.services import books as lib
from app.services import stories
from helpers import expect, register, unique_name


@pytest.fixture
def learner(client):
    return register(client, unique_name("reader"))


def open_book():
    return next(b for b in lib.all_books() if stories.gate(b) <= 1)


def test_save_list_and_remove_a_sentence(client, learner):
    _, h = learner
    book = open_book()
    slug, first = book["slug"], book["chapters"][0]["sentences"][0]
    ch = expect(client, "get", f"/api/stories/{slug}/chapters/1", 200, headers=h)
    assert ch["saved"] == []
    r = expect(client, "post", f"/api/stories/{slug}/chapters/1/sentences/0/save", 200, headers=h)
    again = expect(client, "post", f"/api/stories/{slug}/chapters/1/sentences/0/save", 200, headers=h)
    assert r == again and r["saved"]
    assert expect(client, "get", f"/api/stories/{slug}/chapters/1", 200, headers=h)["saved"] == [0]

    saved = expect(client, "get", "/api/stories/saved/sentences", 200, headers={**h, "X-Locale": "ru"})
    assert len(saved) == 1
    s = saved[0]
    assert s["zh"] == first["zh"] and s["pinyin"] and s["slug"] == slug and (s["chapter"], s["position"]) == (1, 0)
    assert s["translation"] == stories._text(first, "ru") and s["translation"]
    zh = expect(client, "get", "/api/stories/saved/sentences", 200, headers={**h, "X-Locale": "zh"})
    assert zh[0]["translation"] == ""

    _, other = register(client, unique_name("other"))
    assert expect(client, "get", "/api/stories/saved/sentences", 200, headers=other) == []
    expect(client, "delete", f"/api/stories/saved/sentences/{s['id']}", 404, headers=other)
    expect(client, "delete", f"/api/stories/saved/sentences/{s['id']}", 204, headers=h)
    assert expect(client, "get", "/api/stories/saved/sentences", 200, headers=h) == []


def test_only_real_sentences_of_open_books_can_be_saved(client, learner):
    _, h = learner
    book = open_book()
    n = len(book["chapters"][0]["sentences"])
    expect(client, "post", f"/api/stories/{book['slug']}/chapters/1/sentences/{n}/save", 404, headers=h)
    expect(client, "post", f"/api/stories/{book['slug']}/chapters/999/sentences/0/save", 404, headers=h)
    expect(client, "post", "/api/stories/no-such-book/chapters/1/sentences/0/save", 404, headers=h)
    locked = next((b for b in lib.all_books() if stories.gate(b) > 1), None)
    if locked:
        expect(client, "post", f"/api/stories/{locked['slug']}/chapters/1/sentences/0/save", 403, headers=h)
    expect(client, "post", f"/api/stories/{book['slug']}/chapters/1/sentences/0/save", 401)


def test_a_lines_translation_is_the_books_own(client, learner):
    _, h = learner
    book = open_book()
    first = book["chapters"][0]["sentences"][0]
    r = expect(client, "post", f"/api/stories/{book['slug']}/explain", 200, headers={**h, "X-Locale": "tg"},
               json={"chapter": 1, "text": first["zh"], "focus": "translate"})
    assert r["translation"] == {"text": stories._text(first, "tg"), "source": "book"}
