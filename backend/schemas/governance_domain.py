"""
Pydantic v2 schemas for the ParallaxAI Governance Platform domain:
Decisions, Agents, Votes, Governance Rules, Bias & Fairness, Audit Logs, Notifications, and System Stats.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator
import yaml


class AgentOut(BaseModel):
    id: str
    uuid: uuid.UUID
    code: str
    name: str
    type: Literal["ai", "human"]
    provider: Optional[str] = None
    model_version: Optional[str] = None
    role: str
    description: Optional[str] = None
    confidence_threshold: float = 0.5
    influence_weight: float = 1.0
    vote_count: int = 0
    average_confidence: float = 0.0
    is_active: bool = True
    user_id: Optional[uuid.UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class AgentCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    code: Optional[str] = Field(default=None, max_length=64)
    type: Literal["ai", "human"] = "ai"
    provider: Optional[str] = Field(default=None, max_length=64)
    model_version: Optional[str] = Field(default=None, max_length=100)
    role: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = Field(default=None, max_length=2000)
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    influence_weight: float = Field(default=1.0, ge=0.1, le=5.0)
    is_active: bool = True
    user_id: Optional[uuid.UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    provider: Optional[str] = Field(default=None, max_length=64)
    model_version: Optional[str] = Field(default=None, max_length=100)
    role: Optional[str] = Field(default=None, min_length=2, max_length=150)
    description: Optional[str] = Field(default=None, max_length=2000)
    confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    influence_weight: Optional[float] = Field(default=None, ge=0.1, le=5.0)
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class DecisionParticipantOut(BaseModel):
    agent_id: str
    agent_uuid: uuid.UUID
    agent_code: str
    agent_name: str
    agent_type: Literal["ai", "human"]
    agent_role: str
    provider: Optional[str] = None
    model_version: Optional[str] = None
    influence_weight: float
    participation_status: str
    assigned_at: datetime


class VoteOut(BaseModel):
    id: str
    agent_id: str
    agent_uuid: Optional[uuid.UUID] = None
    agent_code: Optional[str] = None
    agent_name: Optional[str] = None
    agent_type: Optional[str] = None
    agent_role: Optional[str] = None
    provider: Optional[str] = None
    model_version: Optional[str] = None
    influence_weight: float = 1.0
    decision_id: str
    vote: Literal["accept", "reject", "abstain"]
    recommendation: Optional[str] = None
    confidence: float
    justification: str
    bias_indicators: List[str] = Field(default_factory=list)
    timestamp: datetime


class VoteCreateRequest(BaseModel):
    decision_id: str
    agent_id: Optional[str] = None
    vote: Literal["accept", "reject", "abstain"]
    recommendation: Optional[str] = None
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    justification: str = Field(..., min_length=3, max_length=4000)
    bias_indicators: List[str] = Field(default_factory=list)


class DecisionCreateRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    context: str = Field(..., min_length=3, max_length=5000)
    application_type: str = Field(default="general", min_length=2, max_length=64)
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    applicant_data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    participant_agent_ids: Optional[List[str]] = None
    governance_rule_id: Optional[uuid.UUID] = None


class DecisionUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    context: Optional[str] = Field(default=None, min_length=3, max_length=5000)
    application_type: Optional[str] = Field(default=None, min_length=2, max_length=64)
    priority: Optional[Literal["low", "medium", "high", "critical"]] = None
    applicant_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    governance_rule_id: Optional[uuid.UUID] = None


class DecisionGovernanceActionRequest(BaseModel):
    action: Literal["approve", "reject", "escalate", "request_review"]
    justification: str = Field(..., min_length=5, max_length=2000)


class DecisionStatusUpdateLegacy(BaseModel):
    status: Literal["pending", "under_review", "approved", "rejected", "escalated"]
    justification: Optional[str] = Field(default=None, max_length=2000)


class ConsensusSummaryOut(BaseModel):
    total_participants: int
    votes_cast: int
    pending_votes: int
    accept_votes: int
    reject_votes: int
    abstain_votes: int
    weighted_accept_score: float
    weighted_reject_score: float
    consensus_score: float
    average_confidence: float
    ai_consensus_rate: float
    human_consensus_rate: float
    consensus_status: str
    recommended_outcome: str
    explanation: str


class DecisionOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    context: str
    application_type: str
    priority: str = "medium"
    status: str
    applicant_data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    bias_score: float = 0.0
    risk_level: Literal["low", "medium", "high"] = "low"
    ai_recommendation: Optional[str] = None
    consensus_status: str = "pending"
    consensus_score: float = 0.0
    human_override: bool = False
    override_reason: Optional[str] = None
    created_by_id: Optional[uuid.UUID] = None
    created_by_name: str = "System"
    governance_rule_id: Optional[uuid.UUID] = None
    governance_rule_name: Optional[str] = None
    participant_count: int = 0
    vote_count: int = 0
    created_at: datetime
    updated_at: datetime


class PaginatedDecisionsOut(BaseModel):
    items: List[DecisionOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class GovernanceRuleOut(BaseModel):
    id: str
    name: str
    description: str
    context: str
    policy_type: str = "threshold"
    rule_definition: str
    approval_threshold: float = 0.7
    require_human_review: bool = False
    escalation_target: Optional[str] = None
    is_active: bool = True
    priority: int = 1
    applied_count: int = 0
    created_at: datetime
    updated_at: datetime


class GovernanceRuleCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: str = Field(..., min_length=3, max_length=2000)
    context: str = Field(default="general", max_length=64)
    policy_type: str = Field(default="threshold", max_length=64)
    rule_definition: str = Field(..., min_length=3)
    approval_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    require_human_review: bool = False
    escalation_target: Optional[str] = Field(default=None, max_length=100)
    is_active: bool = True
    priority: int = Field(default=1, ge=1, le=100)

    @field_validator("rule_definition")
    @classmethod
    def validate_yaml_syntax(cls, v: str) -> str:
        try:
            parsed = yaml.safe_load(v)
            if not isinstance(parsed, dict):
                raise ValueError("YAML rule definition must parse to a key-value mapping")
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML syntax: {exc}") from exc
        return v


class GovernanceRuleUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    description: Optional[str] = Field(default=None, min_length=3, max_length=2000)
    context: Optional[str] = Field(default=None, max_length=64)
    policy_type: Optional[str] = Field(default=None, max_length=64)
    rule_definition: Optional[str] = None
    approval_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    require_human_review: Optional[bool] = None
    escalation_target: Optional[str] = Field(default=None, max_length=100)
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(default=None, ge=1, le=100)

    @field_validator("rule_definition")
    @classmethod
    def validate_yaml_syntax(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            parsed = yaml.safe_load(v)
            if not isinstance(parsed, dict):
                raise ValueError("YAML rule definition must parse to a key-value mapping")
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML syntax: {exc}") from exc
        return v


class AuditLogOut(BaseModel):
    id: str
    decision_id: Optional[str] = None
    decision_title: Optional[str] = None
    actor_user_id: Optional[uuid.UUID] = None
    actor_agent_id: Optional[uuid.UUID] = None
    actor_name: str = "system"
    actor_type: str = "system"
    event_type: str = "decision_event"
    action: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    agent_actions: List[str] = Field(default_factory=list)
    rules_applied: List[str] = Field(default_factory=list)
    compliance_status: Literal["compliant", "under_review", "non_compliant"] = "compliant"
    audit_hash: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class PaginatedAuditLogsOut(BaseModel):
    items: List[AuditLogOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class NotificationOut(BaseModel):
    id: str
    type: str
    title: str
    message: str
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    is_read: bool = False
    recipient_user_id: Optional[uuid.UUID] = None
    related_decision_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime
    read_at: Optional[datetime] = None


class NotificationCreateRequest(BaseModel):
    type: str = Field(default="system_alert", max_length=64)
    title: str = Field(..., min_length=2, max_length=255)
    message: str = Field(..., min_length=2, max_length=2000)
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    related_decision_id: Optional[uuid.UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

