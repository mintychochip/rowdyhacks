import enum
import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, BigInteger, Boolean, Enum as SAEnum,
    DateTime, ForeignKey, Index, TypeDecorator, JSON,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# --- Custom types for cross-dialect compatibility (PostgreSQL + SQLite) ---

class Guid(TypeDecorator):
    """Platform-independent UUID type. Uses PostgreSQL UUID when available,
    falls back to String for SQLite."""
    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value  # UUID type handles it
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value  # Already a UUID
        if isinstance(value, str):
            return uuid.UUID(value)
        return value


class ArrayOfStrings(TypeDecorator):
    """Stores a list of strings. Uses PostgreSQL ARRAY(String) when available,
    falls back to JSON-encoded TEXT for SQLite."""
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(String))
        return dialect.type_descriptor(Text)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        return json.loads(value)


class JsonType(TypeDecorator):
    """Stores JSON data. Uses PostgreSQL JSONB when available,
    falls back to JSON-encoded TEXT for SQLite."""
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB)
        return dialect.type_descriptor(Text)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        return json.loads(value)


# --- Enums ---

class UserRole(str, enum.Enum):
    organizer = "organizer"
    participant = "participant"
    judge = "judge"


class SubmissionStatus(str, enum.Enum):
    pending = "pending"
    analyzing = "analyzing"
    completed = "completed"
    failed = "failed"


class Verdict(str, enum.Enum):
    clean = "clean"
    review = "review"
    flagged = "flagged"


class CheckStatus(str, enum.Enum):
    pass_ = "pass"
    warn = "warn"
    fail = "fail"
    error = "error"


class RegistrationStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    waitlisted = "waitlisted"
    offered = "offered"  # NEW: Spot offered, waiting for response
    checked_in = "checked_in"


class JudgingSessionStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    closed = "closed"


# --- Models ---

class User(Base):
    __tablename__ = "users"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    email = Column(String(320), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.participant)
    password_hash = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    hackathons = relationship("Hackathon", back_populates="organizer")
    submissions = relationship("Submission", back_populates="submitter")
    registrations = relationship("Registration", back_populates="user")
    oauth_accounts = relationship("OAuthAccount", back_populates="user", cascade="all, delete-orphan")
    co_organized_hackathons = relationship("HackathonOrganizer", back_populates="user", foreign_keys="HackathonOrganizer.user_id", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.email} role={self.role}>"


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    provider = Column(String(20), nullable=False)
    provider_user_id = Column(String(255), nullable=False)
    provider_email = Column(String(320), nullable=True)
    user_id = Column(Guid, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_oauth_accounts_provider_user", "provider", "provider_user_id", unique=True),
    )

    user = relationship("User", back_populates="oauth_accounts")

    def __repr__(self) -> str:
        return f"<OAuthAccount {self.provider} user={self.user_id}>"


