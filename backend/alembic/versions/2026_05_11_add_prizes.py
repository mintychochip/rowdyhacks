"""Add prizes table.

Revision ID: 2026_05_11_add_prizes
Revises: 2026_05_11_add_sponsors
Create Date: 2026-05-11 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026_05_11_add_prizes"
down_revision: Union[str, None] = "2026_05_11_add_sponsors"
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
        "prizes",
        sa.Column("id", id_type, primary_key=True, nullable=False),
        sa.Column("hackathon_id", id_type, sa.ForeignKey("hackathons.id"), nullable=False),
        sa.Column("track_id", id_type, sa.ForeignKey("tracks.id"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("amount", sa.String(100), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=created_default, nullable=False),
    )
    op.create_index("ix_prizes_hackathon_id", "prizes", ["hackathon_id"])
    op.create_index("ix_prizes_track_id", "prizes", ["track_id"])


def downgrade() -> None:
    op.drop_index("ix_prizes_track_id", table_name="prizes")
    op.drop_index("ix_prizes_hackathon_id", table_name="prizes")
    op.drop_table("prizes")
