"""Add webhook subscription and delivery log tables.

Revision ID: 2026_05_11_add_webhooks
Revises: 2026_05_11_add_events
Create Date: 2026-05-11 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026_05_11_add_webhooks"
down_revision: Union[str, None] = "2026_05_11_add_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    dialect = op.get_context().dialect.name

    if dialect == "postgresql":
        id_type = postgresql.UUID(as_uuid=True)
        events_type = postgresql.ARRAY(sa.String())
        created_default = sa.text("now()")
    else:
        id_type = sa.String(36)
        events_type = sa.Text()
        created_default = sa.text("CURRENT_TIMESTAMP")

    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", id_type, primary_key=True, nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("secret", sa.String(128), nullable=False),
        sa.Column("events", events_type, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=created_default, nullable=False),
    )

    op.create_table(
        "webhook_delivery_logs",
        sa.Column("id", id_type, primary_key=True, nullable=False),
        sa.Column("subscription_id", id_type, sa.ForeignKey("webhook_subscriptions.id"), nullable=False),
        sa.Column("event_id", id_type, sa.ForeignKey("events.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("http_status", sa.Integer, nullable=True),
        sa.Column("response_body", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=created_default, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("webhook_delivery_logs")
    op.drop_table("webhook_subscriptions")
