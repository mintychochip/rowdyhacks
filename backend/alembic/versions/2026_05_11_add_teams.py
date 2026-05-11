"""Add team and team_member tables.

Revision ID: 2026_05_11_add_teams
Revises: 2026_05_11_add_webhooks
Create Date: 2026-05-11 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026_05_11_add_teams"
down_revision: Union[str, None] = "2026_05_11_add_webhooks"
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
        "teams",
        sa.Column("id", id_type, primary_key=True, nullable=False),
        sa.Column("hackathon_id", id_type, sa.ForeignKey("hackathons.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("join_code", sa.String(16), nullable=False, unique=True),
        sa.Column("captain_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=created_default, nullable=False),
    )
    op.create_index("ix_teams_join_code", "teams", ["join_code"], unique=True)

    op.create_table(
        "team_members",
        sa.Column("id", id_type, primary_key=True, nullable=False),
        sa.Column("team_id", id_type, sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=created_default, nullable=False),
    )

    # Add team_id to submissions
    op.add_column(
        "submissions",
        sa.Column("team_id", id_type, sa.ForeignKey("teams.id"), nullable=True),
    )
    op.create_index("ix_submissions_team_id", "submissions", ["team_id"])


def downgrade() -> None:
    op.drop_index("ix_submissions_team_id", table_name="submissions")
    op.drop_column("submissions", "team_id")
    op.drop_table("team_members")
    op.drop_index("ix_teams_join_code", table_name="teams")
    op.drop_table("teams")
