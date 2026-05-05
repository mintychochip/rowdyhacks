"""add content pages and track markdown

Revision ID: add_content_pages
Revises: 13c6923a3bb7
Create Date: 2026-05-04

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_content_pages"
down_revision: Union[str, Sequence[str], None] = "add_assistant_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    dialect = op.get_context().dialect.name

    # Add resources_markdown column to tracks table
    op.add_column("tracks", sa.Column("resources_markdown", sa.Text(), nullable=True))

    # Create content_pages table
    if dialect == "postgresql":
        id_type = postgresql.UUID(as_uuid=True)
        fk_type = postgresql.UUID(as_uuid=True)
        server_default_uuid = sa.text("gen_random_uuid()")
    else:
        id_type = sa.String(36)
        fk_type = sa.String(36)
        server_default_uuid = None

    id_server_default = server_default_uuid if server_default_uuid is not None else None

    op.create_table(
        "content_pages",
        sa.Column("id", id_type, primary_key=True, server_default=id_server_default),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tab_group", sa.String(50), nullable=False, server_default="resources"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tab_group_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", fk_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP") if dialect == "sqlite" else sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes for content_pages
    op.create_index("ix_content_pages_slug", "content_pages", ["slug"])
    op.create_index("ix_content_pages_tab_group", "content_pages", ["tab_group", "sort_order"])
    op.create_index("ix_content_pages_published", "content_pages", ["is_published"])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop content_pages indexes and table
    op.drop_index("ix_content_pages_published", table_name="content_pages")
    op.drop_index("ix_content_pages_tab_group", table_name="content_pages")
    op.drop_index("ix_content_pages_slug", table_name="content_pages")
    op.drop_table("content_pages")

    # Drop resources_markdown column from tracks
    op.drop_column("tracks", "resources_markdown")
