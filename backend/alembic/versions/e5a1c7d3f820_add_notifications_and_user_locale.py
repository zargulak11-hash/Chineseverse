"""add notifications and users.locale

Revision ID: e5a1c7d3f820
Revises: c4e8a2f6b9d1
Create Date: 2026-09-30 18:00:00.000000

Following someone had no effect on the person followed: nothing was stored
for them and nothing reached them while they were away. `notifications`
persists "X followed you" (and later other types) per recipient with a
read state, plus private email-delivery bookkeeping so a copy can be mailed
and retried independently of the follow itself. `users.locale` remembers
the UI language the learner last used so that email can be written in it.
Both are additive; no existing row is touched.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e5a1c7d3f820'
down_revision: Union[str, Sequence[str], None] = 'c4e8a2f6b9d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recipient_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("email_status", sa.String(length=12), nullable=False, server_default="pending"),
        sa.Column("email_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("emailed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_notifications_id", "notifications", ["id"])
    op.create_index("ix_notifications_recipient_id", "notifications", ["recipient_id"])
    op.create_index("ix_notifications_actor_id", "notifications", ["actor_id"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])

    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("locale", sa.String(length=5), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("locale")
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_actor_id", table_name="notifications")
    op.drop_index("ix_notifications_recipient_id", table_name="notifications")
    op.drop_index("ix_notifications_id", table_name="notifications")
    op.drop_table("notifications")
