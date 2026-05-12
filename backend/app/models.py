"""SQLAlchemy ORM models and cross-dialect custom types.

Defines the full database schema for the hackathon platform, including
users, hackathons, registrations, submissions, judging, and auxiliary
entities. Also provides portable SQLAlchemy types that transparently
switch between PostgreSQL-native features (UUID, ARRAY, JSONB) and
SQLite-compatible fallbacks for local development.
"""

import enum
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TypeDecorator,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


# --- Custom types for cross-dialect compatibility (PostgreSQL + SQLite) ---


class Guid(TypeDecorator):
    """Platform-independent UUID type that uses PostgreSQL native UUID when available and falls back to String(36) for SQLite."""

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Select the appropriate dialect-specific implementation for UUID storage.

        Behavior:
        1. Check if the dialect is postgresql.
        2. Return UUID(as_uuid=True) type descriptor for PostgreSQL.
        3. Return String(36) type descriptor for other dialects.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: sqlalchemy.dialects.postgresql.UUID.
        Consumers: SQLAlchemy column binding.
        """
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        """Convert a UUID object to a database-bound value.

        Behavior:
        1. Return None if value is None.
        2. Return the raw UUID for PostgreSQL (driver handles it).
        3. Convert to string for all other dialects.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: None
        Consumers: SQLAlchemy column binding.
        """
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value  # UUID type handles it
        return str(value)

    def process_result_value(self, value, dialect):
        """Convert a database result value back to a UUID object.

        Behavior:
        1. Return None if value is None.
        2. Return the raw value for PostgreSQL (already a UUID).
        3. Parse string into uuid.UUID for other dialects.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: uuid.UUID.
        Consumers: SQLAlchemy column result loading.
        """
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value  # Already a UUID
        return uuid.UUID(value)


class ArrayOfStrings(TypeDecorator):
    """Cross-dialect type that stores a list of strings using PostgreSQL ARRAY or JSON-encoded TEXT for SQLite."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Select the appropriate dialect-specific implementation for string array storage.

        Behavior:
        1. Check if the dialect is postgresql.
        2. Return ARRAY(String) type descriptor for PostgreSQL.
        3. Return Text type descriptor for other dialects.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: sqlalchemy.dialects.postgresql.ARRAY.
        Consumers: SQLAlchemy column binding.
        """
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(String))
        return dialect.type_descriptor(Text)

    def process_bind_param(self, value, dialect):
        """Serialize a list of strings for database storage.

        Behavior:
        1. Return None if value is None.
        2. Return the raw list for PostgreSQL (driver handles it).
        3. JSON-encode the list for all other dialects.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: json.dumps.
        Consumers: SQLAlchemy column binding.
        """
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        """Deserialize a database result back into a list of strings.

        Behavior:
        1. Return None if value is None.
        2. Return the raw value for PostgreSQL (already a list).
        3. JSON-decode the string for other dialects.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: json.loads.
        Consumers: SQLAlchemy column result loading.
        """
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        return json.loads(value)


class JsonType(TypeDecorator):
    """Cross-dialect type that stores JSON data using PostgreSQL JSONB or JSON-encoded TEXT for SQLite."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Select the appropriate dialect-specific implementation for JSON storage.

        Behavior:
        1. Check if the dialect is postgresql.
        2. Return JSONB type descriptor for PostgreSQL.
        3. Return Text type descriptor for other dialects.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: sqlalchemy.dialects.postgresql.JSONB.
        Consumers: SQLAlchemy column binding.
        """
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB)
        return dialect.type_descriptor(Text)

    def process_bind_param(self, value, dialect):
        """Serialize a Python object to JSON for database storage.

        Behavior:
        1. Return None if value is None.
        2. Return the raw object for PostgreSQL (driver handles it).
        3. JSON-encode the object for all other dialects.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: json.dumps.
        Consumers: SQLAlchemy column binding.
        """
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        """Deserialize a database result back into a Python object.

        Behavior:
        1. Return None if value is None.
        2. Return the raw value for PostgreSQL (already parsed).
        3. JSON-decode the string for other dialects.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: json.loads.
        Consumers: SQLAlchemy column result loading.
        """
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        return json.loads(value)


# --- Enums ---


class UserRole(str, enum.Enum):
    """Roles available to users in the platform: organizer, participant, judge, or volunteer."""

    organizer = "organizer"
    participant = "participant"
    judge = "judge"
    volunteer = "volunteer"


class SubmissionStatus(str, enum.Enum):
    """Lifecycle states of a project submission review pipeline."""

    pending = "pending"
    analyzing = "analyzing"
    completed = "completed"
    failed = "failed"


class Verdict(str, enum.Enum):
    """Final integrity verdict assigned to a submission after analysis."""

    clean = "clean"
    review = "review"
    flagged = "flagged"


class CheckStatus(str, enum.Enum):
    """Outcome of an individual automated submission check."""

    pass_ = "pass"
    warn = "warn"
    fail = "fail"
    error = "error"


class RegistrationStatus(str, enum.Enum):
    """Lifecycle states of a hackathon participant registration."""

    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    waitlisted = "waitlisted"
    offered = "offered"  # NEW: Spot offered, waiting for response
    checked_in = "checked_in"


class JudgingSessionStatus(str, enum.Enum):
    """Lifecycle states of a hackathon judging session time window."""

    pending = "pending"
    active = "active"
    closed = "closed"


class WorkshopRSVPStatus(str, enum.Enum):
    """Lifecycle states of a workshop attendee RSVP."""

    registered = "registered"
    attended = "attended"
    cancelled = "cancelled"


class QuestionType(str, enum.Enum):
    """Type of a custom registration question."""

    text = "text"
    textarea = "textarea"
    number = "number"
    select = "select"
    multiselect = "multiselect"
    checkbox = "checkbox"
    url = "url"
    file = "file"


class NotificationType(str, enum.Enum):
    """Severity level of an in-app notification."""

    info = "info"
    success = "success"
    warning = "warning"
    error = "error"


# --- Models ---


class User(Base):
    """A platform user with role, OAuth links, registrations, and team memberships."""

    __tablename__ = "users"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(320), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.participant)
    password_hash = Column(String(128), nullable=True)
    bio = Column(Text, nullable=True)
    skills = Column(JsonType, nullable=True)
    links = Column(JsonType, nullable=True)
    availability = Column(Text, nullable=True)
    looking_for_team = Column(Boolean, nullable=False, default=False)
    is_banned = Column(Boolean, nullable=False, default=False)
    banned_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    hackathons = relationship("Hackathon", back_populates="organizer")
    submissions = relationship("Submission", back_populates="submitter")
    registrations = relationship("Registration", back_populates="user")
    oauth_accounts = relationship("OAuthAccount", back_populates="user", cascade="all, delete-orphan")
    co_organized_hackathons = relationship(
        "HackathonOrganizer",
        back_populates="user",
        foreign_keys="HackathonOrganizer.user_id",
        cascade="all, delete-orphan",
    )
    assistant_conversations = relationship(
        "AssistantConversation",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User {self.email} role={self.role}>"


class OAuthAccount(Base):
    """An external OAuth identity (Google, GitHub, Discord) linked to a local user."""

    __tablename__ = "oauth_accounts"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    provider = Column(String(20), nullable=False)
    provider_user_id = Column(String(255), nullable=False)
    provider_email = Column(String(320), nullable=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    __table_args__ = (Index("ix_oauth_accounts_provider_user", "provider", "provider_user_id", unique=True),)

    user = relationship("User", back_populates="oauth_accounts")

    def __repr__(self) -> str:
        return f"<OAuthAccount {self.provider} user={self.user_id}>"


class Hackathon(Base):
    """A hackathon event with scheduling, venue info, Discord integration, and related tracks, teams, and workshops."""

    __tablename__ = "hackathons"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    name = Column(String(300), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    application_deadline = Column(DateTime(timezone=True), nullable=True)
    max_participants = Column(Integer, nullable=True)
    current_participants = Column(Integer, nullable=False, default=0)
    waitlist_enabled = Column(Boolean, nullable=False, default=False)
    organizer_id = Column(String(64), ForeignKey("users.id"), nullable=False)
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
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    organizer = relationship("User", back_populates="hackathons")
    submissions = relationship("Submission", back_populates="hackathon")
    registrations = relationship("Registration", back_populates="hackathon")
    co_organizers = relationship("HackathonOrganizer", back_populates="hackathon", cascade="all, delete-orphan")
    tracks = relationship("Track", back_populates="hackathon", cascade="all, delete-orphan")
    teams = relationship("Team", back_populates="hackathon", cascade="all, delete-orphan")
    workshops = relationship("Workshop", back_populates="hackathon", cascade="all, delete-orphan")
    sponsors = relationship("Sponsor", back_populates="hackathon", cascade="all, delete-orphan")
    prizes = relationship("Prize", back_populates="hackathon", cascade="all, delete-orphan")
    help_requests = relationship("HelpRequest", back_populates="hackathon", cascade="all, delete-orphan")
    assistant_conversations = relationship("AssistantConversation", back_populates="hackathon")
    assistant_documents = relationship("AssistantDocument", back_populates="hackathon", cascade="all, delete-orphan")
    registration_questions = relationship(
        "RegistrationQuestion", back_populates="hackathon", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Hackathon {self.name}>"


class Track(Base):
    """A challenge track or prize category within a hackathon with scoring criteria and resources."""

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
    resources_markdown = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    hackathon = relationship("Hackathon", back_populates="tracks")
    prizes = relationship("Prize", back_populates="track", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Track {self.name}>"


class Prize(Base):
    """A monetary or recognition prize offered within a hackathon, optionally linked to a track."""

    __tablename__ = "prizes"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id"), nullable=False)
    track_id = Column(Guid, ForeignKey("tracks.id"), nullable=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    amount = Column(String(100), nullable=True)
    currency = Column(String(10), nullable=False, default="USD")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    hackathon = relationship("Hackathon", back_populates="prizes")
    track = relationship("Track", back_populates="prizes")

    def __repr__(self) -> str:
        return f"<Prize {self.name}>"


class HelpRequest(Base):
    """A mentor help request submitted by a participant during a hackathon."""

    __tablename__ = "help_requests"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id"), nullable=False)
    requester_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="open")
    mentor_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    hackathon = relationship("Hackathon", back_populates="help_requests")
    requester = relationship("User", foreign_keys=[requester_id])
    mentor = relationship("User", foreign_keys=[mentor_id])

    def __repr__(self) -> str:
        return f"<HelpRequest {self.title} status={self.status}>"


class HackathonOrganizer(Base):
    """Many-to-many association linking co-organizers to hackathons with audit tracking."""

    __tablename__ = "hackathon_organizers"
    __table_args__ = (
        Index("ix_hackathon_organizers_hackathon", "hackathon_id"),
        Index("ix_hackathon_organizers_user", "user_id"),
    )

    hackathon_id = Column(Guid, ForeignKey("hackathons.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    added_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    added_by = Column(String(64), ForeignKey("users.id"), nullable=True)

    hackathon = relationship("Hackathon", back_populates="co_organizers")
    user = relationship("User", foreign_keys=[user_id], back_populates="co_organized_hackathons")


class Submission(Base):
    """A Devpost or GitHub project submission undergoing automated integrity analysis."""

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
    team_id = Column(Guid, ForeignKey("teams.id"), nullable=True, index=True)
    submitted_by = Column(String(64), ForeignKey("users.id"), nullable=True)
    status = Column(SAEnum(SubmissionStatus), nullable=False, default=SubmissionStatus.pending, index=True)
    risk_score = Column(Integer, nullable=True)
    verdict = Column(SAEnum(Verdict), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    access_token = Column(String(36), nullable=True)
    stage = Column(String(50), nullable=True)  # progress stage: scraping, cloning, checking, scoring
    check_progress = Column(
        JsonType, nullable=True
    )  # {completed: ["check1"], pending: ["check2", ...], current: "check name"}

    hackathon = relationship("Hackathon", back_populates="submissions")
    team = relationship("Team", back_populates="submissions")
    submitter = relationship("User", back_populates="submissions")
    check_results = relationship("CheckResultModel", back_populates="submission", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Submission {self.devpost_url}>"


class CheckResultModel(Base):
    """The outcome of a single automated integrity check run against a submission."""

    __tablename__ = "check_results"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    submission_id = Column(Guid, ForeignKey("submissions.id"), nullable=False)
    check_category = Column(String(100), nullable=False)
    check_name = Column(String(100), nullable=False)
    score = Column(Integer, nullable=False)
    status = Column(SAEnum(CheckStatus), nullable=False)
    details = Column(JsonType, nullable=True)
    evidence = Column(ArrayOfStrings, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    submission = relationship("Submission", back_populates="check_results")

    def __repr__(self) -> str:
        return f"<CheckResult {self.check_name} score={self.score}>"


class Registration(Base):
    """A participant's application and enrollment record for a specific hackathon."""

    __tablename__ = "registrations"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id"), nullable=False)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
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
    track_id = Column(Guid, ForeignKey("tracks.id"), nullable=True)
    registered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
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
    answers = relationship("RegistrationAnswer", cascade="all, delete-orphan", back_populates="registration")
    review_notes = relationship("RegistrationReviewNote", cascade="all, delete-orphan", back_populates="registration")

    def __repr__(self) -> str:
        return f"<Registration {self.id} status={self.status}>"


