"""Add assistant models for AI chat functionality.

Revision ID: add_assistant_models
Revises: 13c6923a3bb7
Create Date: 2025-05-04

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_assistant_models'
down_revision: Union[str, None] = '13c6923a3bb7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE conversationrole AS ENUM ('user', 'assistant', 'system', 'tool')")
    op.execute("CREATE TYPE assistantmessagestatus AS ENUM ('pending', 'streaming', 'completed', 'error')")
    op.execute("CREATE TYPE documenttype AS ENUM ('hackathon_info', 'track_info', 'faq', 'schedule', 'rules', 'resources', 'submission_summary')")

    # Create assistant_conversations table
    op.create_table(
        'assistant_conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hackathon_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['hackathon_id'], ['hackathons.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_assistant_conversations_user_id', 'assistant_conversations', ['user_id'])
    op.create_index('ix_assistant_conversations_hackathon_id', 'assistant_conversations', ['hackathon_id'])
    op.create_index('ix_assistant_conversations_expires_at', 'assistant_conversations', ['expires_at'])

    # Create assistant_messages table
    op.create_table(
        'assistant_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.Enum('user', 'assistant', 'system', 'tool', name='conversationrole'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tool_calls', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('tool_results', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('status', sa.Enum('pending', 'streaming', 'completed', 'error', name='assistantmessagestatus'), nullable=False),
        sa.Column('model_used', sa.String(100), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['assistant_conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_assistant_messages_conversation_id', 'assistant_messages', ['conversation_id'])
    op.create_index('ix_assistant_messages_created_at', 'assistant_messages', ['created_at'])

    # Create assistant_documents table
    op.create_table(
        'assistant_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hackathon_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('qdrant_id', sa.String(36), nullable=False),
        sa.Column('doc_type', sa.Enum('hackathon_info', 'track_info', 'faq', 'schedule', 'rules', 'resources', 'submission_summary', name='documenttype'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['hackathon_id'], ['hackathons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('qdrant_id')
    )
    op.create_index('ix_assistant_documents_hackathon_id', 'assistant_documents', ['hackathon_id'])
    op.create_index('ix_assistant_documents_qdrant_id', 'assistant_documents', ['qdrant_id'])
    op.create_index('ix_assistant_documents_doc_type', 'assistant_documents', ['doc_type'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('assistant_documents')
    op.drop_table('assistant_messages')
    op.drop_table('assistant_conversations')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS documenttype")
    op.execute("DROP TYPE IF EXISTS assistantmessagestatus")
    op.execute("DROP TYPE IF EXISTS conversationrole")
