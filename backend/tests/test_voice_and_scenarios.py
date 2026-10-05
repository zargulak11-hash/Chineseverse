"""Voice practice history and the scenario catalogue: a learner's recordings
are theirs alone, and a scenario's dialogue is served only once its
location is open at the viewer's HSK level (anonymous viewers count as
HSK 1)."""

import pytest

from app import models
from app.database import SessionLocal
from helpers import expect, register, unique_name


def say(client, h, text):
    return expect(client, "post", "/api/voice/attempt", 200, headers=h,
                  json={"spoken_text": text, "expected_keywords": ["面"]})


def test_voice_history_is_the_learners_own_newest_first(client):
    _, h = register(client, unique_name("speaker"))
    _, other = register(client, unique_name("speaker_other"))
    first = say(client, h, "我要一碗面")["attempt"]["id"]
    second = say(client, h, "我要两碗牛肉面")["attempt"]["id"]
    say(client, other, "你好")
    history = expect(client, "get", "/api/voice/history", 200, headers=h)
    assert [a["id"] for a in history] == [second, first]
    assert all(a["spoken_text"] != "你好" for a in history)
    assert len(expect(client, "get", "/api/voice/history", 200, headers=other)) == 1
    expect(client, "get", "/api/voice/history", 401)


def test_voice_history_is_capped_at_the_latest_thirty(client):
    uid, h = register(client, unique_name("chatty"))
    with SessionLocal() as db:
        for i in range(35):
            db.add(models.VoiceAttempt(user_id=uid, spoken_text=f"第{i}句", transcript="", overall=0))
        db.commit()
    assert len(expect(client, "get", "/api/voice/history", 200, headers=h)) == 30


def test_the_scenario_catalogue_lists_every_scenario_and_filters_by_location(client):
    with SessionLocal() as db:
        total = db.query(models.Scenario).count()
        loc = db.query(models.Location).join(models.Scenario, models.Scenario.location_id == models.Location.id).first()
        at_loc = db.query(models.Scenario).filter_by(location_id=loc.id).count()
    every = expect(client, "get", "/api/world/scenarios", 200)
    assert len(every) == total
    by_loc = expect(client, "get", f"/api/world/scenarios?location_slug={loc.slug}", 200)
    assert len(by_loc) == at_loc and 0 < at_loc < total
    assert expect(client, "get", "/api/world/scenarios?location_slug=nowhere", 200) == []
    ru = expect(client, "get", "/api/world/scenarios", 200, headers={"X-Locale": "ru"})
    assert [s["slug"] for s in ru] == [s["slug"] for s in every]
    assert any(a["title"] != b["title"] for a, b in zip(ru, every)), "titles are localized"


@pytest.fixture(scope="module")
def locked_scenario(client):
    with SessionLocal() as db:
        sc = (db.query(models.Scenario).join(models.Location, models.Scenario.location_id == models.Location.id)
              .filter(models.Location.unlock_level > 1).first())
        assert sc is not None, "the seed has a scenario above HSK 1"
        return sc.slug


def test_a_scenario_above_the_viewers_level_is_refused(client, locked_scenario):
    _, h = register(client, unique_name("viewer"))
    expect(client, "get", f"/api/world/scenarios/{locked_scenario}", 403, headers=h)
    expect(client, "get", f"/api/world/scenarios/{locked_scenario}", 403)  # anonymous = HSK 1
    expect(client, "get", "/api/world/scenarios/ordering-noodles", 200)
    expect(client, "get", "/api/world/scenarios/no-such-scenario", 404)


def test_the_same_scenario_opens_once_the_learner_reaches_its_level(client, locked_scenario):
    uid, h = register(client, unique_name("climber"))
    expect(client, "get", "/api/dashboard", 200, headers=h)  # skill rows
    with SessionLocal() as db:
        for us in db.query(models.UserSkill).filter_by(user_id=uid):
            us.mastery = 6 * 15 + 0.5  # HSK 7 by Learning Compass
        db.commit()
    detail = expect(client, "get", f"/api/world/scenarios/{locked_scenario}", 200, headers=h)
    assert detail["slug"] == locked_scenario and detail["dialogues"]
