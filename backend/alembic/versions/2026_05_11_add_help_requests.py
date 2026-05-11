"""Add help_requests table.

Revision ID: 2026_05_11_add_help_requests
Revises: 2026_05_11_add_prizes
Create Date: 2026-05-11 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026_05_11_add_help_requests"
down_revision: Union[str, None] = "2026_05_11_add_prizes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    dialect = op.get_context().dialect.name

    if dialect == "postgresql":
        id_type = postgresql.UUID(as_uuid=True)
        created_default = sa.text("now()")
    else:
        id_type = sa.String(36)
        created_default = sa.text("CURRENT_TIMESTAMP")

    op.create_table(
        "help_requests",
        sa.Column("id", id_type, primary_key=True, nullable=False),
        sa.Column("hackathon_id", id_type, sa.ForeignKey("hackathons.id"), nullable=False),
        sa.Column("requester_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("mentor_id", sa.String(64), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=created_default, nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_help_requests_hackathon_id", "help_requests", ["hackathon_id"])
    op.create_index("ix_help_requests_status", "help_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_help_requests_status", table_name="help_requests")
    op.drop_index("ix_help_requests_hackathon_id", table_name="help_requests")
    op.drop_table("help_requests")
