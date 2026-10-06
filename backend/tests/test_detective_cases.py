"""Detective Mode: the hand-written case files and the two newer generated
structures (who was late / who has it now).

Covers: every case file validates and reads at its level, the loader's
refusals, the case list and its level filter, the dossier (read-only, no
verdict before the case is solved), playing a case file as a graded round
(clues graded like a story's, the deduction answered with the case's own
verdict, the solve recorded and counted once per round), level locking,
and that the new structures' deductions really follow from their clues."""

import random

import pytest

from app import models
from app.database import SessionLocal
from app.services import case_files, detective
from app.services.books import BookError
from helpers import expect, register as register_only, unique_name

FILE = "the-teachers-cup"


def register(client):
    uid, h = register_only(client, unique_name("sleuth"))
    expect(client, "get", "/api/dashboard", 200, headers=h)  # creates skill rows
    return uid, h


def set_level(uid, level):
    with SessionLocal() as db:
        for us in db.query(models.UserSkill).filter_by(user_id=uid):
            us.mastery = (level - 1) * 15 + 0.5
        db.commit()


def stored(sid):
    with SessionLocal() as db:
        return db.get(models.PracticeSession, sid).questions


def answer_all(client, h, sid, questions, right=True):
    keys = stored(sid)
    for q in questions:
        good = keys[q["index"]]["item_id"]
        choice = good if right else next(o["id"] for o in q["options"] if o["id"] != good)
        expect(client, "post", f"/api/practice/sessions/{sid}/answer", 200, headers=h,
               json={"index": q["index"], "choice_id": choice, "response_ms": 2500})


def test_every_case_file_is_valid_and_written_for_its_level(client):
    cases = case_files.all_cases()
    assert len(cases) >= 10 and {c["level"] for c in cases} >= {1, 2, 3, 4}
    with SessionLocal() as db:
        for c in cases:
            assert 2 <= len(c["suspects"]) <= 5 and 0 <= c["culprit"] < len(c["suspects"])
            assert all(s["name"] in c["names"] for s in c["suspects"])
            assert len(c["evidence"]) >= 2 and len(c["timeline"]) >= 2 and len(c["questions"]) >= 2
            for q in c["questions"]:
                assert q["tr"] and all(q["tr"].get(k) for k in ("en", "ru", "tg")), (c["slug"], q["q"])
            rep = case_files.vocabulary_report(db, c)
            assert rep["ok"], (c["slug"], rep)


def test_the_loader_refuses_a_broken_case():
    good = {
        "slug": "x", "level": 1, "title": ["案子", "Case", "Дело", "Парванда"], "summary": ["案子", "a", "b", "c"],
        "names": {"小明": "Xiǎomíng", "小红": "Xiǎohóng"},
        "brief": [["有人拿了书。", "a", "b", "c"]],
        "suspects": [{"name": "小明", "role": ["学生", "a", "b", "c"], "statement": ["我在家。", "a", "b", "c"]},
                     {"name": "小红", "role": ["学生", "a", "b", "c"], "statement": ["我在学校。", "a", "b", "c"]}],
        "evidence": [["书在学校。", "a", "b", "c"], ["小红在学校。", "a", "b", "c"]],
        "timeline": [{"time": "08:00", "event": ["书在桌子上。", "a", "b", "c"]},
                     {"time": "09:00", "event": ["书没有了。", "a", "b", "c"]}],
        "questions": [{"q": "书在哪儿？", "options": ["学校", "家"], "answer": 0},
                      {"q": "小红在哪儿？", "options": ["学校", "家"], "answer": 0}],
        "ask": ["谁拿了书？", "a", "b", "c"], "culprit": 1, "verdict": [["是小红。", "a", "b", "c"]],
    }
    assert case_files.parse(good)["culprit"] == 1
    broken = [
        {"culprit": 5}, {"level": 10}, {"slug": "Bad Slug"},
        {"suspects": good["suspects"][:1]},
        {"suspects": [dict(good["suspects"][0], name="老王"), good["suspects"][1]]},  # a name without pinyin
        {"timeline": list(reversed(good["timeline"]))},                              # out of time order
        {"timeline": [{"time": "8 am", "event": ["书。", "a", "b", "c"]}] * 2},
        {"questions": good["questions"][:1]}, {"evidence": good["evidence"][:1]},
        {"brief": [["English only", "a", "b", "c"]]},
    ]
    for patch in broken:
        with pytest.raises(BookError):  # CaseFileError, or the shared book checks
            case_files.parse({**good, **patch})


