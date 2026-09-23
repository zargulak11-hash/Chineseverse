"""make total_xp and coins not null with server default

Revision ID: 3918c7437f2d
Revises: c6acf8197ca2
Create Date: 2026-09-22 19:23:26.638846

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3918c7437f2d'
down_revision: Union[str, Sequence[str], None] = 'c6acf8197ca2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Backfill any pre-existing NULLs before enforcing NOT NULL — rows
    # created before this column had a Python-side default (raw SQL, seed
    # scripts, or older code paths) could otherwise still hold NULL and
    # break this migration.
    op.execute("UPDATE users SET total_xp = 0 WHERE total_xp IS NULL")
    op.execute("UPDATE users SET coins = 0 WHERE coins IS NULL")
    # batch_alter_table (not a plain op.alter_column): SQLite has no real
    # ALTER COLUMN, so Alembic has to recreate the table under the hood.
    # On Postgres this still runs as a normal, non-batch ALTER COLUMN.
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('total_xp',
                   existing_type=sa.INTEGER(),
                   nullable=False,
                   server_default='0')
        batch_op.alter_column('coins',
                   existing_type=sa.INTEGER(),
                   nullable=False,
                   server_default='0')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('coins',
                   existing_type=sa.INTEGER(),
                   nullable=True,
                   server_default=None)
        batch_op.alter_column('total_xp',
                   existing_type=sa.INTEGER(),
                   nullable=True,
                   server_default=None)
