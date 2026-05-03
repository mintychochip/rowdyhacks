"""add waitlist and registration fields

Revision ID: 13c6923a3bb7
Revises:
Create Date: 2026-05-03

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "13c6923a3bb7"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Get the dialect name
    dialect = op.get_context().dialect.name

    # Add 'offered' to the registrationstatus enum (PostgreSQL only)
    # Must commit before using the new value in partial indexes
    if dialect == "postgresql":
        op.execute("ALTER TYPE registrationstatus ADD VALUE IF NOT EXISTS 'offered'")
        op.execute("COMMIT")

    # Add registration fields for waitlist support
    op.add_column("registrations", sa.Column("offered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("registrations", sa.Column("offer_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("registrations", sa.Column("declined_count", sa.Integer(), nullable=True, server_default="0"))

    # Add additional registration data fields
    # Note: dietary_restrictions, experience_level, t_shirt_size already exist in models
    # We only add the missing ones
    op.add_column("registrations", sa.Column("special_needs", sa.Text(), nullable=True))
    op.add_column("registrations", sa.Column("school_company", sa.Text(), nullable=True))
    op.add_column("registrations", sa.Column("graduation_year", sa.Integer(), nullable=True))

    # Create index for waitlist queries (PostgreSQL-specific partial index)
    # For SQLite, we create a regular index since partial indexes work differently
    if dialect == "postgresql":
        op.create_index(
            "idx_registrations_waitlist",
            "registrations",
            ["hackathon_id", "status", "declined_count", "registered_at"],
            postgresql_where=sa.text("status = 'waitlisted'"),
        )
    else:
        # For SQLite and others, create a regular index
        op.create_index(
            "idx_registrations_waitlist", "registrations", ["hackathon_id", "status", "declined_count", "registered_at"]
        )

    # Create index for expired offer cleanup
    if dialect == "postgresql":
        op.create_index(
            "idx_registrations_offered_expires",
            "registrations",
            ["status", "offer_expires_at"],
            postgresql_where=sa.text("status = 'offered'"),
        )
    else:
        op.create_index("idx_registrations_offered_expires", "registrations", ["status", "offer_expires_at"])

    # Create email_logs table
    # Use dialect-appropriate UUID type
    if dialect == "postgresql":
        id_type = postgresql.UUID(as_uuid=True)
        fk_type = postgresql.UUID(as_uuid=True)
        server_default_uuid = sa.text("gen_random_uuid()")
    else:
        id_type = sa.String(36)
        fk_type = sa.String(36)
        server_default_uuid = None  # SQLite doesn't support server_default for UUID

    # Build server_default conditionally (use explicit None check to avoid boolean evaluation of SQL expression)
    id_server_default = server_default_uuid if server_default_uuid is not None else None

    op.create_table(
        "email_logs",
        sa.Column("id", id_type, primary_key=True, server_default=id_server_default),
        sa.Column("registration_id", fk_type, sa.ForeignKey("registrations.id"), nullable=True),
        sa.Column("hackathon_id", fk_type, sa.ForeignKey("hackathons.id"), nullable=True),
        sa.Column("email_type", sa.String(length=50), nullable=False),
        sa.Column("recipient_email", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP") if dialect == "sqlite" else sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes for email_logs
    if dialect == "postgresql":
        op.create_index(
            "idx_email_logs_status",
            "email_logs",
            ["status", "retry_count"],
            postgresql_where=sa.text("status = 'failed'"),
        )
    else:
        op.create_index("idx_email_logs_status", "email_logs", ["status", "retry_count"])

    op.create_index("idx_email_logs_hackathon", "email_logs", ["hackathon_id", "created_at"])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop email_logs table and indexes
    op.drop_index("idx_email_logs_hackathon", table_name="email_logs")
    op.drop_index("idx_email_logs_status", table_name="email_logs")
    op.drop_table("email_logs")

    # Drop registration indexes
    op.drop_index("idx_registrations_offered_expires", table_name="registrations")
    op.drop_index("idx_registrations_waitlist", table_name="registrations")

    # Drop registration columns (in reverse order)
    op.drop_column("registrations", "graduation_year")
    op.drop_column("registrations", "school_company")
    op.drop_column("registrations", "special_needs")
    op.drop_column("registrations", "declined_count")
    op.drop_column("registrations", "offer_expires_at")
    op.drop_column("registrations", "offered_at")
