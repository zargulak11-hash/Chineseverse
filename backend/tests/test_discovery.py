"""Detective Mode, Chinese Sound World, Character DNA and the Vocabulary
Ecosystem -- real content, real grading, and read-only views that never
write progress."""

import re

from app import models
from app.database import SessionLocal
from helpers import expect, register as register_only, unique_name


def register(client, name=None):
    uid, h = register_only(client, name or unique_name())
    expect(client, "get", "/api/dashboard", 200, headers=h)  # creates skill rows
    return uid, h


def stored(sid):
    with SessionLocal() as db:
        s = db.get(models.PracticeSession, sid)
        return s.questions, s.answers


def set_skill(uid, code, value):
    with SessionLocal() as db:
        for us in db.query(models.UserSkill).join(models.Skill).filter(models.UserSkill.user_id == uid):
            if code is None or us.skill.code == code:
                us.mastery = value
        db.commit()


def progress_counts(uid):
    with SessionLocal() as db:
        return tuple(db.query(m).filter_by(user_id=uid).count() for m in (
            models.UserVocabulary, models.UserHanzi, models.ActivityEvent, models.LearningMistake, models.PracticeSession))


def play(client, h, sid, questions, right=True, skip=()):
    qs, _ = stored(sid)
    for q in questions:
        if q["index"] in skip:
            continue
        good = qs[q["index"]]["item_id"]
        choice = good if right else next(o["id"] for o in q["options"] if o["id"] != good)
        expect(client, "post", f"/api/practice/sessions/{sid}/answer", 200, headers=h,
               json={"index": q["index"], "choice_id": choice, "response_ms": 3000})


def test_discovery_views_require_sign_in(client):
    for path in ("/api/detective/cases", "/api/sound-world/places", "/api/vocab/ecosystem", "/api/hanzi/character/学/dna"):
        expect(client, "get", path, 401)


def test_character_dna_shows_real_compounds_and_an_empty_history(client):
    uid, h = register(client)
    before = progress_counts(uid)
    dna = expect(client, "get", "/api/hanzi/character/学/dna", 200, headers=h)
    starts = [w["text"] for w in dna["tree"]["starts"]]
    ends = [w["text"] for w in dna["tree"]["ends"]]
    assert {"学习", "学生", "学校"} <= set(starts), starts
    assert "大学" in ends or "同学" in ends, ends
    assert dna["pinyin"] and dna["meaning"] and dna["words"], dna
    assert all("学" in w["text"] for w in dna["words"])
    assert dna["mine"]["status"] == "new" and dna["mine"]["first_seen_at"] is None and dna["mine"]["recent"] == []
    expect(client, "get", "/api/hanzi/character/ab/dna", 422, headers=h)
    expect(client, "get", "/api/hanzi/character/龘/dna", 404, headers=h)
    ru = expect(client, "get", "/api/hanzi/character/学/dna", 200, headers={**h, "X-Locale": "ru"})
    assert ru["words"][0]["meaning"] != dna["words"][0]["meaning"] or ru["meaning"] != dna["meaning"]
    with SessionLocal() as db:
        real = {w.simplified for w in db.query(models.VocabularyWord).filter(models.VocabularyWord.simplified.contains("学"))}
    assert set(w["text"] for w in dna["words"]) <= real  # nothing invented
    # Character DNA: real compounds tree (学习/学生/学校 ...), structure, localized, 404/422, empty learner history