def test_the_case_list_offers_structures_and_files_by_level(client):
    _, h = register(client)
    lst = expect(client, "get", "/api/detective/cases", 200, headers=h)
    files = {f["slug"]: f for f in lst["files"]}
    assert len(files) == len(case_files.all_cases())
    assert not files[FILE]["locked"] and files[FILE]["suspects"] == 3 and files[FILE]["played"] == 0
    assert all(f["locked"] for f in lst["files"] if f["level"] > 1)
    assert [x["level"] for x in lst["file_levels"]] == list(range(1, 10))
    one = expect(client, "get", "/api/detective/cases?level=1", 200, headers=h)
    assert one["files"] and all(f["level"] == 1 for f in one["files"])
    ru = expect(client, "get", "/api/detective/cases?level=1", 200, headers={**h, "X-Locale": "ru"})
    assert ru["files"][0]["title"] == case_files.get(ru["files"][0]["slug"])["title"]["ru"]
    expect(client, "get", "/api/detective/cases?level=0", 422, headers=h)
    assert client.get("/api/detective/files/" + FILE).status_code == 401


def test_a_case_file_is_studied_played_and_its_verdict_shown_once_solved(client):
    uid, h = register(client)
    case = case_files.get(FILE)
    d = expect(client, "get", f"/api/detective/files/{FILE}", 200, headers=h)
    assert [s["name"] for s in d["suspects"]] == [s["name"] for s in case["suspects"]]
    assert d["brief"][0]["zh"] == case["brief"][0]["zh"] and d["brief"][0]["pinyin"] and d["brief"][0]["tr"]
    assert len(d["timeline"]) == len(case["timeline"]) and d["timeline"][0]["time"] == case["timeline"][0]["time"]
    assert d["verdict"] is None and d["culprit"] is None, "the answer stays hidden until solved"
    with SessionLocal() as db:
        assert db.query(models.PracticeSession).filter_by(user_id=uid).count() == 0, "reading writes nothing"

    s = expect(client, "post", "/api/practice/sessions", 201, headers=h,
               json={"source": "detective", "case": f"file:{FILE}"})
    assert s["context"]["kind"] == "case" and s["context"]["file"] == FILE
    assert s["context"]["intro"]["zh"].startswith(case["brief"][0]["zh"])
    types = [q["type"] for q in s["questions"]]
    assert types == ["story_q"] * len(case["questions"]) + ["case_deduce"]
    final = s["questions"][-1]
    assert sorted(o["label"] for o in final["options"]) == sorted(x["name"] for x in case["suspects"])
    assert all("item_id" not in q for q in s["questions"])
    answer_all(client, h, s["id"], s["questions"][:-1])
    keys = stored(s["id"])
    r = expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h,
               json={"index": final["index"], "choice_id": keys[final["index"]]["item_id"]})
    assert r["correct"] and r["card"]["hanzi"] == case["suspects"][case["culprit"]]["name"]
    assert r["card"]["solution"] == [v["zh"] for v in case["verdict"]] and r["card"]["meaning"]
    expect(client, "post", f"/api/practice/sessions/{s['id']}/complete", 200, headers=h)
    with SessionLocal() as db:
        assert db.query(models.ActivityEvent).filter_by(user_id=uid, action_type="detective_case").count() == 1

    lst = expect(client, "get", "/api/detective/cases", 200, headers=h)
    card = next(f for f in lst["files"] if f["slug"] == FILE)
    assert card["played"] == 1 and card["solved"] == 1
    after = expect(client, "get", f"/api/detective/files/{FILE}", 200, headers=h)
    assert after["culprit"] == case["suspects"][case["culprit"]]["name"]
    assert [v["zh"] for v in after["verdict"]] == [v["zh"] for v in case["verdict"]]