class RegistrationQuestion(Base):
    """A custom question that hackers answer during registration."""

    __tablename__ = "registration_questions"
    __table_args__ = (Index("ix_registration_questions_hackathon_id", "hackathon_id"),)

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(String(500), nullable=False)
    question_type = Column(SAEnum(QuestionType), nullable=False)
    options = Column(JsonType, nullable=True)  # JSON array of strings for select/multiselect
    is_required = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )

    hackathon = relationship("Hackathon", back_populates="registration_questions")
    answers = relationship("RegistrationAnswer", cascade="all, delete-orphan", back_populates="question")

    def __repr__(self) -> str:
        return f"<RegistrationQuestion {self.question_text[:30]}...>"


class RegistrationAnswer(Base):
    """A hacker's answer to a custom registration question."""

    __tablename__ = "registration_answers"
    __table_args__ = (
        Index("ix_registration_answers_registration_id", "registration_id"),
        Index("ix_registration_answers_question_id", "question_id"),
        Index("ix_registration_answers_unique", "registration_id", "question_id", unique=True),
    )

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    registration_id = Column(Guid, ForeignKey("registrations.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Guid, ForeignKey("registration_questions.id", ondelete="CASCADE"), nullable=False)
    answer_value = Column(Text, nullable=False)  # JSON string for structured answers, plain text for others
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )

    registration = relationship("Registration", back_populates="answers")
    question = relationship("RegistrationQuestion", back_populates="answers")

    def __repr__(self) -> str:
        return f"<RegistrationAnswer question={self.question_id}>"


class RegistrationReviewNote(Base):
    """An organizer's internal review note on a registration."""

    __tablename__ = "registration_review_notes"
    __table_args__ = (
        Index("ix_registration_review_notes_registration_id", "registration_id"),
        Index("ix_registration_review_notes_organizer_id", "organizer_id"),
    )

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    registration_id = Column(Guid, ForeignKey("registrations.id", ondelete="CASCADE"), nullable=False)
    organizer_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    note_text = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)  # 1-5, optional
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )

    registration = relationship("Registration", back_populates="review_notes")
    organizer = relationship("User", foreign_keys=[organizer_id])

    def __repr__(self) -> str:
        return f"<RegistrationReviewNote reg={self.registration_id} rating={self.rating}>"


