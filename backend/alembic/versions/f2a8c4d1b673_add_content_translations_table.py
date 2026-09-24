"""add content_translations table

Revision ID: f2a8c4d1b673
Revises: d3f1a9b7c412
Create Date: 2026-09-25 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2a8c4d1b673'
down_revision: Union[str, Sequence[str], None] = 'd3f1a9b7c412'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'content_translations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content_type', sa.String(length=40), nullable=False),
        sa.Column('content_key', sa.String(length=40), nullable=False),
        sa.Column('field', sa.String(length=40), nullable=False),
        sa.Column('locale', sa.String(length=5), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('content_type', 'content_key', 'field', 'locale', name='uq_content_translation'),
    )
    op.create_index(op.f('ix_content_translations_content_type'), 'content_translations', ['content_type'], unique=False)
    op.create_index(op.f('ix_content_translations_content_key'), 'content_translations', ['content_key'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_content_translations_content_key'), table_name='content_translations')
    op.drop_index(op.f('ix_content_translations_content_type'), table_name='content_translations')
    op.drop_table('content_translations')
