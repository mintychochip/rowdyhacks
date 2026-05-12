"""Add social and networking tables and user profile columns.

Revision ID: 2026_05_11_add_social_networking
Revises: 2026_05_11_add_plugins
Create Date: 2026-05-11 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026_05_11_add_social_networking"
down_revision: Union[str, None] = "2026_05_11_add_plugins"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    dialect = op.get_context().dialect.name

    if dialect == "postgresql":
        id_type = postgresql.UUID(as_uuid=True)
        created_default = sa.text("now()")
        json_type = postgresql.JSONB()
        array_type = postgresql.ARRAY(sa.String)
    else:
        id_type = sa.String(36)
        created_default = sa.text("CURRENT_TIMESTAMP")
        json_type = sa.Text
        array_type = sa.Text

    # Add user profile columns
    op.add_column("users", sa.Column("bio", sa.Text, nullable=True))
    op.add_column("users", sa.Column("skills", json_type, nullable=True))
    op.add_column("users", sa.Column("links", json_type, nullable=True))
    op.add_column("users", sa.Column("availability", sa.Text, nullable=True))
    op.add_column("users", sa.Column("looking_for_team", sa.Boolean, nullable=False, server_default=sa.false()))

    # Team finder posts
    op.create_table(
        "team_finder_posts",
        sa.Column("id", id_type, primary_key=True, nullable=False),
        sa.Column("hackathon_id", id_type, sa.ForeignKey("hackathons.id"), nullable=False),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("post_type", sa.String(30), nullable=False),
        sa.Column("skills_needed", array_type, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=created_default, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_team_finder_posts_hackathon", "team_finder_posts", ["hackathon_id"])
    op.create_index("ix_team_finder_posts_user", "team_finder_posts", ["user_id"])
    op.create_index("ix_team_finder_posts_active", "team_finder_posts", ["hackathon_id", "is_active"])

    # Mentorship requests
    op.create_table(
        "mentorship_requests",
        sa.Column("id", id_type, primary_key=True, nullable=False),
        sa.Column("hackathon_id", id_type, sa.ForeignKey("hackathons.id"), nullable=False),
        sa.Column("requester_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("mentor_id", sa.String(64), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("topic", sa.Text, nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=created_default, nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_mentorship_requests_hackathon", "mentorship_requests", ["hackathon_id"])
    op.create_index("ix_mentorship_requests_requester", "mentorship_requests", ["requester_id"])
    op.create_index("ix_mentorship_requests_mentor", "mentorship_requests", ["mentor_id"])

    # Public votes
    op.create_table(
        "public_votes",
        sa.Column("id", id_type, primary_key=True, nullable=False),
        sa.Column("hackathon_id", id_type, sa.ForeignKey("hackathons.id"), nullable=False),
        sa.Column("submission_id", id_type, sa.ForeignKey("submissions.id"), nullable=False),
        sa.Column("voter_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=created_default, nullable=False),
    )
    op.create_index("ix_public_votes_hackathon", "public_votes", ["hackathon_id"])
    op.create_index("ix_public_votes_submission", "public_votes", ["submission_id"])
    op.create_index("ix_public_votes_voter", "public_votes", ["voter_id"])
    op.create_index("ix_public_votes_unique", "public_votes", ["hackathon_id", "voter_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_public_votes_unique", table_name="public_votes")
    op.drop_index("ix_public_votes_voter", table_name="public_votes")
    op.drop_index("ix_public_votes_submission", table_name="public_votes")
    op.drop_index("ix_public_votes_hackathon", table_name="public_votes")
    op.drop_table("public_votes")

    op.drop_index("ix_mentorship_requests_mentor", table_name="mentorship_requests")
    op.drop_index("ix_mentorship_requests_requester", table_name="mentorship_requests")
    op.drop_index("ix_mentorship_requests_hackathon", table_name="mentorship_requests")
    op.drop_table("mentorship_requests")

    op.drop_index("ix_team_finder_posts_active", table_name="team_finder_posts")
    op.drop_index("ix_team_finder_posts_user", table_name="team_finder_posts")
    op.drop_index("ix_team_finder_posts_hackathon", table_name="team_finder_posts")
    op.drop_table("team_finder_posts")

    op.drop_column("users", "looking_for_team")
    op.drop_column("users", "availability")
    op.drop_column("users", "links")
    op.drop_column("users", "skills")
    op.drop_column("users", "bio")
