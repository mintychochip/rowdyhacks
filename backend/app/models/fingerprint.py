"""Fingerprint models for cross-submission similarity detection."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import ForeignKey, Index, String, Text, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.models import Base


class SubmissionFingerprint(Base):
    """Store SimHash fingerprints for cross-submission similarity detection."""
    
    __tablename__ = "submission_fingerprints"
    
    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hackathon_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("hackathons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # SimHash fingerprint (64-bit hash stored as signed int64)
    simhash: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    
    # Source info
    github_url: Mapped[str] = mapped_column(Text, nullable=True)
    repo_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    code_lines: Mapped[int] = mapped_column(Integer, default=0)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    submission: Mapped["Submission"] = relationship(back_populates="fingerprints")
    hackathon: Mapped["Hackathon"] = relationship(back_populates="fingerprints")
    
    __table_args__ = (
        Index("idx_fingerprint_simhash", "simhash"),
        Index("idx_fingerprint_submission", "submission_id", "simhash"),
    )


class SimilarityMatch(Base):
    """Store detected similarities between submissions."""
    
    __tablename__ = "similarity_matches"
    
    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # First submission
    submission_a_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    hackathon_a_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("hackathons.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Second submission
    submission_b_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    hackathon_b_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("hackathons.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Similarity score (0-100, higher = more similar)
    similarity_score: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Hamming distance between SimHashes (lower = more similar)
    hamming_distance: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Evidence: matching file paths
    matching_files: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
    )  # pending, confirmed, dismissed
    
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    
    __table_args__ = (
        Index("idx_similarity_pair", "submission_a_id", "submission_b_id"),
        Index("idx_similarity_score", "similarity_score"),
        Index("idx_similarity_status", "status"),
    )
