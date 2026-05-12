"""make assistant_document hackathon_id nullable and add site_page to documenttype enum

Revision ID: 2026_05_12_make_assistant_doc_hackathon_id_nullable
Revises: 3e2ab12a7512
Create Date: 2026-05-12

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026_05_12_make_assistant_doc_hackathon_id_nullable"
down_revision: Union[str, Sequence[str], None] = "3e2ab12a7512"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'site_page' to the documenttype enum
    op.execute("ALTER TYPE documenttype ADD VALUE IF NOT EXISTS 'site_page'")

    # Make hackathon_id nullable on assistant_documents
    op.alter_column(
        "assistant_documents",
        "hackathon_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    # Revert hackathon_id to non-nullable
    op.alter_column(
        "assistant_documents",
        "hackathon_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )

    # Note: PostgreSQL does not support removing values from an enum.
    # To downgrade the enum change, you would need to recreate the enum.
    # This is intentionally left as a no-op for safety.
