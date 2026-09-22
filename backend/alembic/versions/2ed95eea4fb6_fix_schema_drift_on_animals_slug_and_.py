"""fix schema drift on animals slug and lessons hsk_level_id

Revision ID: 2ed95eea4fb6
Revises: 9ff480a197c2
Create Date: 2026-09-22 14:31:08.688176

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2ed95eea4fb6'
down_revision: Union[str, Sequence[str], None] = '9ff480a197c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Bring a pre-Alembic database's schema in line with the models.

    An earlier version of this app used an ad-hoc ALTER TABLE patch list at
    startup (main.py) instead of real migrations. It added the `slug` and
    `hsk_level_id` columns but never enforced the NOT NULL / UNIQUE /
    foreign key that the SQLAlchemy models have always declared, so the
    live Postgres schema quietly drifted from the models.

    This only matters for that one pre-existing database — a fresh install
    already gets everything right from the baseline migration, since it
    creates these tables directly from the current models. So this is
    Postgres-only and fully idempotent (safe to run against a database that
    already has these, which is exactly what a fresh install looks like).
    """
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("ALTER TABLE animals ALTER COLUMN slug SET NOT NULL")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_animals_slug ON animals (slug)")
    op.execute("ALTER TABLE lessons ALTER COLUMN order_index DROP NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_lessons_hsk_level_id ON lessons (hsk_level_id)")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_lessons_hsk_level_id_hsk_levels'
            ) THEN
                ALTER TABLE lessons ADD CONSTRAINT fk_lessons_hsk_level_id_hsk_levels
                    FOREIGN KEY (hsk_level_id) REFERENCES hsk_levels(id);
            END IF;
        END$$;
        """
    )


def downgrade() -> None:
    """No-op: this migration only corrects historical drift, it doesn't
    introduce anything a downgrade should remove."""
    pass