def test_character_dna_shows_the_learners_real_practice(client):
    uid, h = register(client)
    with SessionLocal() as db:
        hz = db.query(models.Hanzi).filter_by(character="学").order_by(models.Hanzi.id).first()
        lvl = db.get(models.HSKLevel, hz.hsk_level_id).level
        others = [r.id for r in db.query(models.Hanzi).filter(models.Hanzi.hsk_level_id == hz.hsk_level_id,
                                                              models.Hanzi.id != hz.id).limit(3)]
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "hanzi", "hsk_level": lvl, "size": 4})
    with SessionLocal() as db:
        # A real round whose first question is about 学 (the round itself
        # is what a learner gets; only the item is pinned for the test).
        sess = db.get(models.PracticeSession, s["id"])
        qq = list(sess.questions)
        qq[0] = {**qq[0], "type": "char_to_meaning", "item_id": hz.id, "option_ids": [hz.id] + others}
        sess.questions = qq
        db.commit()
    expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h, json={"index": 0, "choice_id": hz.id})
    mine = expect(client, "get", "/api/hanzi/character/学/dna", 200, headers=h)["mine"]
    assert mine["practice_count"] >= 1 and mine["first_seen_at"] and mine["status"] != "new", mine
    assert mine["recent"][0]["correct"] is True and mine["next_review_at"]
    # Character DNA shows this learner's real practice: first met, recent answers, status, schedule


def test_ecosystem_is_a_real_capped_compound_network(client):
    uid, h = register(client)
    eco1 = expect(client, "get", "/api/vocab/ecosystem?center=学&hsk_max=1", 200, headers=h)
    eco3 = expect(client, "get", "/api/vocab/ecosystem?center=学&hsk_max=3", 200, headers=h)
    ids = {n["id"] for n in eco3["nodes"]}
    assert all(e["from"] in ids and e["to"] in ids for e in eco3["edges"])
    words1 = [n for n in eco1["nodes"] if n["kind"] == "word"]
    words3 = [n for n in eco3["nodes"] if n["kind"] == "word"]
    assert all(n["level"] <= 1 for n in words1) and all(n["level"] <= 3 for n in words3)
    assert eco3["stats"]["compounds_total"] >= eco1["stats"]["compounds_total"] >= 1
    assert len(eco3["nodes"]) <= 1 + 18 + 18
    assert eco3["nodes"][0]["center"] and eco3["nodes"][0]["text"] == "学"
    expect(client, "get", "/api/vocab/ecosystem?center=xyz", 422, headers=h)
    _, fresh = register(client)
    assert expect(client, "get", "/api/vocab/ecosystem", 200, headers=fresh)["center"] == "学"
    # Ecosystem: real compound network, HSK filter respected, capped, valid edges, default centre


def test_discovery_views_write_no_progress(client):
    uid, h = register(client)
    after_reads = progress_counts(uid)
    expect(client, "get", "/api/vocab/ecosystem?center=中", 200, headers=h)
    expect(client, "get", "/api/hanzi/character/中/dna", 200, headers=h)
    expect(client, "get", "/api/detective/cases", 200, headers=h)
    expect(client, "get", "/api/sound-world/places", 200, headers=h)
    assert progress_counts(uid) == after_reads, "read-only endpoints wrote progress"
    # DNA / ecosystem / case list / places are read-only (no fake progress)


def test_detective_cases_build_with_hidden_listening_clues(client):
    uid, h = register(client)
    cases = expect(client, "get", "/api/detective/cases", 200, headers=h)
    assert cases["profile"]["tier"] == "beginner" and cases["profile"]["suspects"] == 3
    assert [c["key"] for c in cases["cases"]] == ["who_took", "where_lost", "who_lies", "who_late", "who_has"]
    for key in ("who_took", "where_lost", "who_lies", "who_late", "who_has"):
        d = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "detective", "case": key})
        assert d["context"]["kind"] == "case" and d["context"]["title"]["zh"], d["context"]
        clues = [q for q in d["questions"] if q["type"] == "case_clue"]
        assert clues and d["questions"][-1]["type"] == "case_deduce"
        assert any(q["prompt"]["mode"] == "listen" for q in clues)
        for q in clues:
            assert "item_id" not in q and q["answer"] is None
            if q["prompt"]["mode"] == "listen":
                assert q["prompt"]["text"] is None  # heard before it can be read
    expect(client, "post", "/api/practice/sessions", 404, headers=h, json={"source": "detective", "case": "nope"})
    for _ in range(3):
        ru = expect(client, "post", "/api/practice/sessions", 201, headers={**h, "X-Locale": "ru"},
                    json={"source": "detective", "case": "who_took"})
        for q in ru["questions"]:
            if q["type"] == "case_clue" and ":" not in q["options"][0]["label"]:
                cyr = [bool(re.search("[а-яА-Я]", o["label"])) for o in q["options"]]
                assert all(cyr) or not any(cyr), [o["label"] for o in q["options"]]  # one language per question

    # five reusable case structures build; listening clues hidden until answered


