"""Core CRUD and the authorization rules around it: public reads,
admin-only content and user-management writes (401 without a token, 403
for a learner), and progress rows that only ever belong to their owner."""

from types import SimpleNamespace

import pytest

from app import models
from app.database import SessionLocal
from helpers import bearer, expect_response as expect


@pytest.fixture(scope="module")
def people(client):
    """An admin and a regular learner. The admin registers normally and is
    promoted by a direct DB write -- exactly how a real deployment's admin
    is granted, never via a payload."""
    adminbot = expect(
        client, "post", "/api/auth/register", 201,
        json={"username": "adminbot", "email": "adminbot@example.com", "password": "secret1"},
    ).json()["user"]
    joe_reg = expect(
        client, "post", "/api/auth/register", 201,
        json={"username": "regularjoe", "email": "regularjoe@example.com", "password": "secret1"},
    ).json()
    with SessionLocal() as db:
        db.get(models.User, adminbot["id"]).is_admin = True
        db.commit()
    admin_login = expect(
        client, "post", "/api/auth/login", 200,
        json={"username": "adminbot", "password": "secret1"},
    ).json()
    panda = next(a for a in client.get("/api/animals").json() if a["name"] == "Panda")
    return SimpleNamespace(
        admin_id=adminbot["id"],
        admin=bearer(admin_login["access_token"]),
        joe_id=joe_reg["user"]["id"],
        joe=bearer(joe_reg["access_token"]),
        panda=panda,
    )


def test_health_and_seeded_animals(client):
    expect(client, "get", "/health", 200)
    animals = client.get("/api/animals").json()
    assert len(animals) == 20, animals
    assert any(a["name"] == "Panda" for a in animals)


def test_animal_crud_is_admin_only(client, people):
    admin, joe = people.admin, people.joe
    turtle = {"slug": "turtle", "name": "Turtle", "species": "Testudo", "description": "Slow but steady"}
    expect(client, "post", "/api/animals", 401, json=turtle)
    expect(client, "post", "/api/animals", 403, json=turtle, headers=joe)
    created = expect(client, "post", "/api/animals", 201, json=turtle, headers=admin).json()
    aid = created["id"]
    expect(client, "get", f"/api/animals/{aid}", 200)
    expect(client, "get", "/api/animals/999999", 404)
    expect(
        client, "put", f"/api/animals/{aid}", 200,
        json={"slug": "turtle", "name": "Turtle", "species": "Geochelone", "description": "Updated", "image_url": ""},
        headers=admin,
    )
    expect(client, "patch", f"/api/animals/{aid}", 403, json={"description": "x"}, headers=joe)
    patched = expect(
        client, "patch", f"/api/animals/{aid}", 200, json={"description": "Patched"}, headers=admin,
    ).json()
    assert patched["description"] == "Patched"
    expect(
        client, "post", "/api/animals", 409,
        json={"slug": "panda-2", "name": "Panda", "species": "x", "description": "dup"},
        headers=admin,
    )
    expect(client, "delete", f"/api/animals/{aid}", 401)
    expect(client, "delete", f"/api/animals/{aid}", 204, headers=admin)
    expect(client, "get", f"/api/animals/{aid}", 404)


