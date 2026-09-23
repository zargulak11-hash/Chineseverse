"""backfill and enforce not null on daily_quests.claimed

Revision ID: 757a5095116a
Revises: 3918c7437f2d
Create Date: 2026-09-22 19:31:11.034022

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '757a5095116a'
down_revision: Union[str, Sequence[str], None] = '3918c7437f2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("UPDATE daily_quests SET claimed = false WHERE claimed IS NULL")
    with op.batch_alter_table('daily_quests') as batch_op:
        batch_op.alter_column('claimed',
                   existing_type=sa.BOOLEAN(),
                   nullable=False,
                   server_default='false')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('daily_quests') as batch_op:
        batch_op.alter_column('claimed',
                   existing_type=sa.BOOLEAN(),
                   nullable=True,
                   server_default=None)
