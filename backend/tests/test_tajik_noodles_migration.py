"""Migration e7b3c9d2f418 on a database seeded before the fix: the Tajik
"решаи гӯшти гов" ("root of beef") becomes "угрои гӯшти гов" (beef
noodles) where the seeded text is still there, an admin's own edit is left
alone, and downgrade/upgrade round-trips."""

import pytest
from alembic import command
from sqlalchemy import text

from app import database

pytestmark = pytest.mark.migration

BEFORE = "c3e5a7b9d102"
ROW = "INSERT INTO content_translations (content_type, content_key, field, locale, text) VALUES (:ct, :k, :f, 'tg', :t)"


def texts(c):
    return dict(c.execute(text("SELECT content_key, text FROM content_translations")).all())


def test_the_seeded_text_is_fixed_and_an_admin_edit_is_kept(legacy_db):
    _url, cfg = legacy_db
    command.upgrade(cfg, BEFORE)
    with database.engine.begin() as c:
        c.execute(text(ROW), {"ct": "vocab_word", "k": "1", "f": "meanings", "t": "решаи гӯшти гов"})
        c.execute(text(ROW), {"ct": "scenario", "k": "2", "f": "title", "t": "Фармоиши решаи гӯшти гов"})
        c.execute(text(ROW), {"ct": "mission", "k": "3", "f": "objective",
                              "t": "'Фармоиши реша бо гӯшти гов'-ро бо овоз анҷом диҳед."})
        # Edited by an admin since the seed: not the seeded text, so untouched.
        c.execute(text(ROW), {"ct": "dialogue", "k": "4", "f": "prompt", "t": "Гӯй: решаи гӯшти гов, лутфан."})
    command.upgrade(cfg, "head")
    with database.engine.begin() as c:
        got = texts(c)
    assert got["1"] == "угрои гӯшти гов" and got["2"] == "Фармоиши угрои гӯшти гов"
    assert got["3"] == "'Фармоиши угрои гӯшти гов'-ро бо овоз анҷом диҳед."
    assert got["4"] == "Гӯй: решаи гӯшти гов, лутфан."
    command.downgrade(cfg, BEFORE)
    with database.engine.begin() as c:
        assert texts(c)["1"] == "решаи гӯшти гов"
    command.upgrade(cfg, "head")
    with database.engine.begin() as c:
        assert texts(c)["1"] == "угрои гӯшти гов" and len(texts(c)) == 4
