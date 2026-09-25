"""seed real HSK 3.0 Hanzi data and the advanced-band HSKLevel row

Revision ID: 06e70a177b1d
Revises: d498a985f521
Create Date: 2026-09-25 13:55:00.000000

ROOT CAUSE this migration fixes: HSK level pages showing "no Hanzi" (e.g.
the Russian empty state "На этом уровне пока нет иероглифов.") on any
database that only ever received schema migrations. The real 3,000-row
Hanzi dataset (and the HSK 7-9 shared-advanced-band HSKLevel row that
levels 7/8/9 filtering depends on via app.services.hsk_band.
resolve_level_filter) were previously only ever inserted by manually
running backend/scripts/import_hsk30_curriculum.py against one developer's
local database -- that script reads backend/data_sources/hanzi_import_ready.json,
which is gitignored and therefore never reaches a fresh clone (CI,
another developer, or a deployed server that runs `alembic upgrade head`
but was never manually seeded). On such a database, `hanzi` has zero rows
for every level, and levels 7/8/9 additionally have no HSKLevel row at all
to filter against -- both produce an empty list for every single level,
not a partial/some-levels issue.

This migration is the fix: the same real, already-license-documented data
(see backend/data_sources/hsk30_README.md / krmanik_LICENSE for
provenance) is bundled at alembic/seed_data/hanzi_import_ready.json (now
version-controlled, not gitignored) and inserted here idempotently, so
`alembic upgrade head` alone reproduces the real data on any database --
dev, CI, or production -- instead of depending on a manual, undocumented,
non-repeatable script run. Safe to run against a database that already has
this data (like the developer's own): every insert is skipped if the
(level, character) pair already exists, so no duplicates and no changes
to existing user_hanzi progress.

Scope: only Hanzi + the HSK level rows Hanzi filtering depends on. The
equivalent vocabulary/grammar/lesson data has the exact same gap (also
only ever manually imported) but is out of scope for this specific
"missing Hanzi" bug fix -- see the final report.
"""
import json
import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '06e70a177b1d'
down_revision: Union[str, Sequence[str], None] = 'd498a985f521'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "seed_data")

# Real cumulative HSK 3.0 (2021) benchmark totals -- validated exactly
# against the elkmovie/hsk30 source lists (see build_hanzi_import.py).
REAL_VOCAB_TARGET_CUMULATIVE = {1: 500, 2: 1272, 3: 2245, 4: 3245, 5: 4316, 6: 5456, 7: 11092}

# Same (level, title, description, mastery_to_unlock_next) the app's own
# baseline seed (app/seed_data.py HSK_LEVELS) creates -- duplicated here,
# not imported, because Alembic migrations must not depend on application
# code that can change shape after this migration is written. Used only as
# a fallback if a level row doesn't already exist yet: app startup runs
# migrations BEFORE seed_all() (see app/main.py's lifespan handler), so on
# a truly first-ever startup against an empty database, HSK1-6 don't exist
# yet at the point this migration runs -- without this fallback, this
# migration would silently skip seeding Hanzi for those levels.
HSK_LEVEL_BASELINE = [
    (1, "HSK 1", "Foundation. Greetings, numbers, basic daily phrases.", 60),
    (2, "HSK 2", "Daily life, shopping, simple conversations.", 60),
    (3, "HSK 3", "Travel and work scenarios, richer grammar.", 65),
    (4, "HSK 4", "Opinions, news, longer exchanges.", 70),
    (5, "HSK 5", "Academic and professional Chinese.", 75),
    (6, "HSK 6", "Near-native fluency and cultural depth.", 100),
]

hsk_levels_t = sa.table(
    "hsk_levels",
    sa.column("id", sa.Integer),
    sa.column("level", sa.Integer),
    sa.column("title", sa.String),
    sa.column("description", sa.Text),
    sa.column("total_vocab_target", sa.Integer),
    sa.column("mastery_to_unlock_next", sa.Float),
    sa.column("is_advanced_band", sa.Boolean),
)
hanzi_t = sa.table(
    "hanzi",
    sa.column("id", sa.Integer),
    sa.column("hsk_level_id", sa.Integer),
    sa.column("character", sa.String),
    sa.column("pinyin", sa.String),
    sa.column("meaning", sa.String),
    sa.column("radical", sa.String),
    sa.column("decomposition", sa.String),
    sa.column("stroke_count", sa.Integer),
    sa.column("handwriting_tier", sa.String),
    sa.column("stroke_data", sa.JSON),
    sa.column("order_index", sa.Integer),
)


