"""The Alembic revision graph itself, without a database.

Migrations run on every backend start (app/main.py), so a graph with two
heads -- two branches that each added a migration on the same parent -- makes
`alembic upgrade head` fail and the API not start, on the server, during a
deploy. This fails here first.
"""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_DIR = Path(__file__).resolve().parents[1]


def script():
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return ScriptDirectory.from_config(cfg)


def test_there_is_exactly_one_head():
    heads = script().get_heads()
    assert len(heads) == 1, f"more than one Alembic head (merge them first): {heads}"


def test_every_parent_exists_and_the_chain_reaches_the_first_migration():
    s = script()
    revisions = {r.revision: r for r in s.walk_revisions()}
    for rev in revisions.values():
        parents = rev.down_revision if isinstance(rev.down_revision, tuple) else (rev.down_revision,)
        for parent in parents:
            assert parent is None or parent in revisions, f"{rev.revision} names a missing parent {parent}"
    bases = [r for r in revisions.values() if r.down_revision is None]
    assert len(bases) == 1, f"expected one first migration, found {[b.revision for b in bases]}"


def test_this_releases_migrations_follow_production_in_order():
    # Production was at e7b3c9d2f418 when b8d1f4a6c3e9 (email_verified_at)
    # and d4a9c2e7f150 (sessions_revoked_at) were written on top of it.
    s = script()
    assert s.get_revision("b8d1f4a6c3e9").down_revision == "e7b3c9d2f418"
    assert s.get_revision("d4a9c2e7f150").down_revision == "b8d1f4a6c3e9"
    # walk_revisions goes from the head down; reversed it is upgrade order.
    upgrade_order = [r.revision for r in s.walk_revisions()][::-1]
    at = upgrade_order.index("e7b3c9d2f418")
    assert upgrade_order[at:at + 3] == ["e7b3c9d2f418", "b8d1f4a6c3e9", "d4a9c2e7f150"], upgrade_order[at:]
