"""Add site_config table.

Revision ID: 2026_05_11_add_site_config
Revises: 3e2ab12a7512
Create Date: 2026-05-11 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026_05_11_add_site_config"
down_revision: Union[str, None] = "3e2ab12a7512"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "site_config",
        sa.Column("key", sa.String(64), primary_key=True, nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("category", sa.String(32), nullable=False, server_default="general", index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("site_config")
