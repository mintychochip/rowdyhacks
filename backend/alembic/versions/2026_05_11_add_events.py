"""Add events table.

Revision ID: 2026_05_11_add_events
Revises: 2026_05_11_add_site_config
Create Date: 2026-05-11 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026_05_11_add_events"
down_revision: Union[str, None] = "2026_05_11_add_site_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    dialect = op.get_context().dialect.name

    if dialect == "postgresql":
        id_type = postgresql.UUID(as_uuid=True)
        payload_type = postgresql.JSONB()
        created_default = sa.text("now()")
    else:
        id_type = sa.String(36)
        payload_type = sa.Text()
        created_default = sa.text("CURRENT_TIMESTAMP")

    op.create_table(
        "events",
        sa.Column("id", id_type, primary_key=True, nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("payload", payload_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=created_default, nullable=False),
    )
    op.create_index("ix_events_type", "events", ["type"])


def downgrade() -> None:
    op.drop_index("ix_events_type", table_name="events")
    op.drop_table("events")