class Team(Base):
    """A group of participants competing together in a hackathon.

    Each team has a unique join code and a designated captain who
    can manage memberships and submit projects on behalf of the team.
    """

    __tablename__ = "teams"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id"), nullable=False)
    name = Column(String(200), nullable=False)
    join_code = Column(String(16), nullable=False, unique=True, index=True)
    captain_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    hackathon = relationship("Hackathon", back_populates="teams")
    captain = relationship("User", foreign_keys=[captain_id])
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="team")

    def __repr__(self) -> str:
        return f"<Team {self.name}>"


class TeamMember(Base):
    """Associative table linking users to teams.

    Records when a user joined so that organizers can see team
    formation timelines.
    """

    __tablename__ = "team_members"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    team_id = Column(Guid, ForeignKey("teams.id"), nullable=False)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    team = relationship("Team", back_populates="members")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<TeamMember team={self.team_id} user={self.user_id}>"


class Workshop(Base):
    """A scheduled educational session during a hackathon.

    Workshops have start and end times, location, and an optional
    speaker name for display on the event schedule.
    """

    __tablename__ = "workshops"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    location = Column(String(200), nullable=True)
    speaker_name = Column(String(200), nullable=True)
    max_capacity = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    hackathon = relationship("Hackathon", back_populates="workshops")
    rsvps = relationship("WorkshopRSVP", back_populates="workshop", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Workshop {self.title}>"


class WorkshopRSVP(Base):
    """A participant RSVP for a workshop with attendance tracking."""

    __tablename__ = "workshop_rsvps"
    __table_args__ = (
        Index("ix_workshop_rsvps_workshop", "workshop_id"),
        Index("ix_workshop_rsvps_user", "user_id"),
        Index("ix_workshop_rsvps_hackathon", "hackathon_id"),
    )

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    workshop_id = Column(Guid, ForeignKey("workshops.id", ondelete="CASCADE"), nullable=False)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False)
    status = Column(SAEnum(WorkshopRSVPStatus), nullable=False, default=WorkshopRSVPStatus.registered)
    registered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    attended_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User")
    workshop = relationship("Workshop", back_populates="rsvps")
    hackathon = relationship("Hackathon")

    def __repr__(self) -> str:
        return f"<WorkshopRSVP user={self.user_id} workshop={self.workshop_id} status={self.status}>"


