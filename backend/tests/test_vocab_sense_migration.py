"""Migration c9e4f2a7b318 corrects vocabulary rows that taught the rare
reading of an everyday word (便宜 "convenient" -> piányi "cheap"), keeps
the row (and so learners' review records), leaves a row an admin already
corrected alone, and never touches a genuine polyphone entry."""

import gzip
import json

import pytest
from alembic import command
from sqlalchemy import text

from app import database
from app.services.curriculum import SNAPSHOT_PATH

pytestmark = pytest.mark.migration

BEFORE = "f6c2a8d4e197"


@pytest.fixture
def legacy_vocab(legacy_db):
    _url, cfg = legacy_db
    command.upgrade(cfg, BEFORE)
    with database.engine.begin() as c:
        level_id = {}
        for level in (1, 2, 6):  # earlier migrations may already have seeded the levels
            row = c.execute(text("SELECT id FROM hsk_levels WHERE level = :l"), {"l": level}).first()
            if row is None:
                c.execute(text("INSERT INTO hsk_levels (level, title) VALUES (:l, :t)"), {"l": level, "t": f"HSK {level}"})
                row = c.execute(text("SELECT id FROM hsk_levels WHERE level = :l"), {"l": level}).first()
            level_id[level] = row[0]
        rows = (
            (90010, 2, "便宜", "biàn yí", "convenient"),                         # wrong -> fixed
            (90011, 1, "告诉", "gào sù", "to tell (fixed by an admin)"),         # already corrected -> untouched
            (90012, 6, "看", "kān", "to look after; to take care of; to watch"),  # real polyphone -> untouched
        )
        for wid, level, zh, py, mean in rows:
            c.execute(text("INSERT INTO vocabulary_words (id, hsk_level_id, simplified, pinyin, meanings) "
                           "VALUES (:i, :l, :z, :p, :m)"), {"i": wid, "l": level_id[level], "z": zh, "p": py, "m": mean})
    command.upgrade(cfg, "head")
    return cfg


def test_wrong_readings_are_corrected_and_nothing_else_moves(legacy_vocab):
    with database.engine.connect() as c:
        got = {r.id: (r.pinyin, r.meanings) for r in c.execute(text("SELECT id, pinyin, meanings FROM vocabulary_words"))}
    assert got[90010] == ("pián yi", "cheap; inexpensive")
    assert got[90011] == ("gào sù", "to tell (fixed by an admin)")
    assert got[90012] == ("kān", "to look after; to take care of; to watch")


def test_the_snapshot_a_fresh_database_imports_carries_the_same_fix():
    snap = json.load(gzip.open(SNAPSHOT_PATH, "rt", encoding="utf-8"))
    by = {(v["level"], v["simplified"]): v for v in snap["vocab"]}
    assert by[(2, "便宜")]["meanings"].startswith("cheap") and by[(1, "告诉")]["meanings"].startswith("to tell")
    assert by[(3, "大夫")]["meanings"].startswith("doctor") and by[(3, "生意")]["meanings"].startswith("business")
    wrong = ("to press charges", "senior official", "life force", "old practice", "easy to get along with")
    assert not [v for v in snap["vocab"] if v["meanings"].startswith(wrong)]