def test_user_management_is_admin_only(client, people):
    admin, joe, panda = people.admin, people.joe, people.panda
    expect(client, "get", "/api/users", 401)  # no token
    expect(client, "get", "/api/users", 403, headers=joe)  # authenticated, not admin
    expect(client, "get", "/api/users", 200, headers=admin)
    expect(client, "get", f"/api/users/{people.admin_id}", 200, headers=admin)
    expect(client, "delete", f"/api/users/{people.joe_id}", 403, headers=joe)
    expect(client, "delete", f"/api/users/{people.admin_id}", 400, headers=admin)  # no self-delete

    alice_body = {"username": "alice", "email": "alice@example.com", "password": "secret1", "animal_id": panda["id"]}
    expect(client, "post", "/api/users", 401, json=alice_body)
    expect(client, "post", "/api/users", 403, json=alice_body, headers=joe)
    expect(client, "post", "/api/users", 422, json={"username": "ab", "email": "t@t.com", "password": "123456"}, headers=admin)
    expect(client, "post", "/api/users", 422, json={"username": "alice", "email": "not-an-email", "password": "123456"}, headers=admin)
    user = expect(client, "post", "/api/users", 201, json=alice_body, headers=admin).json()
    uid = user["id"]
    assert user["animal_id"] == panda["id"]
    assert "password_hash" not in user and "password" not in user
    expect(client, "post", "/api/users", 409, json={"username": "alice", "email": "other@example.com", "password": "secret1"}, headers=admin)
    expect(client, "post", "/api/users", 409, json={"username": "bob", "email": "alice@example.com", "password": "secret1"}, headers=admin)
    expect(client, "post", "/api/users", 404, json={"username": "carol", "email": "c@example.com", "password": "secret1", "animal_id": 999999}, headers=admin)
    expect(client, "get", f"/api/users/{uid}", 200, headers=admin)
    expect(client, "get", "/api/users/999999", 404, headers=admin)
    expect(client, "patch", f"/api/users/{uid}", 200, json={"animal_id": None}, headers=admin)
    put_user = expect(
        client, "put", f"/api/users/{uid}", 200,
        json={"username": "alice", "email": "alice@example.com", "password": "newsecret", "animal_id": panda["id"]},
        headers=admin,
    ).json()
    assert put_user["animal_id"] == panda["id"]

    # The password an admin set is the one that signs in.
    ok = expect(client, "post", "/api/auth/login", 200, json={"username": "alice", "password": "newsecret"}).json()
    assert ok["user"]["id"] == uid
    expect(client, "post", "/api/auth/login", 401, json={"username": "alice", "password": "wrongpw"})
    expect(client, "post", "/api/auth/login", 401, json={"username": "nobody", "password": "secret1"})

    expect(client, "delete", f"/api/users/{uid}", 204, headers=admin)
    expect(client, "get", f"/api/users/{uid}", 404, headers=admin)


def test_lesson_crud_is_admin_only(client, people):
    admin, joe = people.admin, people.joe
    baseline_hsk1 = len(client.get("/api/lessons", params={"hsk_level": 1}).json())
    hello = {"title": "Hello", "content": "你好", "hsk_level": 1, "order_index": 0}
    expect(client, "post", "/api/lessons", 401, json=hello)
    expect(client, "post", "/api/lessons", 403, json=hello, headers=joe)
    expect(client, "post", "/api/lessons", 422, json={"title": "A", "hsk_level": 9}, headers=admin)
    lesson = expect(client, "post", "/api/lessons", 201, json=hello, headers=admin).json()
    lid = lesson["id"]
    numbers = expect(client, "post", "/api/lessons", 201, json={"title": "Numbers", "content": "一二三", "hsk_level": 1, "order_index": 1}, headers=admin).json()
    family = expect(client, "post", "/api/lessons", 201, json={"title": "Family", "content": "家", "hsk_level": 2, "order_index": 0}, headers=admin).json()
    assert len(client.get("/api/lessons", params={"hsk_level": 1}).json()) == baseline_hsk1 + 2
    # A lesson's content is gated by the lesson path (test_lesson_path.py);
    # admins author lessons, so they may read any of them.
    expect(client, "get", f"/api/lessons/{lid}", 401)
    expect(client, "get", f"/api/lessons/{lid}", 200, headers=admin)
    expect(client, "get", "/api/lessons/999999", 404, headers=admin)
    result = expect(
        client, "put", f"/api/lessons/{lid}", 200,
        json={"title": "Hello!", "content": "你好", "hsk_level": 1, "order_index": 0, "lesson_type": "lesson"},
        headers=admin,
    ).json()
    assert result["title"] == "Hello!"
    expect(client, "patch", f"/api/lessons/{lid}", 200, json={"hsk_level": 2}, headers=admin)
    expect(client, "delete", f"/api/lessons/{lid}", 401)
    expect(client, "delete", f"/api/lessons/{lid}", 403, headers=joe)
    expect(client, "delete", f"/api/lessons/{lid}", 204, headers=admin)
    expect(client, "get", f"/api/lessons/{lid}", 404, headers=admin)
    for extra in (numbers, family):
        expect(client, "delete", f"/api/lessons/{extra['id']}", 204, headers=admin)