def test_detective_misses_are_explained_reviewed_and_return_as_evidence(client):
    uid, h = register(client)
    d = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "detective", "case": "who_took"})
    dq, _ = stored(d["id"])
    clue = next(q for q in d["questions"] if q["type"] == "case_clue")
    wrong = next(o["id"] for o in clue["options"] if o["id"] != dq[clue["index"]]["item_id"])
    r = expect(client, "post", f"/api/practice/sessions/{d['id']}/answer", 200, headers=h,
               json={"index": clue["index"], "choice_id": wrong})
    assert not r["correct"] and r["card"]["gloss"] and r["card"]["pinyin"], r["card"]
    with SessionLocal() as db:
        w = db.get(models.VocabularyWord, dq[clue["index"]]["focus_id"])
        m = db.query(models.LearningMistake).filter_by(user_id=uid, reference=w.simplified).first()
        rec = db.query(models.UserVocabulary).filter_by(user_id=uid, word_id=w.id).first()
        assert m is not None and rec is not None and rec.next_review_at is not None
    play(client, h, d["id"], d["questions"], skip={clue["index"]})
    fin = expect(client, "post", f"/api/practice/sessions/{d['id']}/complete", 200, headers=h)
    assert fin["reaction"]["event"] == "detective_complete"
    with SessionLocal() as db:
        assert db.query(models.ActivityEvent).filter_by(user_id=uid, action_type="detective_case").count() == 1
    cases = expect(client, "get", "/api/detective/cases", 200, headers=h)
    assert next(c for c in cases["cases"] if c["key"] == "who_took")["solved"] == 1
    # a missed clue explains the Chinese (pinyin + gloss), records the mistake and schedules review; solve is logged

    # evidence notes from the learner's own mistakes
    d2 = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "detective", "case": "where_lost"})
    dq2, _ = stored(d2["id"])
    assert any(q.get("tag") == "evidence" for q in dq2), "mistake words should come back as evidence"
    # the learner's unresolved mistakes come back as evidence notes


def test_detective_difficulty_adapts_to_the_learner(client):
    _, h = register(client)
    cases = expect(client, "get", "/api/detective/cases", 200, headers=h)
    # adaptation: advanced reader-listener vs beginner
    aid, ah = register(client)
    set_skill(aid, None, 75.0)
    set_skill(aid, "listening", 95.0)
    prof = expect(client, "get", "/api/detective/cases", 200, headers=ah)["profile"]
    assert prof["tier"] == "advanced" and prof["suspects"] == 5 and prof["listen_share"] > cases["profile"]["listen_share"]
    a = expect(client, "post", "/api/practice/sessions", 201, headers=ah, json={"source": "detective", "case": "who_took"})
    aclues = [q for q in a["questions"] if q["type"] == "case_clue"]
    assert len(aclues) == 5 and len(a["questions"][-1]["options"]) == 5
    assert sum(q["prompt"]["mode"] == "listen" for q in aclues) >= 3
    assert any(":" in o["label"] for q in aclues for o in q["options"])  # red herring asks a time
    # difficulty adapts: advanced strong listener gets 5 suspects, a red herring, mostly audio clues


