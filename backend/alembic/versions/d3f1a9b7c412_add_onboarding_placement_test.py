"""add onboarding placement test

Revision ID: d3f1a9b7c412
Revises: a1ebd40c9c57
Create Date: 2026-09-23 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3f1a9b7c412'
down_revision: Union[str, Sequence[str], None] = 'a1ebd40c9c57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('user_profiles', sa.Column('learning_motivation', sa.String(length=30), nullable=True))
    op.add_column('user_profiles', sa.Column('learning_motivation_other', sa.String(length=200), nullable=True))
    op.add_column('user_profiles', sa.Column('discovery_source', sa.String(length=30), nullable=True))
    op.add_column('user_profiles', sa.Column('discovery_source_other', sa.String(length=200), nullable=True))
    op.add_column(
        'user_profiles',
        sa.Column('onboarding_completed', sa.Boolean(), nullable=False, server_default='false'),
    )

    op.create_table(
        'placement_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='active'),
        sa.Column('question_data', sa.JSON(), nullable=True),
        sa.Column('correct_count', sa.Integer(), nullable=True),
        sa.Column('total_count', sa.Integer(), nullable=True),
        sa.Column('placed_level', sa.Integer(), nullable=True),
        sa.Column('overall_mastery', sa.Float(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_placement_attempts_id'), 'placement_attempts', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_placement_attempts_id'), table_name='placement_attempts')
    op.drop_table('placement_attempts')
    op.drop_column('user_profiles', 'onboarding_completed')
    op.drop_column('user_profiles', 'discovery_source_other')
    op.drop_column('user_profiles', 'discovery_source')
    op.drop_column('user_profiles', 'learning_motivation_other')
    op.drop_column('user_profiles', 'learning_motivation')
