"""Migration e5a9c2d7b104 removes the Chinese "meanings" that were only the
word itself (喝 -> 喝) and leaves a real Chinese definition alone."""

import pytest
from alembic import command
from sqlalchemy import text

from app import database

pytestmark = pytest.mark.migration


def test_the_migration_drops_mirrors_but_not_a_real_definition(legacy_db):
    _url, cfg = legacy_db
    command.upgrade(cfg, "d4f8a1c3e925")
    with database.engine.begin() as c:
        level = c.execute(text("SELECT id FROM hsk_levels WHERE level = 1")).first()
        if level is None:
            c.execute(text("INSERT INTO hsk_levels (level, title) VALUES (1, 'HSK 1')"))
            level = c.execute(text("SELECT id FROM hsk_levels WHERE level = 1")).first()
        for wid, zh in ((91001, "喝"), (91002, "吃")):
            c.execute(text("INSERT INTO vocabulary_words (id, hsk_level_id, simplified, pinyin, meanings) "
                           "VALUES (:i, :l, :z, '', 'x')"), {"i": wid, "l": level[0], "z": zh})
        for key, body in (("91001", "喝"), ("91002", "把食物放进嘴里咽下")):
            c.execute(text("INSERT INTO content_translations (content_type, content_key, field, locale, text) "
                           "VALUES ('vocab_word', :k, 'meanings', 'zh', :t)"), {"k": key, "t": body})
    command.upgrade(cfg, "head")
    with database.engine.connect() as c:
        left = dict(c.execute(text("SELECT content_key, text FROM content_translations "
                                   "WHERE content_key IN ('91001', '91002')")).all())
    assert left == {"91002": "把食物放进嘴里咽下"}
