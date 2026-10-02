"""Deterministic daily-quest completion helpers for the frontend journey.

The daily trio is random (listening / vocab / lesson / case / duel / speaking),
so the journey drives whatever quest is present to completion by performing the
matching activity through the real HTTP API.
"""


def drive_quest(call, H, q):
    kind = q["quest_type"]
    need = max(0, q["target"] - (q["progress"] or 0))
    if kind in ("listening", "speaking"):
        for _ in range(need):
            call(
                "POST",
                "/api/voice/attempt",
                {
                    "spoken_text": "我要一碗牛肉面",
                    "prompt_text": "Say: I want a bowl of beef noodles",
                    "expected_keywords": ["牛肉面"],
                    "scenario_id": None,
                },
                headers=H,
            )
    elif kind == "vocab":
        # Only correct graded answers count; the self-graded
        # /api/vocab/{id}/review that used to feed this quest is gone.
        vocab_round(call, H)
    elif kind == "lesson":
        # A lesson completes only when its server-graded round is passed
        # (status="completed" via /api/progress is refused), so this is a real
        # attempt at the current lesson -- it counts only if it scores >= 70%.
        path = call("GET", "/api/lessons/path", headers=H)
        if path["current_lesson_id"] is None:
            return
        s = call("POST", "/api/practice/sessions", {"source": "lesson", "lesson_id": path["current_lesson_id"]}, headers=H)
        for i, q in enumerate(s["questions"]):
            call("POST", f"/api/practice/sessions/{s['id']}/answer", {"index": i, "choice_id": q["options"][0]["id"]}, headers=H)
        call("POST", f"/api/practice/sessions/{s['id']}/complete", headers=H)
    elif kind == "case":
        call(
            "POST",
            "/api/world/scenarios/the-missing-bill/solve",
            {"conclusion": "顾客是对的，老王收了二十五元"},
            headers=H,
        )
    elif kind == "duel":
        for _ in range(need):
            play_real_duel(call, H)


def vocab_round(call, H):
    """One real graded vocabulary round. A script can't see the answers, so
    it picks the first option; callers repeat until enough of them count."""
    s = call("POST", "/api/practice/sessions", {"source": "vocab", "hsk_level": 1, "size": 10}, headers=H)
    for i, q in enumerate(s["questions"]):
        call("POST", f"/api/practice/sessions/{s['id']}/answer", {"index": i, "choice_id": q["options"][0]["id"]}, headers=H)
    call("POST", f"/api/practice/sessions/{s['id']}/complete", headers=H)


def play_real_duel(call, H):
    """A complete real 1-vs-1 duel through the HTTP API: registers a fresh
    sparring account (duels are between two real users), challenges it,
    accepts as it, and both play every question (first option each)."""
    import uuid

    name = f"duelpartner_{uuid.uuid4().hex[:8]}"
    reg = call("POST", "/api/auth/register",
               {"username": name, "email": f"{name}@example.com", "password": "secret1"})
    P = {"Authorization": f"Bearer {reg['access_token']}"}
    d = call("POST", "/api/duels", {"opponent_id": reg["user"]["id"], "hsk_level": 1}, headers=H)
    call("POST", f"/api/duels/{d['id']}/accept", headers=P)
    for headers in (H, P):
        state = call("POST", f"/api/duels/{d['id']}/start", headers=headers)
        while state["current"] is not None:
            q = state["current"]
            state = call("POST", f"/api/duels/{d['id']}/answer",
                         {"index": q["index"], "choice_id": q["options"][0]["id"]}, headers=headers)["duel"]
    final = call("GET", f"/api/duels/{d['id']}", headers=H)
    assert final["status"] == "completed" and final["result"] is not None, final
    return final


def complete_any(call, H, quests):
    """Drive the leader quest until one is completed; return the completed quest.
    Lesson quests go last: a script cannot pass a lesson round on demand."""
    target = min(quests, key=lambda q: (q["quest_type"] == "lesson", q["target"] - (q["progress"] or 0)))
    for _ in range(30):
        drive_quest(call, H, target)
        refreshed = call("GET", "/api/quests/today", headers=H)
        target = next(q for q in refreshed if q["id"] == target["id"])
        if target["completed"]:
            return target
        target = min(refreshed, key=lambda q: (q["target"] - (q["progress"] or 0)))
    raise AssertionError("could not complete any daily quest")


def complete_known(call, H, quests):
    """Return first already-completed quest, else drive one to completion."""
    done = [q for q in quests if q["completed"]]
    if done:
        return done[0]
    return complete_any(call, H, quests)