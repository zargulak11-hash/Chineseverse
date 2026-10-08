"""Learning Compass statuses (services/dna.skill_status): a strand never
practised is "untested", not "weak" -- per strand, also once the learner
has practised others -- and only practised strands are listed as weak."""

from app import models
from app.database import SessionLocal
from helpers import expect, register, unique_name


def test_untested_strands_are_not_called_weak(client):
    uid, h = register(client, unique_name("compass"))
    expect(client, "get", "/api/dna", 200, headers=h)  # creates the skill rows
    with SessionLocal() as db:
        for us in db.get(models.User, uid).user_skills:
            us.mastery = {"grammar": 22.0, "listening": 80.0, "vocabulary": 50.0}.get(us.skill.code, 0.0)
        db.commit()
    for url in ("/api/dna", "/api/dashboard"):
        body = expect(client, "get", url, 200, headers=h)
        dna = body.get("dna", body)
        status = {s["code"]: s["status"] for s in dna["skills"]}
        assert (status["grammar"], status["listening"], status["vocabulary"]) == ("weak", "strong", "developing")
        assert {c for c, st in status.items() if st == "untested"} == set(status) - {"grammar", "listening", "vocabulary"}
        assert dna["weak_areas"] == ["Grammar"] and dna["strong_areas"] == ["Listening"], (url, dna)