def test_a_wrong_accusation_is_played_but_not_solved(client):
    _, h = register(client)
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h,
               json={"source": "detective", "case": "file:the-fish-for-dinner"})
    answer_all(client, h, s["id"], s["questions"], right=False)
    expect(client, "post", f"/api/practice/sessions/{s['id']}/complete", 200, headers=h)
    card = next(f for f in expect(client, "get", "/api/detective/cases", 200, headers=h)["files"]
                if f["slug"] == "the-fish-for-dinner")
    assert card["played"] == 1 and card["solved"] == 0
    assert expect(client, "get", "/api/detective/files/the-fish-for-dinner", 200, headers=h)["verdict"] is None


def test_case_files_above_the_level_are_locked_and_unknown_ones_missing(client):
    uid, h = register(client)
    high = next(c for c in case_files.all_cases() if c["level"] >= 3)
    expect(client, "get", f"/api/detective/files/{high['slug']}", 403, headers=h)
    expect(client, "post", "/api/practice/sessions", 403, headers=h,
           json={"source": "detective", "case": f"file:{high['slug']}"})
    expect(client, "get", "/api/detective/files/no-such-case", 404, headers=h)
    expect(client, "post", "/api/practice/sessions", 404, headers=h, json={"source": "detective", "case": "file:nope"})
    set_level(uid, 7)
    adv = next(c for c in case_files.all_cases() if c["level"] == 7)
    d = expect(client, "get", f"/api/detective/files/{adv['slug']}", 200, headers=h)
    assert d["brief"][0]["pinyin"] is None, "advanced case files are read without pinyin"


@pytest.mark.parametrize("tier_level", [1, 3, 6])
def test_who_was_late_has_exactly_one_arrival_after_the_meeting(client, tier_level):
    uid, h = register(client)
    set_level(uid, tier_level)
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "detective", "case": "who_late"})
    keys = stored(s["id"])
    clues = [q for q in keys if q["type"] == "case_clue"]
    final = keys[-1]
    late_id = final["options"][final["item_id"]]["word_id"]
    meet = s["context"]["intro"]["zh"]
    assert clues and final["type"] == "case_deduce"

    def minutes(label):
        hh, mm = label.split(":")
        return int(hh) * 60 + int(mm)

    arrivals = {q["ask"]["who"]: minutes(q["options"][q["item_id"]]["label"]) for q in clues}
    assert len(arrivals) == len(final["options"])
    latest = max(arrivals, key=arrivals.get)
    assert latest == late_id and sorted(arrivals.values())[-2] < arrivals[late_id], meet


def test_who_has_it_ends_with_the_last_hand_over(client):
    uid, h = register(client)
    set_level(uid, 4)
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "detective", "case": "who_has"})
    keys = stored(s["id"])
    clues = [q for q in keys if q["type"] == "case_clue"]
    final = keys[-1]
    assert all(q["ask"]["kind"] == "when_gave" for q in clues)
    givers = {q["ask"]["who"] for q in clues}
    holders = [o["word_id"] for o in final["options"]]
    # Everyone hands it on except the last holder, who is the answer.
    assert set(holders) - givers == {final["options"][final["item_id"]]["word_id"]}
    # The latest hand-over is the one that reached the answer.
    last = max(clues, key=lambda q: q["options"][q["item_id"]]["label"].zfill(5))
    assert final["options"][final["item_id"]]["zh"] in last["clue"]["zh"]
    q = next(x for x in s["questions"] if x["type"] == "case_clue")
    assert q["prompt"]["ask"]["kind"] == "when_gave" and q["prompt"]["ask"]["who"]


def test_new_structures_build_without_repeated_options(client):
    uid, _ = register(client)
    with SessionLocal() as db:
        user = db.get(models.User, uid)
        for seed in range(6):
            for case in ("who_late", "who_has"):
                qs = detective.build_questions(db, user, case, 1, random.Random(seed), None)
                final = qs[-1]
                labels = [o["zh"] for o in final["options"]]
                assert len(labels) == len(set(labels)), labels
                for q in qs:
                    if q["type"] == "case_clue":
                        opts = [o.get("label") or o.get("zh") for o in q["options"]]
                        assert len(opts) == len(set(opts)) >= 2, opts
