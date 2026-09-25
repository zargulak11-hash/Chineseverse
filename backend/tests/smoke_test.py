import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/smoke.db"

from fastapi.testclient import TestClient

from app import models
from app.database import SessionLocal
from app.main import app


def expect(client, method, url, expected, **kwargs):
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == expected, (
        f"{method.upper()} {url} -> {resp.status_code} (expected {expected}): {resp.text}"
    )
    return resp


with TestClient(app) as client:
    # Health
    expect(client, "get", "/health", 200)

    # Animals: seeded on startup
    animals = client.get("/api/animals").json()
    assert len(animals) == 20, animals
    panda = next(a for a in animals if a["name"] == "Panda")

    # Animal CRUD
    created = expect(
        client,
        "post",
        "/api/animals",
        201,
        json={"slug": "turtle", "name": "Turtle", "species": "Testudo", "description": "Slow but steady"},
    ).json()
    aid = created["id"]
    expect(client, "get", f"/api/animals/{aid}", 200)
    expect(client, "get", "/api/animals/999999", 404)
    expect(
        client,
        "put",
        f"/api/animals/{aid}",
        200,
        json={"slug": "turtle", "name": "Turtle", "species": "Geochelone", "description": "Updated", "image_url": ""},
    )
    patched = expect(
        client,
        "patch",
        f"/api/animals/{aid}",
        200,
        json={"description": "Patched"},
    ).json()
    assert patched["description"] == "Patched"
    expect(
        client, "post", "/api/animals", 409,
        json={"slug": "panda-2", "name": "Panda", "species": "x", "description": "dup"},
    )
    expect(client, "delete", f"/api/animals/{aid}", 204)
    expect(client, "get", f"/api/animals/{aid}", 404)

    # User CRUD — GET/PUT/PATCH/DELETE on /api/users are admin-gated (see
    # app.routers.users / app.deps.require_admin), so this smoke test needs
    # its own admin account. Promoting via a direct DB write mirrors exactly
    # how a real deployment bootstraps its first admin (see
    # alembic/versions/a1c3f9e2d7b4_add_user_is_admin.py) — never through a
    # request payload.
    adminbot = expect(
        client, "post", "/api/users", 201,
        json={"username": "adminbot", "email": "adminbot@example.com", "password": "secret1"},
    ).json()
    regularjoe = expect(
        client, "post", "/api/users", 201,
        json={"username": "regularjoe", "email": "regularjoe@example.com", "password": "secret1"},
    ).json()
    with SessionLocal() as _db:
        _admin = _db.get(models.User, adminbot["id"])
        _admin.is_admin = True
        _db.commit()
    admin_login = expect(
        client, "post", "/api/auth/login", 200,
        json={"username": "adminbot", "password": "secret1"},
    ).json()
    admin_headers = {"Authorization": f"Bearer {admin_login['access_token']}"}
    joe_login = expect(
        client, "post", "/api/auth/login", 200,
        json={"username": "regularjoe", "password": "secret1"},
    ).json()
    joe_headers = {"Authorization": f"Bearer {joe_login['access_token']}"}

    expect(client, "get", "/api/users", 401)  # no token
    expect(client, "get", "/api/users", 403, headers=joe_headers)  # authenticated, not admin
    expect(client, "get", "/api/users", 200, headers=admin_headers)
    expect(client, "get", f"/api/users/{adminbot['id']}", 200, headers=admin_headers)
    expect(client, "delete", f"/api/users/{regularjoe['id']}", 403, headers=joe_headers)
    expect(client, "delete", f"/api/users/{adminbot['id']}", 400, headers=admin_headers)  # no self-delete
    expect(client, "delete", f"/api/users/{regularjoe['id']}", 204, headers=admin_headers)

    expect(client, "post", "/api/users", 422, json={"username": "ab", "email": "t@t.com", "password": "123456"})
    expect(client, "post", "/api/users", 422, json={"username": "alice", "email": "not-an-email", "password": "123456"})
    user = expect(
        client,
        "post",
        "/api/users",
        201,
        json={"username": "alice", "email": "alice@example.com", "password": "secret1", "animal_id": panda["id"]},
    ).json()
    uid = user["id"]
    assert user["animal_id"] == panda["id"]
    assert "password_hash" not in user and "password" not in user
    expect(client, "post", "/api/users", 409, json={"username": "alice", "email": "other@example.com", "password": "secret1"})
    expect(client, "post", "/api/users", 409, json={"username": "bob", "email": "alice@example.com", "password": "secret1"})
    expect(client, "post", "/api/users", 404, json={"username": "carol", "email": "c@example.com", "password": "secret1", "animal_id": 999999})
    expect(client, "get", f"/api/users/{uid}", 200, headers=admin_headers)
    expect(client, "get", "/api/users/999999", 404, headers=admin_headers)
    expect(
        client,
        "patch",
        f"/api/users/{uid}",
        200,
        json={"animal_id": None},
        headers=admin_headers,
    )
    put_user = expect(
        client,
        "put",
        f"/api/users/{uid}",
        200,
        json={"username": "alice", "email": "alice@example.com", "password": "newsecret", "animal_id": panda["id"]},
        headers=admin_headers,
    ).json()
    assert put_user["animal_id"] == panda["id"]

    # Login
    ok = expect(client, "post", "/api/auth/login", 200, json={"username": "alice", "password": "newsecret"}).json()
    assert ok["user"]["id"] == uid
    expect(client, "post", "/api/auth/login", 401, json={"username": "alice", "password": "wrongpw"})
    expect(client, "post", "/api/auth/login", 401, json={"username": "nobody", "password": "secret1"})

    # Lesson CRUD + validation
    baseline_hsk1 = len(client.get("/api/lessons", params={"hsk_level": 1}).json())
    expect(client, "post", "/api/lessons", 422, json={"title": "A", "hsk_level": 9})
    lesson = expect(
        client,
        "post",
        "/api/lessons",
        201,
        json={"title": "Hello", "content": "你好", "hsk_level": 1, "order_index": 0},
    ).json()
    lid = lesson["id"]
    expect(client, "post", "/api/lessons", 201, json={"title": "Numbers", "content": "一二三", "hsk_level": 1, "order_index": 1})
    expect(client, "post", "/api/lessons", 201, json={"title": "Family", "content": "家", "hsk_level": 2, "order_index": 0})
    assert len(client.get("/api/lessons", params={"hsk_level": 1}).json()) == baseline_hsk1 + 2
    expect(client, "get", f"/api/lessons/{lid}", 200)
    expect(client, "get", "/api/lessons/999999", 404)
    result = expect(
        client,
        "put",
        f"/api/lessons/{lid}",
        200,
        json={"title": "Hello!", "content": "你好", "hsk_level": 1, "order_index": 0, "lesson_type": "lesson"},
    ).json()
    assert result["title"] == "Hello!"
    expect(client, "patch", f"/api/lessons/{lid}", 200, json={"hsk_level": 2})
    expect(client, "delete", f"/api/lessons/{lid}", 204)
    expect(client, "get", f"/api/lessons/{lid}", 404)

    # Progress CRUD + relationships + validation
    lesson2 = client.get("/api/lessons", params={"hsk_level": 2}).json()[0]
    prog = expect(
        client,
        "post",
        "/api/progress",
        201,
        json={"user_id": uid, "lesson_id": lesson2["id"], "status": "not_started"},
    ).json()
    pid = prog["id"]
    expect(client, "post", "/api/progress", 409, json={"user_id": uid, "lesson_id": lesson2["id"], "status": "not_started"})
    expect(client, "post", "/api/progress", 422, json={"user_id": uid, "lesson_id": lesson2["id"], "status": "bogus"})
    expect(client, "post", "/api/progress", 404, json={"user_id": 999999, "lesson_id": lesson2["id"], "status": "not_started"})
    expect(client, "post", "/api/progress", 422, json={"user_id": uid, "lesson_id": lesson2["id"], "status": "completed", "score": 150})
    done = expect(
        client,
        "patch",
        f"/api/progress/{pid}",
        200,
        json={"status": "completed", "score": 92},
    ).json()
    assert done["status"] == "completed"
    assert done["completed_at"] is not None
    user_progress = client.get(f"/api/progress/user/{uid}").json()
    assert len(user_progress) == 1
    assert client.get("/api/progress", params={"user_id": uid}).json()
    expect(client, "get", f"/api/progress/{pid}", 200)
    expect(client, "get", "/api/progress/999999", 404)
    expect(client, "delete", f"/api/progress/{pid}", 204)
    expect(client, "get", f"/api/progress/{pid}", 404)

    # Deletion safeguards
    expect(client, "delete", f"/api/animals/{panda['id']}", 400)
    expect(client, "delete", f"/api/users/{uid}", 204, headers=admin_headers)

print("ALL SMOKE TESTS PASSED")