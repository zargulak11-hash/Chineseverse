"""add users.sessions_revoked_at

Revision ID: d4a9c2e7f150
Revises: b8d1f4a6c3e9
Create Date: 2026-10-27 10:00:00.000000

Access tokens are stateless JWTs valid for seven days, and signing out only
forgot the token in that one browser: a token copied off a shared or lost
device kept working until it expired, unless the password was changed.
Settings -> "Sign out of all other devices" (POST /api/me/sessions/revoke)
records this time, and deps.get_current_user refuses tokens issued before
it, exactly as it does for password_changed_at.

Nullable with no default: every existing account reads as "never used", so
no current session is ended by this migration.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4a9c2e7f150'
down_revision: Union[str, Sequence[str], None] = 'b8d1f4a6c3e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('sessions_revoked_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users') as batch:
        batch.drop_column('sessions_revoked_at')
