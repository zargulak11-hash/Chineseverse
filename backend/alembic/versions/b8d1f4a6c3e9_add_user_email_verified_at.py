"""add users.email_verified_at

Revision ID: b8d1f4a6c3e9
Revises: e7b3c9d2f418
Create Date: 2026-10-26 12:00:00.000000

Google and GitHub sign-in linked to any existing account whose email
matched -- but a password registration never proves the address is the
registrant's. Anyone could register a victim's address with a password of
their own, wait for the victim's first Google sign-in to land in that same
account, and keep signing in with the password ("pre-account takeover";
the same for an address later added to ADMIN_EMAILS). Linking by email now
requires the account's own email to have been proven (routers/auth.py
_sign_in_external): by the provider that created or is linked to the
account, or by a completed emailed reset link (services/password_reset.py).

Backfill: an account already bound to Google or GitHub got its address from
that provider, so it counts as proven. Password-only accounts stay null --
their password keeps working exactly as before; only joining them to a
Google/GitHub sign-in needs the address confirmed once.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8d1f4a6c3e9'
down_revision: Union[str, Sequence[str], None] = 'e7b3c9d2f418'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('email_verified_at', sa.DateTime(), nullable=True))
    op.execute(
        "UPDATE users SET email_verified_at = CURRENT_TIMESTAMP "
        "WHERE email_verified_at IS NULL AND (google_sub IS NOT NULL OR github_id IS NOT NULL)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users') as batch:
        batch.drop_column('email_verified_at')
