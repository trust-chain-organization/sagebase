"""SQLAlchemy ORM models for database tables.

This module contains proper SQLAlchemy declarative models for tables that
previously used Pydantic models or dummy dynamic models. This allows the
repository pattern to use ORM features instead of raw SQL.
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class ParliamentaryGroupMembershipModel(Base):
    """SQLAlchemy model for parliamentary_group_memberships table."""

    __tablename__ = "parliamentary_group_memberships"

    id: Mapped[int] = mapped_column(primary_key=True)
    politician_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("politicians.id", use_alter=True, name="fk_pgm_politician")
    )
    parliamentary_group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("parliamentary_groups.id", use_alter=True, name="fk_pgm_group"),
    )
    start_date: Mapped[date] = mapped_column()
    end_date: Mapped[date | None] = mapped_column()
    role: Mapped[str | None] = mapped_column(String(100))
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.user_id", use_alter=True, name="fk_pgm_user")
    )
    is_manually_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    latest_extraction_log_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("extraction_logs.id", use_alter=True, name="fk_pgm_extraction_log"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="chk_membership_end_date_after_start",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ParliamentaryGroupMembershipModel("
            f"id={self.id}, "
            f"politician_id={self.politician_id}, "
            f"parliamentary_group_id={self.parliamentary_group_id}, "
            f"start_date={self.start_date}, "
            f"end_date={self.end_date}"
            f")>"
        )


class UserModel(Base):
    """SQLAlchemy model for users table (minimal definition for FK support)."""

    __tablename__ = "users"

    user_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str] = mapped_column(String(255))

    def __repr__(self) -> str:
        return f"<UserModel(user_id={self.user_id}, email={self.email})>"


class PoliticianModel(Base):
    """SQLAlchemy model for politicians table (minimal definition for FK support)."""

    __tablename__ = "politicians"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))

    def __repr__(self) -> str:
        return f"<PoliticianModel(id={self.id}, name={self.name})>"


class ParliamentaryGroupModel(Base):
    """SQLAlchemy model for parliamentary_groups table."""

    __tablename__ = "parliamentary_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    conference_id: Mapped[int] = mapped_column(Integer)
    url: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column()
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<ParliamentaryGroupModel("
            f"id={self.id}, "
            f"name={self.name}, "
            f"conference_id={self.conference_id}"
            f")>"
        )


class ExtractedParliamentaryGroupMemberModel(Base):
    """SQLAlchemy model for extracted_parliamentary_group_members table."""

    __tablename__ = "extracted_parliamentary_group_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    parliamentary_group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("parliamentary_groups.id", use_alter=True, name="fk_epgm_group"),
    )
    extracted_name: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str] = mapped_column(String(500))
    extracted_role: Mapped[str | None] = mapped_column(String(100))
    extracted_party_name: Mapped[str | None] = mapped_column(String(200))
    extracted_district: Mapped[str | None] = mapped_column(String(200))
    extracted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    matched_politician_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("politicians.id", use_alter=True, name="fk_epgm_politician"),
    )
    matching_confidence: Mapped[float | None] = mapped_column()  # 0.0-1.0
    matching_status: Mapped[str] = mapped_column(String(20), default="pending")
    matched_at: Mapped[datetime | None] = mapped_column(DateTime)
    additional_info: Mapped[str | None] = mapped_column(String(1000))

    def __repr__(self) -> str:
        return (
            f"<ExtractedParliamentaryGroupMemberModel("
            f"id={self.id}, "
            f"extracted_name={self.extracted_name}, "
            f"matching_status={self.matching_status}"
            f")>"
        )


class PoliticianOperationLogModel(Base):
    """SQLAlchemy model for politician_operation_logs table."""

    __tablename__ = "politician_operation_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    politician_id: Mapped[int] = mapped_column(Integer, nullable=False)
    politician_name: Mapped[str] = mapped_column(String(255), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.user_id", use_alter=True, name="fk_pol_log_user")
    )
    operation_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    operated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "operation_type IN ('create', 'update', 'delete')",
            name="check_operation_type",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<PoliticianOperationLogModel("
            f"id={self.id}, "
            f"politician_id={self.politician_id}, "
            f"politician_name={self.politician_name}, "
            f"operation_type={self.operation_type}"
            f")>"
        )
