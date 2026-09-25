"""add users.is_admin and bootstrap the project owner account

Revision ID: a1c3f9e2d7b4
Revises: 06e70a177b1d
Create Date: 2026-09-25 17:00:00.000000

Adds the server-side-only admin flag the new /api/admin/* endpoints gate
on (see app.deps.require_admin). No prior is_admin/is_superuser/role field
existed anywhere in the schema, so this is a new, minimal mechanism rather
than a replacement for one.

Bootstrapping: there is no request path that can ever set is_admin (the
column isn't in any Pydantic schema accepted from a client), so the very
first admin has to be granted here, once, by matching the known project
owner account (username "Zarina", email zargulak11@gmail.com — the same
identity this whole project's git history is authored under). If that
account doesn't exist yet on a given database (a fresh clone, CI), this
step is simply a no-op: no user gets is_admin=True, and granting further
admins after that is a deliberate, separate DB action, never an app
feature (see deps.require_admin's docstring for why that's intentional).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1c3f9e2d7b4'
down_revision: Union[str, Sequence[str], None] = '06e70a177b1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OWNER_USERNAME = "Zarina"
OWNER_EMAIL = "zargulak11@gmail.com"

users_t = sa.table(
    "users",
    sa.column("id", sa.Integer),
    sa.column("username", sa.String),
    sa.column("email", sa.String),
    sa.column("is_admin", sa.Boolean),
)


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    bind = op.get_bind()
    bind.execute(
        users_t.update()
        .where(users_t.c.username == OWNER_USERNAME)
        .where(users_t.c.email == OWNER_EMAIL)
        .values(is_admin=True)
    )


def downgrade() -> None:
    op.drop_column("users", "is_admin")
