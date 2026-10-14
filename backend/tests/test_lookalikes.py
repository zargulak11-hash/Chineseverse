"""Look-alike characters (services/lookalikes.py): shown on Character DNA
and offered among a character question's wrong options, so 己 is practised
against 已 before the learner ever confuses them."""

from datetime import datetime, timedelta

import pytest

from app import models
from app.database import SessionLocal
from app.services import lookalikes
from helpers import expect, register, unique_name


def test_groups_are_symmetric_and_never_include_the_character_itself():
    assert lookalikes.lookalikes("己") == ["已"] and lookalikes.lookalikes("已") == ["己"]
    assert set(lookalikes.lookalikes("人")) == {"入", "八"}
    assert set(lookalikes.lookalikes("目")) == {"日", "曰", "且"}  # in two groups: both count
    for c, others in lookalikes._OF.items():
        assert c not in others
        assert all(c in lookalikes._OF[o] for o in others)
    assert lookalikes.lookalikes("龘") == []


@pytest.fixture
def learner(client):
    return register(client, unique_name("looker"))


def hanzi(char):
    with SessionLocal() as db:
        h = db.query(models.Hanzi).filter_by(character=char).order_by(models.Hanzi.hsk_level_id).first()
        lvl = db.get(models.HSKLevel, h.hsk_level_id).level
        return h.id, lvl


def test_character_dna_shows_what_it_looks_like(client, learner):
    _, h = learner
    dna = expect(client, "get", "/api/hanzi/character/己/dna", 200, headers=h)
    assert [x["char"] for x in dna["related"]["look_alike"]] == ["已"]
    assert dna["related"]["look_alike"][0]["pinyin"] and dna["related"]["look_alike"][0]["meaning"]


def test_a_character_question_offers_its_look_alike(client, learner):
    uid, h = learner
    ji, level = hanzi("己")
    yi, _ = hanzi("已")
    with SessionLocal() as db:
        # Due now, so the round starts with it; still "learning", so it is
        # asked as multiple choice (with options).
        db.add(models.UserHanzi(user_id=uid, hanzi_id=ji, status="learning", mastery=20.0, times_seen=2,
                                times_missed=0, next_review_at=datetime.utcnow() - timedelta(hours=1),
                                last_reviewed_at=datetime.utcnow() - timedelta(days=1)))
        db.commit()
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h,
               json={"source": "hanzi", "hsk_level": level, "size": 4})
    with SessionLocal() as db:
        qs = db.get(models.PracticeSession, s["id"]).questions
    q = next(q for q in qs if q["item_id"] == ji)
    assert yi in q["option_ids"], q
