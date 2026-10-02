"""Drawing helpers for Hanzi tracing tests.

A learner's trace is simulated the way a hand produces one: each stroke of
the character's real stroke data (Hanzi.stroke_data medians) is followed
with many intermediate pointer positions and a little jitter. Nothing here
invents stroke data -- it draws over the real data, and every stroke is
checked with the same matcher the server uses before it is used as a
"correct" stroke.
"""

import random
from datetime import datetime, timedelta

from app import models
from app.database import SessionLocal
from app.services.stroke_match import medians_of, stroke_matches


def hand_stroke(median, rng, jitter=6.0):
    pts = []
    for (x1, y1), (x2, y2) in zip(median, median[1:]):
        steps = rng.randint(4, 9)
        for s in range(steps):
            t = s / steps
            pts.append([round(x1 + (x2 - x1) * t + rng.gauss(0, jitter), 1),
                        round(y1 + (y2 - y1) * t + rng.gauss(0, jitter), 1)])
    pts.append([round(median[-1][0] + rng.gauss(0, jitter), 1), round(median[-1][1] + rng.gauss(0, jitter), 1)])
    return pts


def hand_trace(stroke_data, seed=1, mistakes=0):
    """Strokes of a real trace: `mistakes` misses (scribbles that match no
    stroke) before the first stroke, then every stroke in order."""
    rng = random.Random(seed)
    medians = medians_of(stroke_data)
    drawn = []
    for _ in range(mistakes):
        miss = [[900.0, 850.0], [930.0, 820.0], [960.0, 860.0]]
        assert not stroke_matches(miss, medians, 0)
        drawn.append({"points": miss, "matched": False})
    for i, med in enumerate(medians):
        for _ in range(20):
            pts = hand_stroke(med, rng)
            if stroke_matches([tuple(p) for p in pts], medians, i):
                break
        else:
            raise AssertionError(f"could not draw stroke {i + 1}")
        drawn.append({"points": pts, "matched": True})
    return drawn


def start(client, headers, hanzi_id, seconds_ago=30):
    r = client.post(f"/api/hanzi/{hanzi_id}/write/start", headers=headers)
    assert r.status_code == 201, r.text
    aid = r.json()["attempt_id"]
    # the learner spends a while drawing between "Try writing" and "Save"
    with SessionLocal() as db:
        a = db.get(models.HanziTraceAttempt, aid)
        a.started_at = datetime.utcnow() - timedelta(seconds=seconds_ago)
        db.commit()
    return aid


def stroke_data(hanzi_id):
    with SessionLocal() as db:
        return db.get(models.Hanzi, hanzi_id).stroke_data


def trace(client, headers, hanzi_id, mistakes=0, seed=1):
    aid = start(client, headers, hanzi_id)
    return client.post(f"/api/hanzi/{hanzi_id}/write", headers=headers,
                       json={"attempt_id": aid, "strokes": hand_trace(stroke_data(hanzi_id), seed, mistakes)})
