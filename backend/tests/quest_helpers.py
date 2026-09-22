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
        words = call("GET", "/api/vocab", headers=H)
        for i in range(need):
            w = words[i % len(words)]
            call("POST", f"/api/vocab/{w['id']}/review", {"correct": True}, headers=H)
    elif kind == "lesson":
        lessons = call("GET", "/api/lessons", headers=H)
        lid = lessons[0]["id"]
        prog = call("GET", "/api/progress", headers=H)
        p = next((x for x in prog if x["lesson_id"] == lid), None)
        if p:
            call("PATCH", f"/api/progress/{p['id']}", {"status": "completed", "score": 100}, headers=H)
        else:
            created = call("POST", "/api/progress", {"lesson_id": lid, "status": "completed", "score": 100}, headers=H)
            call("PATCH", f"/api/progress/{created['id']}", {"status": "completed", "score": 100}, headers=H)
    elif kind == "case":
        call(
            "POST",
            "/api/world/scenarios/the-missing-bill/solve",
            {"conclusion": "顾客是对的，老王收了二十五元"},
            headers=H,
        )
    elif kind == "duel":
        d = call("POST", "/api/duels", {"opponent_username": "Buddy"}, headers=H)
        for i, qq in enumerate(d["questions"]):
            options = qq.get("options") or ["好"]
            call("POST", f"/api/duels/{d['id']}/answer", {"index": i, "answer": options[0], "response_time_ms": 800}, headers=H)
        call("POST", f"/api/duels/{d['id']}/finish", headers=H)


def complete_any(call, H, quests):
    """Drive the leader quest until one is completed; return the completed quest."""
    target = min(quests, key=lambda q: (q["target"] - (q["progress"] or 0)))
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