"""add users.password_changed_at

Revision ID: f6c2a8d4e197
Revises: e4b9c2d7a613
Create Date: 2026-10-08 10:00:00.000000

Learners can now change their password in Settings (POST
/api/me/password). Access tokens are stateless JWTs valid for seven days,
so without a record of when the password changed, a token stolen before
the change would keep working until it expired. Tokens issued before this
timestamp are refused (deps.get_current_user); the session that made the
change gets a fresh token.

Nullable with no default: every existing account reads as "never
changed", so no current session is ended by this migration.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6c2a8d4e197'
down_revision: Union[str, Sequence[str], None] = 'e4b9c2d7a613'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('password_changed_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users') as batch:
        batch.drop_column('password_changed_at')