class Sponsor(Base):
    """An organization sponsoring a hackathon.

    Sponsors are displayed by tier (e.g., platinum, gold, silver) and
    can include a logo, website link, and description.
    """

    __tablename__ = "sponsors"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id"), nullable=False)
    name = Column(String(200), nullable=False)
    tier = Column(String(50), nullable=False, default="silver")
    logo_url = Column(Text, nullable=True)
    website_url = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    hackathon = relationship("Hackathon", back_populates="sponsors")

    def __repr__(self) -> str:
        return f"<Sponsor {self.name}>"


class Scan(Base):
    """An attendance or check-in record for a registration.

    Each scan is tied to a registration and records the type (e.g.,
    checkin, meal) and timestamp for auditing purposes.
    """

    __tablename__ = "scans"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    registration_id = Column(Guid, ForeignKey("registrations.id"), nullable=False)
    scan_type = Column(String(50), nullable=False, default="checkin")
    scanned_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    registration = relationship("Registration", back_populates="scans")

    def __repr__(self) -> str:
        return f"<Scan {self.id} type={self.scan_type}>"


class CrawledHackathon(Base):
    """A hackathon discovered by crawling Devpost.

    Stores the Devpost URL and last crawl time so that the scheduler
    knows which events should be refreshed for late submissions.
    """

    __tablename__ = "crawled_hackathons"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    devpost_url = Column(Text, unique=True, nullable=False)
    name = Column(String(300), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    submission_count = Column(Integer, nullable=True)
    last_crawled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    projects = relationship("CrawledProject", back_populates="hackathon", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<CrawledHackathon {self.name}>"


class CrawledProject(Base):
    """A project page discovered by crawling Devpost.

    Mirrors the Submission model structure but represents data found
    during proactive crawling rather than user-initiated analysis.
    """

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
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

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
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    rubric = relationship("Rubric", back_populates="session", uselist=False, cascade="all, delete-orphan")
    assignments = relationship("JudgeAssignment", back_populates="session", cascade="all, delete-orphan")


class Rubric(Base):
    """A scoring framework used during judging.

    A rubric belongs to exactly one judging session and contains
    weighted criteria that determine how projects are evaluated.
    """

    __tablename__ = "rubrics"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    session_id = Column(Guid, ForeignKey("judging_sessions.id"), unique=True, nullable=False)
    name = Column(String(200), nullable=False, default="Default Rubric")

    session = relationship("JudgingSession", back_populates="rubric")
    criteria = relationship("RubricCriterion", back_populates="rubric", cascade="all, delete-orphan")


class RubricCriterion(Base):
    """An individual scoring dimension within a rubric.

    Each criterion has a maximum score, weight, and sort order so
    that judges can provide granular feedback on different aspects
    of a project.
    """

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
    """Mapping of a judge to a specific submission for scoring.

    Tracks whether the assignment has been opened, completed, and
    when scores were submitted.
    """

    __tablename__ = "judge_assignments"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    session_id = Column(Guid, ForeignKey("judging_sessions.id"), nullable=False)
    judge_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    submission_id = Column(Guid, ForeignKey("submissions.id"), nullable=False)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    is_completed = Column(Integer, nullable=False, default=0)

    session = relationship("JudgingSession", back_populates="assignments")
    scores = relationship("Score", back_populates="assignment", cascade="all, delete-orphan")


class Score(Base):
    """A numeric rating given by a judge for a single rubric criterion.

    Also records whether the score was auto-submitted when time expired.
    """

    __tablename__ = "scores"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    assignment_id = Column(Guid, ForeignKey("judge_assignments.id"), nullable=False)
    criterion_id = Column(Guid, ForeignKey("rubric_criteria.id"), nullable=False)
    score = Column(Integer, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    is_auto_submitted = Column(Integer, nullable=False, default=0)

    assignment = relationship("JudgeAssignment", back_populates="scores")


class JudgeRating(Base):
    """Performance statistics for a judge based on historical scoring.

    Uses an Elo-style rating and aggregates raw score distributions
    to identify unusually lenient or strict judges.
    """

    __tablename__ = "judge_ratings"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    judge_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id"), nullable=False)
    rating = Column(Integer, nullable=False, default=1500)
    projects_scored = Column(Integer, nullable=False, default=0)
    mean_raw_score = Column(Integer, nullable=True)
    stddev_raw_score = Column(Integer, nullable=True)


class Announcement(Base):
    """A broadcast message from organizers to all participants.

    Announcements support priority levels so that urgent messages
    can be visually distinguished in the UI.
    """

    __tablename__ = "announcements"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False, default="normal")  # low, normal, high, urgent
    sent_by = Column(String(64), ForeignKey("users.id"), nullable=False)
    sent_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class ConflictOfInterest(Base):
    """A judge's declaration that they should not score a specific submission.

    Records the reason and timestamp so that the assignment algorithm
    can exclude the judge from the affected project.
    """

    __tablename__ = "conflicts_of_interest"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    judge_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id"), nullable=False)
    submission_id = Column(Guid, ForeignKey("submissions.id"), nullable=False)
    reason = Column(Text, nullable=True)
    declared_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


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
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class SimilarityMatch(Base):
    """A detected similarity relationship between two submissions.

    Stores the similarity score, Hamming distance, matching file list,
    and review status so that organizers can confirm or dismiss matches.
    """

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
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(String(64), ForeignKey("users.id"), nullable=True)


class EmailLog(Base):
    """Audit trail for every email sent by the platform.

    Tracks the recipient, template type, delivery status, retry count,
    and any error messages for debugging deliverability issues.
    """

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
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(UTC))

    registration = relationship("Registration", back_populates="email_logs")


class ContentPage(Base):
    """An organizer-editable markdown page displayed in the UI.

    Pages are grouped into tabs (e.g., resources) and ordered within
    the tab so that static content can be customized per hackathon.
    """

    __tablename__ = "content_pages"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    slug = Column(String(100), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    tab_group = Column(String(50), nullable=False, default="resources")
    sort_order = Column(Integer, default=0, nullable=False)
    tab_group_order = Column(Integer, default=0, nullable=False)
    is_published = Column(Boolean, default=True, nullable=False)
    created_by = Column(String(64), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(UTC), nullable=True)

    __table_args__ = (
        Index("ix_content_pages_slug", "slug"),
        Index("ix_content_pages_tab_group", "tab_group", "sort_order"),
        Index("ix_content_pages_published", "is_published"),
    )


class SiteConfig(Base):
    """A global key-value configuration entry.

    Used for feature flags, branding overrides, and other settings
    that should persist across application restarts.
    """

    __tablename__ = "site_config"

    key = Column(String(64), primary_key=True, nullable=False)
    value = Column(Text, nullable=False)
    category = Column(String(32), default="general", nullable=False, index=True)
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )
    description = Column(String(255), nullable=True)


class Event(Base):
    """An internal event record for asynchronous webhook processing.

    Stores the event type and payload so that webhook subscriptions
    can be delivered reliably with retries.
    """

    __tablename__ = "events"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    type = Column(String(64), nullable=False, index=True)
    payload = Column(JsonType, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    def __repr__(self) -> str:
        return f"<Event {self.type}>"


class WebhookSubscription(Base):
    """A third-party URL that wants to receive event notifications.

    Subscriptions define which event types to receive and a shared
    secret for HMAC signature verification.
    """

    __tablename__ = "webhook_subscriptions"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    url = Column(String(500), nullable=False)
    secret = Column(String(128), nullable=False)
    events = Column(ArrayOfStrings, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    def __repr__(self) -> str:
        return f"<WebhookSubscription {self.url}>"


class WebhookDeliveryLog(Base):
    """Record of a single attempt to deliver a webhook payload.

    Stores the HTTP status code and response body so that subscription
    owners can debug delivery failures.
    """

    __tablename__ = "webhook_delivery_logs"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    subscription_id = Column(Guid, ForeignKey("webhook_subscriptions.id"), nullable=False)
    event_id = Column(Guid, ForeignKey("events.id"), nullable=False)
    status = Column(String(20), nullable=False)  # success, failed, retrying
    http_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    def __repr__(self) -> str:
        return f"<WebhookDeliveryLog {self.status}>"


class Plugin(Base):
    """A registered extension or integration in the system.

    Plugins can be enabled or disabled independently and store
    configuration as JSON for flexible third-party integrations.
    """

    __tablename__ = "plugins"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    version = Column(String(50), nullable=False, default="0.1.0")
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    config = Column(JsonType, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    def __repr__(self) -> str:
        return f"<Plugin {self.name}>"


class Notification(Base):
    """An in-app notification sent to a user with optional hackathon scope and action link.

    Notifications support read tracking so the UI can display unread
    badges and filter by read state.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_id", "user_id"),
        Index("ix_notifications_hackathon_id", "hackathon_id"),
        Index("ix_notifications_read_at", "read_at"),
        Index("ix_notifications_created_at", "created_at"),
    )

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(SAEnum(NotificationType), nullable=False, default=NotificationType.info)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    action_url = Column(Text, nullable=True)
    action_text = Column(String(100), nullable=True)

    user = relationship("User")
    hackathon = relationship("Hackathon")

    def __repr__(self) -> str:
        return f"<Notification user={self.user_id} type={self.type} read={self.read_at is not None}>"


class TeamFinderPost(Base):
    """A post by a hacker looking for a team or looking for team members."""

    __tablename__ = "team_finder_posts"
    __table_args__ = (
        Index("ix_team_finder_posts_hackathon", "hackathon_id"),
        Index("ix_team_finder_posts_user", "user_id"),
        Index("ix_team_finder_posts_active", "hackathon_id", "is_active"),
    )

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id"), nullable=False)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    post_type = Column(String(30), nullable=False)  # looking_for_team | looking_for_members
    skills_needed = Column(ArrayOfStrings, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    hackathon = relationship("Hackathon")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<TeamFinderPost {self.post_type} user={self.user_id}>"


class MentorshipRequest(Base):
    """A request for mentorship during a hackathon."""

    __tablename__ = "mentorship_requests"
    __table_args__ = (
        Index("ix_mentorship_requests_hackathon", "hackathon_id"),
        Index("ix_mentorship_requests_requester", "requester_id"),
        Index("ix_mentorship_requests_mentor", "mentor_id"),
    )

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id"), nullable=False)
    requester_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    mentor_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    topic = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="pending")  # pending, accepted, completed, cancelled
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)

    hackathon = relationship("Hackathon")
    requester = relationship("User", foreign_keys=[requester_id])
    mentor = relationship("User", foreign_keys=[mentor_id])

    def __repr__(self) -> str:
        return f"<MentorshipRequest {self.status} requester={self.requester_id}>"


class PublicVote(Base):
    """A people's choice vote cast by a participant for a submission."""

    __tablename__ = "public_votes"
    __table_args__ = (
        Index("ix_public_votes_hackathon", "hackathon_id"),
        Index("ix_public_votes_submission", "submission_id"),
        Index("ix_public_votes_voter", "voter_id"),
        Index("ix_public_votes_unique", "hackathon_id", "voter_id", unique=True),
    )

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id"), nullable=False)
    submission_id = Column(Guid, ForeignKey("submissions.id"), nullable=False)
    voter_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    hackathon = relationship("Hackathon")
    submission = relationship("Submission")
    voter = relationship("User")

    def __repr__(self) -> str:
        return f"<PublicVote submission={self.submission_id} voter={self.voter_id}>"


class PrizeAward(Base):
    """A record of a prize being awarded to a specific team."""

    __tablename__ = "prize_awards"
    __table_args__ = (
        Index("ix_prize_awards_prize_id", "prize_id"),
        Index("ix_prize_awards_team_id", "team_id"),
        Index("ix_prize_awards_hackathon_id", "hackathon_id"),
    )

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    prize_id = Column(Guid, ForeignKey("prizes.id", ondelete="CASCADE"), nullable=False)
    team_id = Column(Guid, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False)
    awarded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    awarded_by = Column(String(64), ForeignKey("users.id"), nullable=False)

    prize = relationship("Prize")
    team = relationship("Team")
    hackathon = relationship("Hackathon")

    def __repr__(self) -> str:
        return f"<PrizeAward prize={self.prize_id} team={self.team_id}>"


class DemoSlot(Base):
    """A scheduled time slot for a team to demo or pitch their project."""

    __tablename__ = "demo_slots"
    __table_args__ = (
        Index("ix_demo_slots_hackathon_id", "hackathon_id"),
        Index("ix_demo_slots_submission_id", "submission_id"),
    )

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False)
    submission_id = Column(Guid, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    room = Column(String(200), nullable=True)
    judge_panel_id = Column(String(64), nullable=True)
    status = Column(String(20), nullable=False, default="scheduled")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    hackathon = relationship("Hackathon")
    submission = relationship("Submission")

    def __repr__(self) -> str:
        return f"<DemoSlot hackathon={self.hackathon_id} room={self.room}>"


class SponsorBooth(Base):
    """A sponsor booth assignment at a hackathon with lead scanning capability."""

    __tablename__ = "sponsor_booths"
    __table_args__ = (
        Index("ix_sponsor_booths_hackathon_id", "hackathon_id"),
        Index("ix_sponsor_booths_sponsor_id", "sponsor_id"),
    )

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False)
    sponsor_id = Column(Guid, ForeignKey("sponsors.id", ondelete="CASCADE"), nullable=False)
    booth_number = Column(String(50), nullable=True)
    lead_scan_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    hackathon = relationship("Hackathon")
    sponsor = relationship("Sponsor")

    def __repr__(self) -> str:
        return f"<SponsorBooth sponsor={self.sponsor_id} booth={self.booth_number}>"


class MealSlot(Base):
    """A scheduled meal service window at a hackathon."""

    __tablename__ = "meal_slots"
    __table_args__ = (Index("ix_meal_slots_hackathon_id", "hackathon_id"),)

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False)
    meal_type = Column(String(50), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    location = Column(String(200), nullable=True)
    max_capacity = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    hackathon = relationship("Hackathon")
    rsvps = relationship("MealRSVP", back_populates="meal_slot", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<MealSlot {self.meal_type} hackathon={self.hackathon_id}>"


class MealRSVP(Base):
    """A participant RSVP for a meal slot with dietary restriction tracking."""

    __tablename__ = "meal_rsvps"
    __table_args__ = (
        Index("ix_meal_rsvps_meal_slot_id", "meal_slot_id"),
        Index("ix_meal_rsvps_user_id", "user_id"),
        Index("ix_meal_rsvps_unique", "meal_slot_id", "user_id", unique=True),
    )

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    meal_slot_id = Column(Guid, ForeignKey("meal_slots.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    dietary_restrictions = Column(String(500), nullable=True)
    registered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    meal_slot = relationship("MealSlot", back_populates="rsvps")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<MealRSVP user={self.user_id} meal={self.meal_slot_id}>"


class VolunteerShift(Base):
    """A volunteer shift assignment at a hackathon with check-in tracking."""

    __tablename__ = "volunteer_shifts"
    __table_args__ = (
        Index("ix_volunteer_shifts_hackathon_id", "hackathon_id"),
        Index("ix_volunteer_shifts_volunteer_id", "volunteer_id"),
    )

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False)
    volunteer_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    shift_name = Column(String(200), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    location = Column(String(200), nullable=True)
    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    hackathon = relationship("Hackathon")
    volunteer = relationship("User", foreign_keys=[volunteer_id])

    def __repr__(self) -> str:
        return f"<VolunteerShift volunteer={self.volunteer_id} shift={self.shift_name}>"


class Survey(Base):
    """A post-event survey for a hackathon with customizable questions."""

    __tablename__ = "surveys"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    questions_json = Column(JsonType, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    hackathon = relationship("Hackathon")
    responses = relationship("SurveyResponse", back_populates="survey", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Survey {self.title}>"


class SurveyResponse(Base):
    """A single response to a survey, including NPS score."""

    __tablename__ = "survey_responses"
    __table_args__ = (
        Index("ix_survey_responses_survey_id", "survey_id"),
        Index("ix_survey_responses_user_id", "user_id"),
    )

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    survey_id = Column(Guid, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    answers_json = Column(JsonType, nullable=False)
    submitted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    nps_score = Column(Integer, nullable=True)

    survey = relationship("Survey", back_populates="responses")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<SurveyResponse survey={self.survey_id} user={self.user_id}>"


class AuditLog(Base):
    """Centralized audit log for platform actions."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_hackathon_id", "hackathon_id"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=True)
    entity_id = Column(String(100), nullable=True)
    details_json = Column(JsonType, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    user = relationship("User")
    hackathon = relationship("Hackathon")

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} entity={self.entity_type}:{self.entity_id}>"


class ChatMessage(Base):
    """A message in the participant-to-organizer chat system.

    Messages are scoped to a hackathon and support read receipts so
    organizers can see which messages have been addressed.
    """

    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_hackathon_id", "hackathon_id"),
        Index("ix_chat_messages_sender_id", "sender_id"),
        Index("ix_chat_messages_recipient_id", "recipient_id"),
        Index("ix_chat_messages_created_at", "created_at"),
    )

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recipient_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    hackathon = relationship("Hackathon")
    sender = relationship("User", foreign_keys=[sender_id])
    recipient = relationship("User", foreign_keys=[recipient_id])

    def __repr__(self) -> str:
        return f"<ChatMessage hackathon={self.hackathon_id} sender={self.sender_id}>"


# Import assistant models to ensure they are registered with SQLAlchemy
# This must be at the end to avoid circular imports
from app.models_assistant import AssistantConversation, AssistantDocument, AssistantMessage  # noqa: E402, F401
