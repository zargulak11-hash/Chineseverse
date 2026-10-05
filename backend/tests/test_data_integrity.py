"""Deleting a learner leaves no broken reference behind.

Production runs PostgreSQL, which enforces foreign keys; the test databases
are SQLite, which does not unless asked. So a user-owned table that neither
cascades from User nor is cleaned up by crud.delete_user_cascade_safe would
pass every other test and then fail an admin's delete in production (this
happened once, see that function's docstring). Two guards:

  * a rule over the schema itself: every foreign key to users.id is covered
    by a delete-orphan relationship on User or by delete_user_cascade_safe;
  * a real deletion, with SQLite's foreign-key enforcement switched on, of a
    learner who has genuine history across the app.
"""

import inspect

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import configure_mappers

from app import crud, database, models
from app.database import Base, SessionLocal
from helpers import bearer, expect, register, unique_name
from trace_helpers import trace


def user_foreign_keys():
    for table in Base.metadata.tables.values():
        for fk in table.foreign_keys:
            if fk.column.table.name == "users":
                yield table.name, fk.parent.name


def test_every_foreign_key_to_users_is_handled_on_deletion():
    configure_mappers()
    cascaded = {r.mapper.local_table.name for r in models.User.__mapper__.relationships
                if "delete-orphan" in r.cascade}
    cleanup = inspect.getsource(crud.delete_user_cascade_safe)
    handled_by_crud = {t.__tablename__ for t in (models.Follow, models.Notification, models.DuelAnswer,
                                                  models.Duel, models.PlacementAttempt, models.ActivityEvent)
                       if f"models.{t.__name__})" in cleanup}
    unhandled = sorted(f"{t}.{c}" for t, c in user_foreign_keys() if t not in cascaded | handled_by_crud)
    assert not unhandled, (
        f"{unhandled}: add a cascade=\"all, delete-orphan\" relationship on User or handle the table in "
        "crud.delete_user_cascade_safe, or deleting such a user fails on PostgreSQL")


@pytest.fixture
def enforced_foreign_keys(client):
    """SQLite with PRAGMA foreign_keys=ON on every connection, like PostgreSQL."""
    def on_connect(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    engine = database.engine
    engine.dispose()  # pooled connections were opened without the pragma
    event.listen(engine, "connect", on_connect)
    with engine.connect() as c:
        assert c.execute(text("PRAGMA foreign_keys")).scalar() == 1
    yield
    event.remove(engine, "connect", on_connect)
    engine.dispose()


def play_round(client, h, body, wrong_first=True):
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json=body)
    with SessionLocal() as db:
        keys = db.get(models.PracticeSession, s["id"]).questions
    for i, q in enumerate(keys):
        choice = next(o for o in q["option_ids"] if o != q["item_id"]) if (wrong_first and i == 0) else q["item_id"]
        expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h,
               json={"index": i, "choice_id": choice})
    expect(client, "post", f"/api/practice/sessions/{s['id']}/complete", 200, headers=h)


def test_deleting_a_learner_with_real_history_breaks_no_foreign_key(client, enforced_foreign_keys):
    admin_id, admin = register(client, unique_name("integrity_admin"))
    with SessionLocal() as db:
        db.get(models.User, admin_id).is_admin = True
        db.commit()
    vid, v = register(client, unique_name("victim"))
    rid, r = register(client, unique_name("rival"))

    # History across the app, made through the real endpoints.
    expect(client, "get", "/api/dashboard", 200, headers=v)                       # skills, streak
    expect(client, "post", "/api/me/animal", 200, headers=v, json={"animal_id": 1})  # companion bond
    expect(client, "post", "/api/onboarding/placement-test/start", 200, headers=v)   # placement attempt
    play_round(client, v, {"source": "vocab", "hsk_level": 1, "size": 4})         # vocab, mistake, activity
    lesson_id = expect(client, "get", "/api/lessons/path", 200, headers=v)["current_lesson_id"]
    expect(client, "post", "/api/progress", 201, headers=v, json={"lesson_id": lesson_id, "status": "in_progress"})
    with SessionLocal() as db:
        hid = db.query(models.Hanzi).filter(models.Hanzi.character == "好").first().id
    assert trace(client, v, hid).status_code == 200                                 # trace attempt, user_hanzi
    expect(client, "post", "/api/voice/attempt", 200, headers=v,
           json={"spoken_text": "我要一碗牛肉面", "expected_keywords": ["面"]})        # voice attempt
    expect(client, "get", "/api/quests/today", 200, headers=v)                      # daily quests
    missions = expect(client, "get", "/api/missions", 200, headers=v)
    expect(client, "post", f"/api/missions/{missions[0]['mission']['id']}/accept", 200, headers=v)
    expect(client, "put", "/api/stories/my-day/progress", 200, headers=v, json={"chapter": 1, "position": 1})
    expect(client, "post", f"/api/users/{rid}/follow", 201, headers=v)              # follow + notification
    expect(client, "post", f"/api/users/{vid}/follow", 201, headers=r)
    # A finished duel the victim won, with both players' answers stored.
    d = expect(client, "post", "/api/duels", 201, headers=v, json={"opponent_id": rid, "hsk_level": 1})
    expect(client, "post", f"/api/duels/{d['id']}/accept", 200, headers=r)
    with SessionLocal() as db:
        qs = db.get(models.Duel, d["id"]).question_data["questions"]
    for h, good in ((v, True), (r, False)):
        expect(client, "post", f"/api/duels/{d['id']}/start", 200, headers=h)
        for i, q in enumerate(qs):
            choice = q["item_id"] if good else next(o for o in q["option_ids"] if o != q["item_id"])
            expect(client, "post", f"/api/duels/{d['id']}/answer", 200, headers=h, json={"index": i, "choice_id": choice})
    with SessionLocal() as db:
        assert db.get(models.Duel, d["id"]).winner_id == vid
        present = {t for t, c in user_foreign_keys()
                   if db.execute(text(f"SELECT count(*) FROM {t} WHERE {c} = :u"), {"u": vid}).scalar()}
    # The history really spans the tables at risk.
    assert {"activity_events", "follows", "notifications", "placement_attempts", "duel_answers", "duels",
            "practice_sessions", "learning_mistakes", "hanzi_trace_attempts", "voice_attempts",
            "story_progress", "user_missions", "daily_quests", "progress"} <= present, present

    expect(client, "delete", f"/api/admin/users/{vid}", 204, headers=admin)

    with SessionLocal() as db:
        left = {f"{t}.{c}": n for t, c in user_foreign_keys()
                if (n := db.execute(text(f"SELECT count(*) FROM {t} WHERE {c} = :u"), {"u": vid}).scalar())}
        assert left == {}, left
        # The duel itself and the rival's side of it survive.
        assert db.get(models.Duel, d["id"]) is not None
        assert db.query(models.DuelAnswer).filter_by(duel_id=d["id"], user_id=rid).count() == len(qs)
    expect(client, "get", "/api/me", 200, headers=r)
    expect(client, "get", "/api/me", 401, headers=v)
