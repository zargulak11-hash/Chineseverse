"""The skill check (services/diagnostic.py): a graded round with a few
questions per skill at a level, a result read from the learner's own stored
answers, and the next step that follows the weakest skill until it is
practised."""

from app import models
from app.database import SessionLocal
from app.services import diagnostic
from helpers import expect, register, unique_name

ROUNDS = "/api/practice/sessions"


def stored(sid):
    with SessionLocal() as db:
        return db.get(models.PracticeSession, sid).questions


def placed(client, level=3):
    """A learner past the beginner foundation, as the placement test leaves them."""
    uid, h = register(client, unique_name("diag"))
    expect(client, "get", "/api/journey", 200, headers=h)  # creates the skill rows
    with SessionLocal() as db:
        for s in db.get(models.User, uid).user_skills:
            s.mastery = level * 15 - 0.5
        db.commit()
    return uid, h


def answer(client, h, s, right_skills):
    """Answer every question: right for the skills listed, wrong otherwise."""
    keys = stored(s["id"])
    for q in s["questions"]:
        k = keys[q["index"]]
        good = k["skill"] in right_skills
        if k["type"] == "type_word":
            with SessionLocal() as db:
                word = db.get(models.VocabularyWord, k["item_id"]).simplified
            body = {"index": q["index"], "text": word if good else "", "response_ms": 3000}
        else:
            choice = k["item_id"] if good else next(o for o in k["option_ids"] if o != k["item_id"])
            body = {"index": q["index"], "choice_id": choice, "response_ms": 3000}
        r = expect(client, "post", f"{ROUNDS}/{s['id']}/answer", 200, headers=h, json=body)
        assert r["correct"] == good, (k["type"], r)
    return expect(client, "post", f"{ROUNDS}/{s['id']}/complete", 200, headers=h)


def test_the_check_asks_every_skill_at_the_chosen_level(client):
    _, h = placed(client)
    s = expect(client, "post", ROUNDS, 201, headers=h, json={"source": "diagnostic", "hsk_level": 3})
    keys = stored(s["id"])
    by_skill = {}
    for k in keys:
        by_skill.setdefault(k["skill"], []).append(k)
    assert set(by_skill) == set(diagnostic.SKILLS)
    assert all(len(v) == diagnostic.PER_SKILL for v in by_skill.values())
    assert len({(k["item_type"], k["item_id"]) for k in keys}) == len(keys), "no item asked twice"
    with SessionLocal() as db:
        level_ids = {l.id for l in db.query(models.HSKLevel).filter_by(level=3)}
        for k in keys:
            model = {"vocab": models.VocabularyWord, "hanzi": models.Hanzi, "grammar": models.GrammarTopic}[k["item_type"]]
            assert db.get(model, k["item_id"]).hsk_level_id in level_ids
    # Tones are heard; nothing in the payload gives an answer away.
    for q, k in zip(s["questions"], keys):
        assert "item_id" not in q and "skill" not in q
        if k["type"] == "char_to_pinyin":
            assert q["prompt"]["speak"] == q["prompt"]["text"]
    assert s["context"] == {"kind": "diagnostic", "level": 3}


def test_the_level_defaults_to_the_learners_own(client):
    _, h = placed(client, level=2)
    s = expect(client, "post", ROUNDS, 201, headers=h, json={"source": "diagnostic"})
    assert s["context"]["level"] == 2


def test_the_result_names_the_weak_skills_and_the_next_step_follows(client):
    uid, h = placed(client)
    s = expect(client, "post", ROUNDS, 201, headers=h, json={"source": "diagnostic", "hsk_level": 3})
    summary = answer(client, h, s, right_skills={"vocabulary", "reading", "grammar", "memory"})
    skills = {x["skill"]: x for x in summary["skills"]}
    assert skills["listening"]["weak"] and skills["tones"]["weak"]
    assert not skills["vocabulary"]["weak"] and skills["vocabulary"]["correct"] == 2
    assert skills["listening"]["to"] == "/sound-world"

    j = expect(client, "get", "/api/journey", 200, headers=h)
    assert [w["skill"] for w in j["skill_check"]["weak"]] == ["listening", "tones"]
    nxt = j["next"]
    assert nxt["kind"] == "checkskill" and nxt["skill"] == "listening" and (nxt["correct"], nxt["total"]) == (0, 2)

    # Practising the skill (a Sound World pronunciation round counts for
    # listening and tones) moves the next step on.
    p = expect(client, "post", ROUNDS, 201, headers=h, json={"source": "pronunciation", "env": "tones"})
    q0 = p["questions"][0]
    expect(client, "post", f"{ROUNDS}/{p['id']}/answer", 200, headers=h,
           json={"index": q0["index"], "choice_id": stored(p["id"])[0]["item_id"]})
    expect(client, "post", f"{ROUNDS}/{p['id']}/complete", 200, headers=h)
    j = expect(client, "get", "/api/journey", 200, headers=h)
    assert j["skill_check"]["weak"] == [] and j["next"]["kind"] != "checkskill"
    # The check's own record stays (it is read, not rewritten).
    assert {x["skill"]: x["correct"] for x in j["skill_check"]["skills"]}["listening"] == 0


def test_a_check_with_everything_right_leaves_nothing_weak(client):
    _, h = placed(client)
    s = expect(client, "post", ROUNDS, 201, headers=h, json={"source": "diagnostic", "hsk_level": 3})
    summary = answer(client, h, s, right_skills=set(diagnostic.SKILLS))
    assert all(not x["weak"] and x["correct"] == x["total"] for x in summary["skills"])
    j = expect(client, "get", "/api/journey", 200, headers=h)
    assert j["skill_check"]["weak"] == [] and j["next"]["kind"] != "checkskill"


def test_a_check_is_graded_like_any_round(client):
    uid, h = placed(client)
    s = expect(client, "post", ROUNDS, 201, headers=h, json={"source": "diagnostic", "hsk_level": 3})
    answer(client, h, s, right_skills=set())
    with SessionLocal() as db:
        assert db.query(models.LearningMistake).filter_by(user_id=uid).count() >= 6
        assert db.query(models.ActivityEvent).filter_by(user_id=uid, action_type="skill_check").count() == 1
    # Another learner can't read it.
    _, other = placed(client)
    expect(client, "get", f"{ROUNDS}/{s['id']}", 404, headers=other)


def test_a_bad_level_is_refused(client):
    _, h = placed(client)
    expect(client, "post", ROUNDS, 422, headers=h, json={"source": "diagnostic", "hsk_level": 12})