class Hackathon(Base):
    __tablename__ = "hackathons"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    name = Column(String(300), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    application_deadline = Column(DateTime(timezone=True), nullable=True)
    max_participants = Column(Integer, nullable=True)
    current_participants = Column(Integer, nullable=False, default=0)
    waitlist_enabled = Column(Boolean, nullable=False, default=False)
    organizer_id = Column(Guid, ForeignKey("users.id"), nullable=False)
    description = Column(Text, nullable=True)
    schedule = Column(JsonType, nullable=True)
    venue_address = Column(Text, nullable=True)
    parking_info = Column(Text, nullable=True)
    wifi_ssid = Column(Text, nullable=True)
    wifi_password = Column(Text, nullable=True)
    discord_invite_url = Column(Text, nullable=True)
    discord_webhook_url = Column(Text, nullable=True)
    discord_application_channel_id = Column(BigInteger, nullable=True)
    devpost_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    organizer = relationship("User", back_populates="hackathons")
    submissions = relationship("Submission", back_populates="hackathon")
    registrations = relationship("Registration", back_populates="hackathon")
    co_organizers = relationship("HackathonOrganizer", back_populates="hackathon", cascade="all, delete-orphan")
    tracks = relationship("Track", back_populates="hackathon", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Hackathon {self.name}>"


class Track(Base):
    __tablename__ = "tracks"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    challenge = Column(Text, nullable=True)
    icon = Column(String(10), nullable=True)
    color = Column(String(20), nullable=True)
    prize = Column(String(300), nullable=True)
    track_type = Column(String(50), nullable=True)  # "prize", "themed", "sponsor", or null
    criteria = Column(JsonType, nullable=True)
    resources = Column(JsonType, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    hackathon = relationship("Hackathon", back_populates="tracks")

    def __repr__(self) -> str:
        return f"<Track {self.name}>"


class HackathonOrganizer(Base):
    """Many-to-many relationship for co-organizers (multi-organizer hackathons)."""
    __tablename__ = "hackathon_organizers"
    __table_args__ = (
        Index("ix_hackathon_organizers_hackathon", "hackathon_id"),
        Index("ix_hackathon_organizers_user", "user_id"),
    )

    hackathon_id = Column(Guid, ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Guid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    added_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    added_by = Column(Guid, ForeignKey("users.id"), nullable=True)

    hackathon = relationship("Hackathon", back_populates="co_organizers")
    user = relationship("User", foreign_keys=[user_id], back_populates="co_organized_hackathons")


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        Index("ix_submissions_verdict", "verdict"),
        Index("ix_submissions_risk_score", "risk_score"),
    )

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    devpost_url = Column(Text, nullable=False)
    github_url = Column(Text, nullable=True)
    project_title = Column(Text, nullable=True)
    project_description = Column(Text, nullable=True)
    claimed_tech = Column(ArrayOfStrings, nullable=True)
    team_members = Column(JsonType, nullable=True)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id"), nullable=True, index=True)
    submitted_by = Column(Guid, ForeignKey("users.id"), nullable=True)
    status = Column(SAEnum(SubmissionStatus), nullable=False, default=SubmissionStatus.pending, index=True)
    risk_score = Column(Integer, nullable=True)
    verdict = Column(SAEnum(Verdict), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    access_token = Column(String(36), nullable=True)
    stage = Column(String(50), nullable=True)  # progress stage: scraping, cloning, checking, scoring
    check_progress = Column(JsonType, nullable=True)  # {completed: ["check1"], pending: ["check2", ...], current: "check name"}

    hackathon = relationship("Hackathon", back_populates="submissions")
    submitter = relationship("User", back_populates="submissions")
    check_results = relationship("CheckResultModel", back_populates="submission", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Submission {self.devpost_url}>"


class CheckResultModel(Base):
    __tablename__ = "check_results"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    submission_id = Column(Guid, ForeignKey("submissions.id"), nullable=False)
    check_category = Column(String(100), nullable=False)
    check_name = Column(String(100), nullable=False)
    score = Column(Integer, nullable=False)
    status = Column(SAEnum(CheckStatus), nullable=False)
    details = Column(JsonType, nullable=True)
    evidence = Column(ArrayOfStrings, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    submission = relationship("Submission", back_populates="check_results")

    def __repr__(self) -> str:
        return f"<CheckResult {self.check_name} score={self.score}>"


class Registration(Base):
    __tablename__ = "registrations"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id"), nullable=False)
    user_id = Column(Guid, ForeignKey("users.id"), nullable=False)
    status = Column(SAEnum(RegistrationStatus), nullable=False, default=RegistrationStatus.pending)
    team_name = Column(String(200), nullable=True)
    team_members = Column(JsonType, nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    github_url = Column(String(500), nullable=True)
    resume_url = Column(String(500), nullable=True)
    experience_level = Column(String(50), nullable=True)
    t_shirt_size = Column(String(10), nullable=True)
    phone = Column(String(20), nullable=True)
    dietary_restrictions = Column(String(500), nullable=True)
    what_build = Column(Text, nullable=True)
    why_participate = Column(Text, nullable=True)
    age = Column(Integer, nullable=True)
    school = Column(String(200), nullable=True)
    major = Column(String(200), nullable=True)
    pronouns = Column(String(50), nullable=True)
    skills = Column(ArrayOfStrings, nullable=True)
    emergency_contact_name = Column(String(200), nullable=True)
    emergency_contact_phone = Column(String(30), nullable=True)
    qr_token = Column(String(512), nullable=True)
    pass_serial_apple = Column(String(128), nullable=True)
    pass_id_google = Column(String(128), nullable=True)
    registered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    checked_in_at = Column(DateTime(timezone=True), nullable=True)

    # Waitlist fields
    offered_at = Column(DateTime(timezone=True), nullable=True)
    offer_expires_at = Column(DateTime(timezone=True), nullable=True)
    declined_count = Column(Integer, default=0, nullable=True)

    # Additional registration data fields
    special_needs = Column(Text, nullable=True)
    school_company = Column(Text, nullable=True)
    graduation_year = Column(Integer, nullable=True)

    hackathon = relationship("Hackathon", back_populates="registrations")
    user = relationship("User", back_populates="registrations")
    scans = relationship("Scan", back_populates="registration", cascade="all, delete-orphan")
    email_logs = relationship("EmailLog", back_populates="registration")

    def __repr__(self) -> str:
        return f"<Registration {self.id} status={self.status}>"


class Scan(Base):
    __tablename__ = "scans"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    registration_id = Column(Guid, ForeignKey("registrations.id"), nullable=False)
    scan_type = Column(String(50), nullable=False, default="checkin")
    scanned_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    registration = relationship("Registration", back_populates="scans")

    def __repr__(self) -> str:
        return f"<Scan {self.id} type={self.scan_type}>"


class CrawledHackathon(Base):
    __tablename__ = "crawled_hackathons"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    devpost_url = Column(Text, unique=True, nullable=False)
    name = Column(String(300), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    submission_count = Column(Integer, nullable=True)
    last_crawled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    projects = relationship("CrawledProject", back_populates="hackathon", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<CrawledHackathon {self.name}>"


class CrawledProject(Base):
    __tablename__ = "crawled_projects"
    __table_args__ = (
        Index("ix_crawled_projects_github_url", "github_url"),
        Index("ix_crawled_projects_commit_hash", "commit_hash"),
    )

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    devpost_url = Column(Text, unique=True, nullable=False)
    hackathon_id = Column(Guid, ForeignKey("crawled_hackathons.id"), nullable=False)
    title = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    claimed_tech = Column(ArrayOfStrings, nullable=True)
    team_members = Column(JsonType, nullable=True)
    github_url = Column(Text, nullable=True)
    commit_hash = Column(String(40), nullable=True)
    video_url = Column(Text, nullable=True)
    slides_url = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    last_crawled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    hackathon = relationship("CrawledHackathon", back_populates="projects")

    def __repr__(self) -> str:
        return f"<CrawledProject {self.devpost_url}>"


class JudgingSession(Base):
    """Per-hackathon judging configuration: window times, per-project limit, linked rubric."""
    __tablename__ = "judging_sessions"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id"), unique=True, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    per_project_seconds = Column(Integer, nullable=False, default=300)
    leaderboard_public = Column(Boolean, nullable=False, default=False)
    status = Column(SAEnum(JudgingSessionStatus), nullable=False, default=JudgingSessionStatus.pending)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    rubric = relationship("Rubric", back_populates="session", uselist=False, cascade="all, delete-orphan")
    assignments = relationship("JudgeAssignment", back_populates="session", cascade="all, delete-orphan")


class Rubric(Base):
    __tablename__ = "rubrics"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    session_id = Column(Guid, ForeignKey("judging_sessions.id"), unique=True, nullable=False)
    name = Column(String(200), nullable=False, default="Default Rubric")

    session = relationship("JudgingSession", back_populates="rubric")
    criteria = relationship("RubricCriterion", back_populates="rubric", cascade="all, delete-orphan")


class RubricCriterion(Base):
    __tablename__ = "rubric_criteria"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    rubric_id = Column(Guid, ForeignKey("rubrics.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    max_score = Column(Integer, nullable=False, default=10)
    weight = Column(Integer, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)

    rubric = relationship("Rubric", back_populates="criteria")


class JudgeAssignment(Base):
    __tablename__ = "judge_assignments"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    session_id = Column(Guid, ForeignKey("judging_sessions.id"), nullable=False)
    judge_id = Column(Guid, ForeignKey("users.id"), nullable=False)
    submission_id = Column(Guid, ForeignKey("submissions.id"), nullable=False)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    is_completed = Column(Integer, nullable=False, default=0)

    session = relationship("JudgingSession", back_populates="assignments")
    scores = relationship("Score", back_populates="assignment", cascade="all, delete-orphan")


class Score(Base):
    __tablename__ = "scores"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    assignment_id = Column(Guid, ForeignKey("judge_assignments.id"), nullable=False)
    criterion_id = Column(Guid, ForeignKey("rubric_criteria.id"), nullable=False)
    score = Column(Integer, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    is_auto_submitted = Column(Integer, nullable=False, default=0)

    assignment = relationship("JudgeAssignment", back_populates="scores")


class JudgeRating(Base):
    __tablename__ = "judge_ratings"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    judge_id = Column(Guid, ForeignKey("users.id"), nullable=False)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id"), nullable=False)
    rating = Column(Integer, nullable=False, default=1500)
    projects_scored = Column(Integer, nullable=False, default=0)
    mean_raw_score = Column(Integer, nullable=True)
    stddev_raw_score = Column(Integer, nullable=True)


class Announcement(Base):
    """Organizer announcements to hackathon participants."""
    __tablename__ = "announcements"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False, default="normal")  # low, normal, high, urgent
    sent_by = Column(Guid, ForeignKey("users.id"), nullable=False)
    sent_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ConflictOfInterest(Base):
    """Judge conflict of interest declarations."""
    __tablename__ = "conflicts_of_interest"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    judge_id = Column(Guid, ForeignKey("users.id"), nullable=False)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id"), nullable=False)
    submission_id = Column(Guid, ForeignKey("submissions.id"), nullable=False)
    reason = Column(Text, nullable=True)
    declared_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


# --- Fingerprint Models for Cross-Submission Similarity ---

class SubmissionFingerprint(Base):
    """Store SimHash fingerprints for cross-submission similarity detection."""
    __tablename__ = "submission_fingerprints"
    __table_args__ = (
        Index("idx_fingerprint_simhash", "simhash"),
        Index("idx_fingerprint_submission", "submission_id", "simhash"),
    )

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    submission_id = Column(Guid, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False, index=True)
    simhash = Column(BigInteger, nullable=False, index=True)
    github_url = Column(Text, nullable=True)
    repo_size_bytes = Column(Integer, default=0)
    code_lines = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SimilarityMatch(Base):
    """Store detected similarities between submissions."""
    __tablename__ = "similarity_matches"
    __table_args__ = (
        Index("idx_similarity_pair", "submission_a_id", "submission_b_id"),
        Index("idx_similarity_score", "similarity_score"),
        Index("idx_similarity_status", "status"),
    )

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    submission_a_id = Column(Guid, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    hackathon_a_id = Column(Guid, ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False)
    submission_b_id = Column(Guid, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    hackathon_b_id = Column(Guid, ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False)
    similarity_score = Column(Integer, nullable=False)  # 0-100
    hamming_distance = Column(Integer, nullable=False)
    matching_files = Column(Text, nullable=True)
    status = Column(String(20), default="pending")  # pending, confirmed, dismissed
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(Guid, ForeignKey("users.id"), nullable=True)


class EmailLog(Base):
    """Track email sending for retry and auditing."""
    __tablename__ = "email_logs"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    registration_id = Column(Guid, ForeignKey("registrations.id"), nullable=True)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id"), nullable=True)
    email_type = Column(String(50), nullable=False)
    recipient_email = Column(Text, nullable=False)
    status = Column(String(20), nullable=False)  # pending, sent, failed
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc))

    registration = relationship("Registration", back_populates="email_logs")
