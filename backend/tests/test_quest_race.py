"""Two requests of a learner's first visit of the day both create today's
quests (services/gamification.generate_daily_quests). The loser used to hit
uq_user_quest and answer 500 -- seen in a browser test of a new account.
The race is staged deterministically: the "other request" commits its
quests in its own session right before this one inserts."""

from datetime import date

from app import models
from app.database import SessionLocal
from app.services import gamification
from helpers import register, unique_name


def test_the_slower_request_reads_the_quests_the_faster_one_created(client, monkeypatch):
    uid, _ = register(client, unique_name("racer"))
    real_pick = gamification._pick_quest_templates

    def pick_while_another_request_wins(bias, k=3):
        chosen = real_pick(bias, k=k)
        with SessionLocal() as other:
            for qtype, title, desc, target, xp, coins, flavor in chosen:
                other.add(models.DailyQuest(user_id=uid, quest_date=date.today(), quest_type=qtype, title=title,
                                            description=desc, target=target, reward_xp=xp, reward_coins=coins,
                                            flavor=flavor))
            other.commit()
        return chosen

    monkeypatch.setattr(gamification, "_pick_quest_templates", pick_while_another_request_wins)
    with SessionLocal() as db:
        db.query(models.DailyQuest).filter_by(user_id=uid).delete()
        db.commit()
        quests = gamification.generate_daily_quests(db, db.get(models.User, uid))
        assert len(quests) == 3
        assert db.query(models.DailyQuest).filter_by(user_id=uid, quest_date=date.today()).count() == 3
