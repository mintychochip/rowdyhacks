"""Assistant models for AI chat functionality."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models import Base


class ConversationRole(str, Enum):
    """Roles in a conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class AssistantMessageStatus(str, Enum):
    """Status of an assistant message."""

    PENDING = "pending"  # Waiting for LLM response
    STREAMING = "streaming"  # Currently streaming
    COMPLETED = "completed"  # Finished successfully
    ERROR = "error"  # Failed


class DocumentType(str, Enum):
    """Types of documents that can be indexed."""

    HACKATHON_INFO = "hackathon_info"
    TRACK_INFO = "track_info"
    FAQ = "faq"
    SCHEDULE = "schedule"
    RULES = "rules"
    RESOURCES = "resources"
    SUBMISSION_SUMMARY = "submission_summary"


class AssistantConversation(Base):
    """A conversation session between a user and the assistant."""

    __tablename__ = "assistant_conversations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hackathon_id = Column(
        UUID(as_uuid=True),
        ForeignKey("hackathons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title = Column(String(255), nullable=True)  # Auto-generated from first message
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.utcnow() + timedelta(days=30),
    )

    # Relationships
    user = relationship("User", back_populates="assistant_conversations")
    hackathon = relationship("Hackathon", back_populates="assistant_conversations")
    messages = relationship(
        "AssistantMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AssistantMessage.created_at",
    )


def default_tool_calls():
    """Default empty list for tool_calls."""
    return []


def default_tool_results():
    """Default empty list for tool_results."""
    return []


class AssistantMessage(Base):
    """A single message in a conversation."""

    __tablename__ = "assistant_messages"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(
        SQLEnum(ConversationRole),
        nullable=False,
    )
    content = Column(Text, nullable=False, default="")
    tool_calls = Column(JSONB, nullable=False, default=default_tool_calls)
    tool_results = Column(JSONB, nullable=False, default=default_tool_results)
    status = Column(
        SQLEnum(AssistantMessageStatus),
        nullable=False,
        default=AssistantMessageStatus.COMPLETED,
    )
    model_used = Column(String(100), nullable=True)  # e.g., "poolside/m.1"
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    conversation = relationship("AssistantConversation", back_populates="messages")


class AssistantDocument(Base):
    """Metadata for documents indexed in Qdrant (actual content is in vector store)."""

    __tablename__ = "assistant_documents"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    hackathon_id = Column(
        UUID(as_uuid=True),
        ForeignKey("hackathons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    qdrant_id = Column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
    )  # The ID in Qdrant vector store
    doc_type = Column(
        SQLEnum(DocumentType),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    source_id = Column(
        UUID(as_uuid=True),
        nullable=True,
    )  # e.g., track_id, faq_id
    doc_metadata = Column(JSONB, nullable=False, default=dict)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    hackathon = relationship("Hackathon", back_populates="assistant_documents")


# Import timedelta for default expires_at
from datetime import timedelta
