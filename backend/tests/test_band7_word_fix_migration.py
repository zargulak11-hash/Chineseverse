"""Three advanced-band words that carried one character's dictionary entry
(pinyin and meaning) get their own: migration b5e1d7a3c962 on a database
seeded before the fix, and the curriculum snapshot new databases are seeded
from. Every other word's pinyin matches its characters syllable for
syllable -- a check that would catch the next such import slip."""

import gzip
import json
import re
import unicodedata
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import text

from app import database, models
from app.database import SessionLocal

BEFORE = "d4a9c2e7f150"
SNAPSHOT = Path(__file__).resolve().parent.parent / "app" / "seed_content" / "curriculum.json.gz"
WORDS = {"得意扬扬": "dé yì yáng yáng", "火暴": "huǒ bào", "无可厚非": "wú kě hòu fēi"}


@pytest.mark.migration
def test_seeded_rows_are_fixed_and_an_admin_edit_is_kept(legacy_db):
    _url, cfg = legacy_db
    command.upgrade(cfg, BEFORE)
    with database.engine.begin() as c:
        band = c.execute(text("SELECT id FROM hsk_levels WHERE level = 7")).scalar()
        if band is None:
            c.execute(text("INSERT INTO hsk_levels (level, title) VALUES (7, 'HSK 7-9')"))
            band = c.execute(text("SELECT id FROM hsk_levels WHERE level = 7")).scalar()
        add = text(f"INSERT INTO vocabulary_words (hsk_level_id, simplified, pinyin, meanings) VALUES ({int(band)}, :w, :p, :m)")
        c.execute(add, {"w": "得意扬扬", "p": "yáng", "m": "ocean; vast; foreign"})
        c.execute(add, {"w": "无可厚非", "p": "fēi", "m": "to not be; not; wrong; incorrect; non-; un-; in-; de-"})
        # An admin already corrected this one their own way: left alone.
        c.execute(add, {"w": "火暴", "p": "huǒbào", "m": "hot-tempered"})
    command.upgrade(cfg, "head")
    rows = lambda c: {w: (p, m) for w, p, m in c.execute(text("SELECT simplified, pinyin, meanings FROM vocabulary_words"))}
    with database.engine.begin() as c:
        got = rows(c)
    assert got["得意扬扬"] == ("dé yì yáng yáng", "immensely pleased with oneself (idiom); proud; complacent")
    assert got["无可厚非"][0] == "wú kě hòu fēi"
    assert got["火暴"] == ("huǒbào", "hot-tempered")
    command.downgrade(cfg, BEFORE)
    with database.engine.begin() as c:
        assert rows(c)["得意扬扬"] == ("yáng", "ocean; vast; foreign")
    command.upgrade(cfg, "head")
    with database.engine.begin() as c:
        assert rows(c)["得意扬扬"][0] == "dé yì yáng yáng" and len(rows(c)) == 3


def test_new_databases_get_the_right_entries(client):
    with SessionLocal() as db:
        for word, pinyin in WORDS.items():
            row = db.query(models.VocabularyWord).filter_by(simplified=word).one()
            assert row.pinyin == pinyin, (word, row.pinyin)


# One pinyin syllable per character (an erhua "r" belongs to the syllable
# before it). Syllables are split on spaces/apostrophes first, then by the
# standard finals, so "xī'ān" and "xiān" both count right.
_SYL = re.compile(
    r"(?:zh|ch|sh|[bpmfdtnlgkhjqxrzcsyw])?(?:iang|iong|uang|ang|eng|ing|ong|ian|iao|uai|uan|van|ai|ei|ao|ou|"
    r"an|en|in|un|vn|ia|ie|iu|ua|uo|ui|ve|ue|er|a|e|i|o|u|v)(?![aeiouv])(?:r(?![aeiouv]))?"
)


def _syllables(pinyin):
    plain = "".join(c for c in unicodedata.normalize("NFD", pinyin.lower()) if not unicodedata.combining(c))
    out = []
    for chunk in re.split(r"[\s'’\-·,.，。!?！？…/]+", plain.replace("ü", "v")):
        if not chunk or chunk == "r":
            continue
        pos = 0
        while pos < len(chunk):
            m = _SYL.match(chunk, pos)
            if not m:
                return None
            out.append(m.group(0))
            pos = m.end()
    return out


def test_every_snapshot_word_has_one_syllable_per_character():
    vocab = json.loads(gzip.open(SNAPSHOT, "rt", encoding="utf-8").read())["vocab"]
    bad = []
    for v in vocab:
        chars = len(re.findall(r"[㐀-鿿]", v["simplified"]))
        syl = _syllables(v["pinyin"] or "")
        erhua = v["simplified"].endswith("儿") and syl is not None and len(syl) == chars - 1
        if syl is None or (chars and len(syl) != chars and not erhua):
            bad.append((v["level"], v["simplified"], v["pinyin"]))
    assert len(vocab) > 11000 and bad == [], bad[:20]
