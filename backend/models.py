from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Any, Optional, Literal
from enum import Enum

class AgentType(str, Enum):
    AI = "ai"
    HUMAN = "human"

class DecisionStatus(str, Enum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"

class VoteDecision(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"

class NotificationType(str, Enum):
    BIAS_ALERT = "bias_alert"
    HUMAN_OVERRIDE = "human_override"
    DECISION_APPROVED = "decision_approved"
    RULE_VIOLATION = "rule_violation"
    SYSTEM_ALERT = "system_alert"

class Agent(BaseModel):
    id: str
    name: str
    type: AgentType
    model_version: Optional[str] = None
    role: str
    confidence_threshold: float = 0.5
    influence_weight: float = 1.0
    vote_count: int = 0
    average_confidence: float = 0.0
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

class Decision(BaseModel):
    id: str
    context: str
    application_type: str
    applicant_data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    status: DecisionStatus
    bias_score: float = 0.0
    risk_level: Literal["low", "medium", "high"] = "low"
    created_at: datetime
    updated_at: datetime
    ai_recommendation: Optional[str] = None
    human_override: bool = False
    override_reason: Optional[str] = None

class Vote(BaseModel):
    id: str
    agent_id: str
    decision_id: str
    vote: VoteDecision
    confidence: float
    justification: str
    timestamp: datetime
    bias_indicators: List[str] = Field(default_factory=list)
    
class GovernanceRule(BaseModel):
    id: str
    name: str
    description: str
    context: str
    rule_definition: str  # YAML or JSON rule definition
    is_active: bool = True
    priority: int = 1
    created_at: datetime
    updated_at: datetime
    applied_count: int = 0

class AuditLog(BaseModel):
    id: str
    decision_id: str
    action: str
    timestamp: datetime
    agent_actions: List[str]
    rules_applied: List[str]
    compliance_status: Literal["compliant", "under_review", "non_compliant"]
    audit_hash: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Notification(BaseModel):
    id: str
    type: NotificationType
    title: str
    message: str
    is_read: bool = False
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    priority: Literal["low", "medium", "high"] = "medium"

class BiasMetrics(BaseModel):
    demographic_parity: float
    equal_opportunity: float
    equalized_odds: float
    overall_fairness: float
    bias_by_category: Dict[str, float]
    active_alerts: int
    total_reviews: int

class InfluenceMetrics(BaseModel):
    total_agents: int
    ai_agents: int
    human_agents: int
    high_influence_agents: int
    consensus_rate: float
    override_events: int
    network_density: float

class SystemStats(BaseModel):
    total_decisions: int
    ai_accuracy: float
    override_rate: float
    bias_incidents: int
    active_rules: int
    compliance_rate: float
    average_processing_time: float
    unread_notifications: int

# WebSocket message models
class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)

class ConnectionInfo(BaseModel):
    client_id: str
    connected_at: datetime
    last_ping: datetime
    subscriptions: List[str] = Field(default_factory=list)
