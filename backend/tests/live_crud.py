"""Full CRUD verification against a LIVE backend on http://localhost:8000.
Does not mutate customer data assumptions; expects a fresh database."""

import os

import httpx

BASE = os.environ.get("LIVE_CRUD_BASE", "http://127.0.0.1:8000")
c = httpx.Client(base_url=BASE, timeout=10)
passed = 0


def check(label, condition):
    global passed
    assert condition, f"FAILED: {label}"
    passed += 1
    print(f"  OK {label}")


def status(method, path, body=None):
    r = c.request(method, path, json=body)
    return r.status_code, r.json() if r.text else None


# ---------- ANIMALS (CRUD) ----------
print("== ANIMALS ==")
s, animals_before = status("GET", "/api/animals")
check("GET list (seeded)", s == 200)
baseline_animals = len(animals_before)
s, animal = status("POST", "/api/animals", {"slug": "test-critter", "name": "TestCritter", "species": "Panthera testa", "description": "Bold hunter"})
check("POST create -> 201", s == 201)
aid = animal["id"]
check("GET list grew by 1", len(status("GET", "/api/animals")[1]) == baseline_animals + 1)
s, a2 = status("PUT", f"/api/animals/{aid}", {"slug": "test-critter", "name": "TestCritter", "species": "Panthera testa altaica", "description": "Updated", "image_url": ""})
check("PUT update -> 200", s == 200 and a2["species"] == "Panthera testa altaica")
s, a3 = status("PATCH", f"/api/animals/{aid}", {"description": "Patched"})
check("PATCH -> 200 + field", s == 200 and a3["description"] == "Patched")
check("GET one -> 200", status("GET", f"/api/animals/{aid}")[0] == 200)
check("GET missing -> 404", status("GET", "/api/animals/999999")[0] == 404)
check("POST duplicate name -> 409", status("POST", "/api/animals", {"slug": "panda-2", "name": "Panda", "species": "x", "description": "d"})[0] == 409)
check("DELETE -> 204", status("DELETE", f"/api/animals/{aid}")[0] == 204)
check("GET deleted -> 404", status("GET", f"/api/animals/{aid}")[0] == 404)

# ---------- USERS (CRUD) ----------
print("== USERS ==")
check("POST invalid email -> 422", status("POST", "/api/users", {"username": "bob", "email": "bad", "password": "secret1"})[0] == 422)
check("POST short username -> 422", status("POST", "/api/users", {"username": "b", "email": "b@e.co", "password": "secret1"})[0] == 422)
s, user = status("POST", "/api/users", {"username": "bob", "email": "bob@example.com", "password": "secret1"})
check("POST create -> 201", s == 201)
uid = user["id"]
check("CREATE response hides password", "password" not in user and "password_hash" not in user)
s, _ = status("POST", "/api/users", {"username": "bob", "email": "x@y.z", "password": "secret1"})
check("POST duplicate username -> 409", s == 409)
s, _ = status("POST", "/api/users", {"username": "bob2", "email": "bob@example.com", "password": "secret1"})
check("POST duplicate email -> 409", s == 409)
check("GET one -> 200", status("GET", f"/api/users/{uid}")[0] == 200)
check("GET missing -> 404", status("GET", "/api/users/999999")[0] == 404)
s, u2 = status("PUT", f"/api/users/{uid}", {"username": "bob", "email": "bob@example.com", "password": "newsecret1"})
check("PUT update -> 200", s == 200)
s, login = status("POST", "/api/auth/login", {"username": "bob", "password": "newsecret1"})
check("Login with new password -> 200", s == 200)
s, u3 = status("PATCH", f"/api/users/{uid}", {"username": "robert"})
check("PATCH username -> 200", s == 200 and u3["username"] == "robert")
status("POST", "/api/users", {"username": "carol", "email": "carol@example.com", "password": "secret1"})
s, _ = status("PATCH", "/api/users/1", {"username": "carol"})
check("PATCH to other user's username -> 409", s == 409)
s, unchanged = status("PATCH", "/api/users/1", {"username": "robert"})
check("PATCH keeping own username -> 200", s == 200 and unchanged["username"] == "robert")

