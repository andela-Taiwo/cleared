"""SQLAlchemy models.

Primary keys are UUIDv7: unguessable in a URL, and time-ordered so that the primary key index
stays compact on insert. PostgreSQL 18 has `uuidv7()`; this project supports older servers, so
the value is generated in the application.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from cleared.db.base import Base, CreatedAtMixin, TimestampsMixin

__all__ = [
    "AuthSession",
    "CredentialType",
    "Employee",
    "EmployeeCredential",
    "JobRole",
    "Organization",
    "ReminderEvent",
    "ReminderRule",
    "RoleRequirement",
    "User",
]


class Organization(TimestampsMixin, Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    # Every date the product shows a user is a date in the agency's timezone, never UTC.
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default=text("'America/New_York'")
    )


class User(TimestampsMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("organization_id", "email"),
        CheckConstraint("role in ('admin', 'coordinator', 'viewer')", name="role_allowed"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'coordinator'")
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthSession(CreatedAtMixin, Base):
    """A signed-in browser.

    Global rather than tenant-owned: the session is how a request learns its tenant. The row
    holds no personal data beyond a user id and an optional user agent.
    """

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Denormalised on purpose: the session has to name its tenant before any tenant-scoped
    # table can be read, and `users` is one of those tables.
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(String(400))
    ip: Mapped[str | None] = mapped_column(String(64))


class JobRole(TimestampsMixin, Base):
    """A kind of worker the agency deploys: CNA, HHA, RN, LPN, PT…"""

    __tablename__ = "job_roles"
    __table_args__ = (UniqueConstraint("organization_id", "code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)


class Employee(TimestampsMixin, Base):
    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint("organization_id", "employee_no"),
        CheckConstraint("status in ('active', 'inactive', 'onboarding')", name="status_allowed"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    employee_no: Mapped[str | None] = mapped_column(String(40))
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(40))
    job_role_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_roles.id", ondelete="RESTRICT"), index=True
    )
    location: Mapped[str | None] = mapped_column(String(120))
    hired_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'active'"))

    job_role: Mapped[JobRole | None] = relationship(lazy="joined")


class CredentialType(TimestampsMixin, Base):
    """A kind of evidence: RN licence, CPR card, TB test, background check…"""

    __tablename__ = "credential_types"
    __table_args__ = (
        UniqueConstraint("organization_id", "code"),
        CheckConstraint(
            "category in ('license', 'certification', 'clearance', 'health', 'training')",
            name="category_allowed",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    issuing_authority: Mapped[str | None] = mapped_column(String(160))
    validity_months: Mapped[int | None] = mapped_column(Integer)
    requires_document: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )


class EmployeeCredential(TimestampsMixin, Base):
    """One piece of evidence, held by one person, with its own expiry date."""

    __tablename__ = "employee_credentials"
    __table_args__ = (
        CheckConstraint(
            "expires_on is null or issued_on is null or expires_on >= issued_on",
            name="dates_ordered",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), index=True
    )
    credential_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("credential_types.id", ondelete="RESTRICT"), index=True
    )
    identifier: Mapped[str | None] = mapped_column(String(80))
    issued_on: Mapped[date | None] = mapped_column(Date)
    expires_on: Mapped[date | None] = mapped_column(Date, index=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    notes: Mapped[str | None] = mapped_column(Text)

    credential_type: Mapped[CredentialType] = relationship(lazy="joined")


class RoleRequirement(CreatedAtMixin, Base):
    """A row exists exactly when the role requires the credential type."""

    __tablename__ = "role_requirements"
    __table_args__ = (UniqueConstraint("organization_id", "job_role_id", "credential_type_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    job_role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_roles.id", ondelete="CASCADE"), index=True
    )
    credential_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("credential_types.id", ondelete="CASCADE")
    )


class ReminderRule(TimestampsMixin, Base):
    __tablename__ = "reminder_rules"
    __table_args__ = (
        UniqueConstraint("organization_id", "days_before", "audience"),
        CheckConstraint("days_before >= 0 and days_before <= 365", name="days_in_range"),
        CheckConstraint("audience in ('employee', 'coordinator', 'both')", name="audience_allowed"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    days_before: Mapped[int] = mapped_column(Integer, nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'email'"))
    audience: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))


class ReminderEvent(CreatedAtMixin, Base):
    __tablename__ = "reminder_events"
    __table_args__ = (
        UniqueConstraint("employee_credential_id", "rule_id", "due_on", "recipient", name="dedupe"),
        CheckConstraint("status in ('queued', 'sent', 'failed', 'skipped')", name="status_allowed"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    employee_credential_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employee_credentials.id", ondelete="CASCADE")
    )
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reminder_rules.id", ondelete="SET NULL")
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE")
    )
    due_on: Mapped[date] = mapped_column(Date, nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    recipient: Mapped[str] = mapped_column(String(320), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'queued'"))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
