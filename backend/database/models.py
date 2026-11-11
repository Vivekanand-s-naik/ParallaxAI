"""
SQLAlchemy 2.0 ORM Models for ParallaxAI.
Covers Authentication, RBAC Authorization, and the Human-AI Co-Governance Platform.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================================
# 1. AUTHENTICATION & AUTHORIZATION MODELS
# ============================================================================


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auth_provider: Mapped[str] = mapped_column(
        String(50), default="local", nullable=False
    )
    google_sub: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    preferences: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}", nullable=False
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user_roles: Mapped[List["UserRoleORM"]] = relationship(
        "UserRoleORM",
        back_populates="user",
        foreign_keys="UserRoleORM.user_id",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    refresh_tokens: Mapped[List["RefreshTokenORM"]] = relationship(
        "RefreshTokenORM",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    password_reset_tokens: Mapped[List["PasswordResetTokenORM"]] = relationship(
        "PasswordResetTokenORM",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def roles(self) -> List["RoleORM"]:
        return [ur.role for ur in self.user_roles if ur.role is not None]

    @property
    def role_names(self) -> List[str]:
        return [r.name for r in self.roles]

    @property
    def primary_role(self) -> str:
        names = self.role_names
        if not names:
            return "VIEWER"
        priority = [
            "SUPER_ADMIN",
            "ADMIN",
            "GOVERNANCE_OFFICER",
            "HUMAN_REVIEWER",
            "ANALYST",
            "VIEWER",
        ]
        for p in priority:
            if p in names:
                return p
        return names[0]


class RoleORM(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user_roles: Mapped[List["UserRoleORM"]] = relationship(
        "UserRoleORM", back_populates="role", cascade="all, delete-orphan"
    )
    role_permissions: Mapped[List["RolePermissionORM"]] = relationship(
        "RolePermissionORM",
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def permissions(self) -> List["PermissionORM"]:
        return [
            rp.permission for rp in self.role_permissions if rp.permission is not None
        ]


class PermissionORM(Base):
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    module: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False
    )

    role_permissions: Mapped[List["RolePermissionORM"]] = relationship(
        "RolePermissionORM", back_populates="permission", cascade="all, delete-orphan"
    )


class UserRoleORM(Base):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    assigned_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False
    )

    user: Mapped["UserORM"] = relationship(
        "UserORM", back_populates="user_roles", foreign_keys=[user_id]
    )
    role: Mapped["RoleORM"] = relationship(
        "RoleORM", back_populates="user_roles", lazy="selectin"
    )


class RolePermissionORM(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_perm"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False
    )

    role: Mapped["RoleORM"] = relationship("RoleORM", back_populates="role_permissions")
    permission: Mapped["PermissionORM"] = relationship(
        "PermissionORM", back_populates="role_permissions", lazy="selectin"
    )


class RefreshTokenORM(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, index=True, nullable=False
    )
    is_revoked: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    replaced_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False
    )

    user: Mapped["UserORM"] = relationship("UserORM", back_populates="refresh_tokens")


class PasswordResetTokenORM(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False
    )

    user: Mapped["UserORM"] = relationship(
        "UserORM", back_populates="password_reset_tokens"
    )


# ============================================================================
# 2. GOVERNANCE PLATFORM MODELS
# ============================================================================


class AgentORM(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(150), unique=True, index=True, nullable=False
    )
    type: Mapped[str] = mapped_column(
        String(32), index=True, nullable=False
    )  # "ai" | "human"
    provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    role: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_threshold: Mapped[float] = mapped_column(
        Float, default=0.5, nullable=False
    )
    influence_weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    vote_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_confidence: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, index=True, nullable=False
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
        nullable=False,
    )

    votes: Mapped[List["VoteORM"]] = relationship(
        "VoteORM", back_populates="agent", cascade="all, delete-orphan"
    )
    participations: Mapped[List["DecisionParticipantORM"]] = relationship(
        "DecisionParticipantORM", back_populates="agent", cascade="all, delete-orphan"
    )


class GovernanceRuleORM(Base):
    __tablename__ = "governance_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(
        String(150), unique=True, index=True, nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str] = mapped_column(
        String(64), default="general", index=True, nullable=False
    )
    policy_type: Mapped[str] = mapped_column(
        String(64), default="threshold", nullable=False
    )
    rule_definition: Mapped[str] = mapped_column(Text, nullable=False)
    approval_threshold: Mapped[float] = mapped_column(
        Float, default=0.7, nullable=False
    )
    require_human_review: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    escalation_target: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, index=True, nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    applied_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
        nullable=False,
    )


class DecisionORM(Base):
    __tablename__ = "decisions"
    __table_args__ = (
        Index("ix_decisions_status_priority", "status", "priority"),
        Index("ix_decisions_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    application_type: Mapped[str] = mapped_column(
        String(64), default="general", index=True, nullable=False
    )
    priority: Mapped[str] = mapped_column(
        String(32), default="medium", index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default="pending", index=True, nullable=False
    )
    applicant_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}", nullable=False
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}", nullable=False
    )
    bias_score: Mapped[float] = mapped_column(
        Float, default=0.0, index=True, nullable=False
    )
    risk_level: Mapped[str] = mapped_column(
        String(32), default="low", index=True, nullable=False
    )
    ai_recommendation: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    consensus_status: Mapped[str] = mapped_column(
        String(64), default="pending", nullable=False
    )
    consensus_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    human_override: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    reviewed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    governance_rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("governance_rules.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
        nullable=False,
    )

    votes: Mapped[List["VoteORM"]] = relationship(
        "VoteORM",
        back_populates="decision",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    participants: Mapped[List["DecisionParticipantORM"]] = relationship(
        "DecisionParticipantORM",
        back_populates="decision",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    audit_logs: Mapped[List["AuditLogORM"]] = relationship(
        "AuditLogORM", back_populates="decision"
    )


class DecisionParticipantORM(Base):
    __tablename__ = "decision_participants"
    __table_args__ = (
        UniqueConstraint(
            "decision_id", "agent_id", name="uq_decision_participants_decision_agent"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    participation_status: Mapped[str] = mapped_column(
        String(32), default="assigned", nullable=False
    )  # "assigned" | "voted" | "abstained"
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False
    )

    decision: Mapped["DecisionORM"] = relationship(
        "DecisionORM", back_populates="participants"
    )
    agent: Mapped["AgentORM"] = relationship(
        "AgentORM", back_populates="participations", lazy="selectin"
    )


class VoteORM(Base):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("decision_id", "agent_id", name="uq_votes_decision_agent"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    submitted_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    vote: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # "accept" | "reject" | "abstain"
    recommendation: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    bias_indicators: Mapped[List[str]] = mapped_column(
        JSONB, default=list, server_default="[]", nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        index=True,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
        nullable=False,
    )

    decision: Mapped["DecisionORM"] = relationship("DecisionORM", back_populates="votes")
    agent: Mapped["AgentORM"] = relationship(
        "AgentORM", back_populates="votes", lazy="selectin"
    )


class AuditLogORM(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    decision_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    actor_agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    actor_name: Mapped[str] = mapped_column(
        String(150), default="system", nullable=False
    )
    actor_type: Mapped[str] = mapped_column(
        String(32), default="system", index=True, nullable=False
    )  # "user" | "ai_agent" | "human_agent" | "system"
    event_type: Mapped[str] = mapped_column(
        String(64), default="decision_event", index=True, nullable=False
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    previous_status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    new_status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    agent_actions: Mapped[List[str]] = mapped_column(
        JSONB, default=list, server_default="[]", nullable=False
    )
    rules_applied: Mapped[List[str]] = mapped_column(
        JSONB, default=list, server_default="[]", nullable=False
    )
    compliance_status: Mapped[str] = mapped_column(
        String(32), default="compliant", index=True, nullable=False
    )
    audit_hash: Mapped[str] = mapped_column(
        String(128), index=True, nullable=False
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}", nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        index=True,
        nullable=False,
    )

    decision: Mapped[Optional["DecisionORM"]] = relationship(
        "DecisionORM", back_populates="audit_logs"
    )


class NotificationORM(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    type: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False
    )  # bias_alert | human_override | decision_approved | rule_violation | system_alert | voting_update | escalation
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(
        String(32), default="medium", index=True, nullable=False
    )  # low | medium | high | critical
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True, nullable=False
    )
    recipient_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    related_decision_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}", nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        index=True,
        nullable=False,
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

