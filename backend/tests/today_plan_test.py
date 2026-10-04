"""Today's plan is built from real records only.

Covers:
  * a brand-new learner gets ONE task (the first foundation step), nothing
    done, zero rounds/words/minutes -- no invented activity;
  * due reviews add a review task with the real count (not doubled -- the
    journey used to count every due item twice), and it is ticked off only
    after a review round was really finished today;
  * the weakest PRACTISED skill gets a task with the right place to practise;
    an unpractised skill never does;
  * today's counts come from today's rounds and reviewed words;
  * the assistant's context carries the same plan.
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/today.db"
os.environ["AI_PROVIDER"] = "offline"

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.routers import assistant as assistant_router  # noqa: E402


def expect(client, method, url, expected, **kwargs):
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == expected, f"{method.upper()} {url} -> {resp.status_code}: {resp.text}"
    return resp.json() if resp.content else None


def main():
    with TestClient(app) as client:
        data = expect(client, "post", "/api/auth/register", 201,
                      json={"username": "today_learner", "email": "today_learner@example.com", "password": "secret1"})
        uid, h = data["user"]["id"], {"Authorization": f"Bearer {data['access_token']}"}

        j = expect(client, "get", "/api/journey", 200, headers=h)
        today = j["today"]
        assert [t["key"] for t in today["tasks"]] == ["learn"], today
        assert today["tasks"][0]["next"]["key"] == "tones" and today["tasks"][0]["done"] is False
        assert (today["left"], today["rounds"], today["words"], today["minutes"]) == (1, 0, 0, 0), today
        print("[PASS] a new learner gets one task (the first foundation step), nothing done, no invented activity")

        # Three vocabulary items due for review.
        with SessionLocal() as db:
            words = db.query(models.VocabularyWord).limit(3).all()
            for w in words:
                db.add(models.UserVocabulary(user_id=uid, word_id=w.id, status="learning", mastery=40.0,
                                             next_review_at=datetime.utcnow() - timedelta(hours=1)))
            db.commit()
        j = expect(client, "get", "/api/journey", 200, headers=h)
        assert j["due_reviews"] == 3, j["due_reviews"]
        review = next(t for t in j["today"]["tasks"] if t["key"] == "review")
        assert review["count"] == 3 and review["done"] is False, review
        print("[PASS] due reviews add a review task with the real count (3, not 6)")

        s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "review", "size": 4})
        with SessionLocal() as db:
            stored = db.get(models.PracticeSession, s["id"]).questions
        for i, q in enumerate(stored):
            expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h,
                   json={"index": i, "choice_id": q["item_id"], "response_ms": 1500})
        expect(client, "post", f"/api/practice/sessions/{s['id']}/complete", 200, headers=h)
        j = expect(client, "get", "/api/journey", 200, headers=h)
        today = j["today"]
        review = next(t for t in today["tasks"] if t["key"] == "review")
        assert review["done"] is True and today["rounds"] == 1 and today["words"] >= 3, today
        print("[PASS] the review task is ticked off by a real finished review round; today's counts are real")

        # A practised weak skill gets a task; untouched skills never do.
        with SessionLocal() as db:
            for us in db.query(models.UserSkill).filter_by(user_id=uid).all():
                us.mastery = 0.0
            grammar = (db.query(models.UserSkill).join(models.Skill)
                       .filter(models.UserSkill.user_id == uid, models.Skill.code == "grammar").one())
            grammar.mastery = 22.0
            listening = (db.query(models.UserSkill).join(models.Skill)
                         .filter(models.UserSkill.user_id == uid, models.Skill.code == "listening").one())
            listening.mastery = 80.0
            db.commit()
        today = expect(client, "get", "/api/journey", 200, headers=h)["today"]
        weak = [t for t in today["tasks"] if t["key"] == "weak"]
        assert len(weak) == 1 and weak[0]["skill"] == "grammar" and weak[0]["mastery"] == 22, today["tasks"]
        assert weak[0]["to"].startswith("/practice?source=grammar"), weak[0]
        assert len(today["tasks"]) <= 4 and all("why" not in t for t in today["tasks"])
        print("[PASS] the weakest practised skill (grammar 22%) gets a grammar-practice task; unpractised ones don't")

        dash = expect(client, "get", "/api/dashboard", 200, headers=h)
        assert dash["dna"]["weak_areas"], dash["dna"]
        with SessionLocal() as db:
            user = db.get(models.User, uid)
            line = assistant_router._today_line(db, user, "en")
        assert "review the 0 item(s) due [done today]" in line and "grammar (22%)" in line and "today so far: 1" in line, line
        print("[PASS] the assistant is given the same real plan")
    print("ALL TODAY PLAN TESTS PASSED")


if __name__ == "__main__":
    main()