def upgrade() -> None:
    bind = op.get_bind()

    existing_levels = {row.level: row for row in bind.execute(sa.select(hsk_levels_t)).fetchall()}

    # 1. Ensure HSK 1-6 rows exist (normally the app's own baseline seed
    # creates these, but that runs AFTER migrations on a first-ever startup
    # -- see the HSK_LEVEL_BASELINE comment above) and carry the real HSK
    # 3.0 2021 total_vocab_target (not the old 2012-standard placeholder).
    for lvl_num, title, desc, mastery in HSK_LEVEL_BASELINE:
        target = REAL_VOCAB_TARGET_CUMULATIVE[lvl_num]
        row = existing_levels.get(lvl_num)
        if row is None:
            bind.execute(
                hsk_levels_t.insert().values(
                    level=lvl_num, title=title, description=desc,
                    total_vocab_target=target, mastery_to_unlock_next=mastery,
                    is_advanced_band=False,
                )
            )
        elif row.total_vocab_target != target:
            bind.execute(
                hsk_levels_t.update().where(hsk_levels_t.c.id == row.id).values(total_vocab_target=target)
            )
    existing_levels = {row.level: row for row in bind.execute(sa.select(hsk_levels_t)).fetchall()}

    # 2. Ensure the HSK 7-9 shared advanced-band row exists. Without this,
    # resolve_level_filter finds no band row at all for hsk_level=7/8/9 and
    # every query for those levels returns nothing.
    band = existing_levels.get(7)
    if band is None:
        bind.execute(
            hsk_levels_t.insert().values(
                level=7,
                title="HSK 7-9 (Advanced)",
                description=(
                    "Shared advanced vocabulary/Hanzi/grammar pool per the real HSK 3.0 "
                    "standard, which treats levels 7, 8 and 9 as one combined advanced "
                    "band rather than three independent official word lists."
                ),
                total_vocab_target=REAL_VOCAB_TARGET_CUMULATIVE[7],
                mastery_to_unlock_next=60.0,
                is_advanced_band=True,
            )
        )
        # Re-query rather than rely on inserted_primary_key: sa.table() is a
        # lightweight Core construct without full PK metadata, so that
        # attribute isn't reliably populated across drivers.
        band_id = bind.execute(
            sa.select(hsk_levels_t.c.id).where(hsk_levels_t.c.level == 7)
        ).scalar_one()
    else:
        band_id = band.id
        if not band.is_advanced_band:
            bind.execute(
                hsk_levels_t.update().where(hsk_levels_t.c.id == band.id).values(is_advanced_band=True)
            )

    level_id_by_num = {row.level: row.id for row in bind.execute(sa.select(hsk_levels_t)).fetchall()}
    level_id_by_num[7] = band_id

    # 3. Insert the real Hanzi rows, idempotently.
    existing_pairs = {
        (r.hsk_level_id, r.character)
        for r in bind.execute(sa.select(hanzi_t.c.hsk_level_id, hanzi_t.c.character)).fetchall()
    }

    data_path = os.path.join(SEED_DIR, "hanzi_import_ready.json")
    if not os.path.exists(data_path):
        # Nothing to seed from -- report honestly rather than fail the
        # whole migration chain (e.g. a shallow checkout missing this file).
        print(f"WARNING: {data_path} not found; skipping Hanzi data seed.")
        return

    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    rows_to_insert = []
    for lvl_key, entries in data.items():
        level_id = level_id_by_num.get(int(lvl_key))
        if level_id is None:
            continue
        for e in entries:
            key = (level_id, e["character"])
            if key in existing_pairs:
                continue
            rows_to_insert.append({
                "hsk_level_id": level_id,
                "character": e["character"],
                "pinyin": e["pinyin"],
                "meaning": (e["meaning"] or "")[:300] or None,
                "radical": e["radical"],
                "decomposition": e["decomposition"],
                "stroke_count": e["stroke_count"],
                "handwriting_tier": e["handwriting_tier"],
                "stroke_data": e["stroke_data"],
                "order_index": 0,
            })
            existing_pairs.add(key)

    CHUNK = 200
    for i in range(0, len(rows_to_insert), CHUNK):
        chunk = rows_to_insert[i:i + CHUNK]
        if chunk:
            bind.execute(hanzi_t.insert(), chunk)

    print(f"Seeded {len(rows_to_insert)} real Hanzi rows ({len(existing_pairs) - len(rows_to_insert)} already present).")


def downgrade() -> None:
    """Deliberately a no-op: this is real, license-documented curriculum
    data plus a real HSK 3.0 structural row, not scaffolding to tear back
    down. Deleting it here would also silently orphan any real user_hanzi
    progress recorded against these rows on whatever database this ran on."""
    pass