# ---------- LESSONS (CRUD) ----------
print("== LESSONS ==")
check("POST hsk_level 7 -> 422", status("POST", "/api/lessons", {"title": "X", "hsk_level": 7})[0] == 422)
s, l1 = status("POST", "/api/lessons", {"title": "Greet", "content": "\u4f60\u597d", "hsk_level": 1, "order_index": 0})
check("POST create -> 201", s == 201)
lid = l1["id"]
baseline_hsk2 = len(c.get("/api/lessons", params={"hsk_level": 2}).json())
status("POST", "/api/lessons", {"title": "Count", "content": "1,2,3", "hsk_level": 2, "order_index": 0})
s, lst = status("GET", "/api/lessons")
check("GET list -> 200", s == 200)
hmm = c.get("/api/lessons", params={"hsk_level": 2})
check("GET filter hsk_level=2 grew by 1", hmm.status_code == 200 and len(hmm.json()) == baseline_hsk2 + 1)
s, l2 = status("PUT", f"/api/lessons/{lid}", {"title": "Greet!", "content": "hello", "hsk_level": 1, "order_index": 5, "lesson_type": "lesson"})
check("PUT update -> 200", s == 200 and l2["order_index"] == 5)
s, l3 = status("PATCH", f"/api/lessons/{lid}", {"hsk_level": 2})
check("PATCH -> 200", s == 200 and l3["hsk_level"] == 2)
check("GET missing -> 404", status("GET", "/api/lessons/999999")[0] == 404)
check("DELETE -> 204", status("DELETE", f"/api/lessons/{lid}")[0] == 204)

# ---------- PROGRESS (CRUD) ----------
print("== PROGRESS ==")
lesson = c.get("/api/lessons").json()[0]
check("POST invalid status -> 422", status("POST", "/api/progress", {"user_id": uid, "lesson_id": lesson["id"], "status": "wat"})[0] == 422)
check("POST score >100 -> 422", status("POST", "/api/progress", {"user_id": uid, "lesson_id": lesson["id"], "status": "not_started", "score": 999})[0] == 422)
check("POST missing user -> 404", status("POST", "/api/progress", {"user_id": 999999, "lesson_id": lesson["id"], "status": "not_started"})[0] == 404)
s, p = status("POST", "/api/progress", {"user_id": uid, "lesson_id": lesson["id"], "status": "in_progress", "score": 50})
check("POST create -> 201", s == 201)
pid = p["id"]
check("POST duplicate pair -> 409", status("POST", "/api/progress", {"user_id": uid, "lesson_id": lesson["id"], "status": "completed"})[0] == 409)
s, p2 = status("PATCH", f"/api/progress/{pid}", {"status": "completed", "score": 95})
check("PATCH completed sets completed_at", s == 200 and p2["completed_at"] is not None)
s, p3 = status("PATCH", f"/api/progress/{pid}", {"status": "not_started"})
check("PATCH not_started clears completed_at", s == 200 and p3["score"] == 95 and p3["completed_at"] is None)
res = c.get("/api/progress", params={"user_id": uid})
check("GET filter by user -> 200", res.status_code == 200 and len(res.json()) == 1)
res = c.get(f"/api/progress/user/{uid}")
check("GET /user/{id} -> 200", res.status_code == 200 and len(res.json()) == 1)
check("GET one -> 200", status("GET", f"/api/progress/{pid}")[0] == 200)
check("GET missing -> 404", status("GET", "/api/progress/999999")[0] == 404)
check("DELETE -> 204", status("DELETE", f"/api/progress/{pid}")[0] == 204)

# ---------- AUTH ----------
print("== AUTH ==")
check("Login wrong password -> 401", status("POST", "/api/auth/login", {"username": "robert", "password": "wrong"})[0] == 401)
check("Login unknown user -> 401", status("POST", "/api/auth/login", {"username": "nope", "password": "x"})[0] == 401)

c.close()
print(f"\nLIVE CRUD: {passed} checks PASSED")