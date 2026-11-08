"""The models describe the schema the migrations build -- no more, no less.

A model column or index the migrations never created (or the reverse) is
invisible until something relies on it: three models declared a second
index on their primary key and one said a NOT NULL column was nullable
(found 2026-11-08 by comparing a freshly migrated PostgreSQL database).
This compares the migrated test database with the models the same way
`alembic check` would. Types are not compared: SQLite reports its own
type names, and CI's PostgreSQL job covers the real database."""

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app import database, models  # noqa: F401  (registers every table)
from app.database import Base

pytestmark = pytest.mark.migration


def test_migrated_schema_matches_the_models(client):
    with database.engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": False}), Base.metadata)
    # SQLite cannot name some unnamed/implicit objects the way PostgreSQL
    # does; only differences that are real on both are listed here.
    real = [d for d in diff if not (isinstance(d, tuple) and d[0] in ("remove_fk", "add_fk"))]
    assert real == [], "\n".join(map(str, real))