def test_sound_world_stage_one_is_slow_and_passing_opens_stage_two(client):
    sid_user, sh = register(client)
    places = expect(client, "get", "/api/sound-world/places", 200, headers=sh)
    assert places["unlocked"] == 1 and len(places["envs"]) == 7
    assert [s["unlocked"] for s in places["stages"]] == [True, False, False, False]
    expect(client, "post", "/api/practice/sessions", 403, headers=sh, json={"source": "sound", "env": "night_market", "stage": 2})
    expect(client, "post", "/api/practice/sessions", 404, headers=sh, json={"source": "sound", "env": "moon", "stage": 1})
    sw = expect(client, "post", "/api/practice/sessions", 201, headers=sh, json={"source": "sound", "env": "night_market", "stage": 1})
    types = {q["type"] for q in sw["questions"]}
    assert {"sound_identify", "sound_info", "sound_find", "sound_respond", "sound_conversation", "sound_memory"} <= types, types
    for q in sw["questions"]:
        for line in q["prompt"]["lines"]:
            assert line["text"] is None and line["speak"] and line["rate"] <= 0.7 * 1.25 + 0.01
    conv = next(q for q in sw["questions"] if q["type"] == "sound_conversation")
    assert len({l["speaker"] for l in conv["prompt"]["lines"]}) == 2
    listening0 = None
    with SessionLocal() as db:
        listening0 = db.query(models.UserSkill).join(models.Skill).filter(
            models.UserSkill.user_id == sid_user, models.Skill.code == "listening").first().mastery
    play(client, sh, sw["id"], sw["questions"])
    fin = expect(client, "post", f"/api/practice/sessions/{sw['id']}/complete", 200, headers=sh)
    assert fin["score"] == 100 and fin["reaction"]["event"] == "sound_complete"
    with SessionLocal() as db:
        l1 = db.query(models.UserSkill).join(models.Skill).filter(
            models.UserSkill.user_id == sid_user, models.Skill.code == "listening").first().mastery
        assert l1 > listening0
        assert db.query(models.ActivityEvent).filter_by(user_id=sid_user, action_type="sound_world").count() == 1
    places = expect(client, "get", "/api/sound-world/places", 200, headers=sh)
    assert places["unlocked"] == 2 and places["stages"][0]["best"] == 100
    sw2 = expect(client, "post", "/api/practice/sessions", 201, headers=sh, json={"source": "sound", "env": "train_station", "stage": 2})
    assert sw2["context"]["stage"] == 2 and sw2["questions"][0]["prompt"]["lines"][0]["rate"] > 0.7
    rq = next(q for q in sw2["questions"] if q["type"] == "sound_identify")
    r = expect(client, "post", f"/api/practice/sessions/{sw2['id']}/answer", 200, headers=sh,
               json={"index": rq["index"], "choice_id": stored(sw2["id"])[0][rq["index"]]["item_id"]})
    assert r["question"]["prompt"]["lines"][0]["text"], "transcript revealed after answering"
    zh = expect(client, "get", f"/api/practice/sessions/{sw2['id']}", 200, headers={**sh, "X-Locale": "ru"})
    assert zh["context"]["env"] == "train_station"
    # Sound World: 6 interaction kinds, 2 voices, slow stage 1; passing it (real score) opens stage 2; DNA + activity


def test_listening_dna_gives_a_head_start_capped_by_level(client):
    # head start from Learning DNA, capped by HSK level
    hid, hh = register(client)
    set_skill(hid, "listening", 75.0)
    st = expect(client, "get", "/api/sound-world/places", 200, headers=hh)
    assert st["unlocked"] == 2 and st["stages"][2]["locked_reason"] in ("level", "pass_previous"), st["stages"]
    set_skill(hid, None, 75.0)
    st = expect(client, "get", "/api/sound-world/places", 200, headers=hh)
    assert st["unlocked"] == 3 and st["stages"][3]["locked_reason"] == "pass_previous"
    # listening DNA gives a real head start, native speed still has to be earned
