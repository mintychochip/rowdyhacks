"""Add plugins table.

Revision ID: 2026_05_11_add_plugins
Revises: 2026_05_11_add_help_requests
Create Date: 2026-05-11 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026_05_11_add_plugins"
down_revision: Union[str, None] = "2026_05_11_add_help_requests"
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
        "plugins",
        sa.Column("id", id_type, primary_key=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("version", sa.String(50), nullable=False, server_default="0.1.0"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("config", sa.JSON() if dialect == "postgresql" else sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=created_default, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("plugins")