def test_progress_rows_belong_to_their_owner(client, people):
    admin, joe = people.admin, people.joe
    reg = expect(
        client, "post", "/api/auth/register", 201,
        json={"username": "progressor", "email": "progressor@example.com", "password": "secret1"},
    ).json()
    uid, mine = reg["user"]["id"], bearer(reg["access_token"])

    # Rows may only be written for a lesson the path has opened (the learner's
    # current one); a locked HSK 2 lesson is refused.
    current = client.get("/api/lessons/path", headers=mine).json()["current_lesson_id"]
    hsk2 = client.get("/api/lessons", params={"hsk_level": 2}).json()
    expect(client, "post", "/api/progress", 403, json={"lesson_id": hsk2[0]["id"], "status": "not_started"}, headers=mine)
    expect(client, "get", "/api/progress", 401)
    expect(client, "post", "/api/progress", 401, json={"lesson_id": current})
    prog = expect(
        client, "post", "/api/progress", 201,
        json={"lesson_id": current, "status": "not_started"}, headers=mine,
    ).json()
    pid = prog["id"]
    assert prog["user_id"] == uid
    expect(client, "post", "/api/progress", 409, json={"lesson_id": current, "status": "not_started"}, headers=mine)
    expect(client, "post", "/api/progress", 422, json={"lesson_id": current, "status": "bogus"}, headers=mine)
    expect(client, "post", "/api/progress", 403, json={"user_id": people.joe_id, "lesson_id": current}, headers=mine)
    expect(client, "post", "/api/progress", 404, json={"lesson_id": 999999}, headers=mine)
    expect(client, "post", "/api/progress", 422, json={"lesson_id": current, "status": "completed", "score": 150}, headers=mine)
    # Completion only comes from a passed practice round, never from the client.
    expect(client, "patch", f"/api/progress/{pid}", 403, json={"status": "completed", "score": 92}, headers=mine)
    # ...and neither does a score: it is the best graded round, not a client value.
    expect(client, "patch", f"/api/progress/{pid}", 403, json={"score": 100}, headers=mine)
    expect(client, "put", f"/api/progress/{pid}", 403, json={"status": "in_progress", "score": 100}, headers=mine)
    expect(client, "post", "/api/progress", 403, json={"lesson_id": hsk2[1]["id"], "status": "in_progress", "score": 100}, headers=mine)
    moved = expect(
        client, "patch", f"/api/progress/{pid}", 200,
        json={"status": "in_progress"}, headers=mine,
    ).json()
    assert moved["score"] is None
    assert moved["status"] == "in_progress"
    assert moved["completed_at"] is None
    # Another learner can neither see nor touch the row.
    assert client.get("/api/progress", headers=joe).json() == []
    expect(client, "get", f"/api/progress/{pid}", 404, headers=joe)
    expect(client, "patch", f"/api/progress/{pid}", 404, json={"status": "not_started"}, headers=joe)
    expect(client, "delete", f"/api/progress/{pid}", 404, headers=joe)
    expect(client, "get", f"/api/progress/user/{uid}", 403, headers=joe)
    assert len(expect(client, "get", f"/api/progress/user/{uid}", 200, headers=admin).json()) == 1
    assert len(client.get("/api/progress", headers=mine).json()) == 1
    expect(client, "get", f"/api/progress/{pid}", 200, headers=mine)
    expect(client, "get", "/api/progress/999999", 404, headers=mine)
    expect(client, "delete", f"/api/progress/{pid}", 204, headers=mine)
    expect(client, "get", f"/api/progress/{pid}", 404, headers=mine)


def test_deletion_safeguards(client, people):
    admin, panda = people.admin, people.panda
    owner = expect(
        client, "post", "/api/users", 201,
        json={"username": "pandafan", "email": "pandafan@example.com", "password": "secret1", "animal_id": panda["id"]},
        headers=admin,
    ).json()
    # A companion some learner has chosen can't be deleted from under them.
    expect(client, "delete", f"/api/animals/{panda['id']}", 400, headers=admin)
    # Learners (with or without rows of their own) are deleted cleanly.
    expect(client, "delete", f"/api/users/{people.joe_id}", 204, headers=admin)
    expect(client, "delete", f"/api/users/{owner['id']}", 204, headers=admin)
    expect(client, "get", f"/api/users/{people.joe_id}", 404, headers=admin)
