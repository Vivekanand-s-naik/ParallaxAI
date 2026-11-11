/**
 * Core domain types matching backend/schemas/governance_domain.py,
 * backend/schemas/users_roles.py, and backend/api/v1/*.py.
 */

export type DecisionStatus =
  | 'pending'
  | 'under_review'
  | 'approved'
  | 'rejected'
  | 'escalated';

export type RiskLevel = 'low' | 'medium' | 'high';
export type PriorityLevel = 'low' | 'medium' | 'high' | 'critical';
export type ComplianceStatus = 'compliant' | 'under_review' | 'non_compliant';
export type VoteChoice = 'accept' | 'reject' | 'abstain';

export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  message: string;
  priority: PriorityLevel;
  is_read: boolean;
  recipient_user_id?: string | null;
  related_decision_id?: string | null;
  metadata: Record<string, unknown>;
  timestamp: string;
  read_at?: string | null;
}

export interface NotificationsListResponse {
  items: NotificationItem[];
  unread_count: number;
  total: number;
}

export interface DecisionSummaryItem {
  id: string;
  title: string;
  description?: string | null;
  context: string;
  application_type: string;
  priority: PriorityLevel;
  status: DecisionStatus;
  applicant_data?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  bias_score: number;
  risk_level: RiskLevel;
  ai_recommendation?: string | null;
  consensus_status: string;
  consensus_score: number;
  human_override: boolean;
  override_reason?: string | null;
  created_by_id?: string | null;
  created_by_name: string;
  governance_rule_id?: string | null;
  governance_rule_name?: string | null;
  participant_count: number;
  vote_count: number;
  created_at: string;
  updated_at: string;
}

export interface PaginatedDecisionsResponse {
  items: DecisionSummaryItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DecisionParticipantItem {
  agent_id: string;
  agent_uuid: string;
  agent_code: string;
  agent_name: string;
  agent_type: 'ai' | 'human';
  agent_role: string;
  provider?: string | null;
  model_version?: string | null;
  influence_weight: number;
  participation_status: string;
  assigned_at: string;
}

export interface VoteItem {
  id: string;
  agent_id: string;
  agent_uuid?: string | null;
  agent_code?: string | null;
  agent_name?: string | null;
  agent_type?: string | null;
  agent_role?: string | null;
  provider?: string | null;
  model_version?: string | null;
  influence_weight: number;
  decision_id: string;
  vote: VoteChoice;
  recommendation?: string | null;
  confidence: number;
  justification: string;
  bias_indicators: string[];
  timestamp: string;
}

export interface AgentOpinionCard {
  agent_id: string;
  agent_uuid: string;
  agent_name: string;
  agent_type: 'ai' | 'human';
  role: string;
  provider?: string | null;
  model_version?: string | null;
  influence_weight: number;
  participation_status: 'voted' | 'pending';
  vote?: VoteChoice | null;
  recommendation?: string | null;
  confidence?: number | null;
  justification?: string | null;
  bias_indicators: string[];
  voted_at?: string | null;
}

export interface ConsensusSummary {
  total_participants: number;
  votes_cast: number;
  pending_votes: number;
  accept_votes: number;
  reject_votes: number;
  abstain_votes: number;
  weighted_accept_score: number;
  weighted_reject_score: number;
  consensus_score: number;
  average_confidence: number;
  ai_consensus_rate: number;
  human_consensus_rate: number;
  consensus_status: string;
  recommended_outcome: string;
  explanation: string;
}

export interface BiasAnalysisReport {
  overall_bias_score: number;
  risk_level?: string;
  category_scores?: Record<string, number>;
  fairness_metrics?: {
    demographic_parity?: number;
    equal_opportunity?: number;
    equalized_odds?: number;
    overall_fairness?: number;
  };
  ml_detection?: {
    is_anomalous?: boolean;
    anomaly_score?: number;
    predicted_bias_score?: number;
    model_confidence?: number;
  };
  bias_indicators?: string[];
  recommendations?: string[];
}

export interface GovernanceRuleItem {
  id: string;
  name: string;
  description: string;
  context: string;
  policy_type: string;
  rule_definition: string;
  approval_threshold: number;
  require_human_review: boolean;
  escalation_target?: string | null;
  is_active: boolean;
  priority: number;
  applied_count: number;
  created_at: string;
  updated_at: string;
}

export interface AuditLogItem {
  id: string;
  decision_id?: string | null;
  decision_title?: string | null;
  actor_user_id?: string | null;
  actor_agent_id?: string | null;
  actor_name: string;
  actor_type: string;
  event_type: string;
  action: string;
  previous_status?: string | null;
  new_status?: string | null;
  agent_actions: string[];
  rules_applied: string[];
  compliance_status: ComplianceStatus;
  audit_hash: string;
  metadata: Record<string, unknown>;
  timestamp: string;
}

export interface PaginatedAuditLogsResponse {
  items: AuditLogItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DecisionWorkspaceResponse {
  decision: DecisionSummaryItem;
  participants: DecisionParticipantItem[];
  votes: VoteItem[];
  ai_opinions: AgentOpinionCard[];
  human_reviews: AgentOpinionCard[];
  consensus: ConsensusSummary;
  bias_analysis: BiasAnalysisReport;
  governance_rules: GovernanceRuleItem[];
  audit_trail: AuditLogItem[];
}

export interface AgentItem {
  id: string;
  uuid: string;
  code: string;
  name: string;
  type: 'ai' | 'human';
  provider?: string | null;
  model_version?: string | null;
  role: string;
  description?: string | null;
  confidence_threshold: number;
  influence_weight: number;
  vote_count: number;
  average_confidence: number;
  is_active: boolean;
  user_id?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface PlatformKpis {
  total_decisions: number;
  approved_decisions: number;
  rejected_decisions: number;
  escalated_decisions: number;
  pending_decisions: number;
  decisions_requiring_review: number;
  approval_rate: number;
  total_agents: number;
  active_agents: number;
  ai_agents: number;
  human_agents: number;
  high_influence_agents: number;
  high_bias_decisions: number;
  medium_bias_decisions: number;
  low_bias_decisions: number;
  bias_incidents: number;
  governance_violations: number;
  ai_accuracy: number;
  override_rate: number;
  unread_notifications: number;
  total_notifications: number;
  active_rules: number;
  total_rules: number;
  compliance_rate: number;
  consensus_rate: number;
  average_processing_time: number;
  override_events: number;
  network_density: number;
  total_votes: number;
  total_audit_logs: number;
  decisions_last_24h: number;
  votes_last_24h: number;
  alerts_last_24h: number;
}

export interface DecisionActivityPoint {
  date: string;
  label: string;
  total: number;
  approved: number;
  rejected: number;
  pending: number;
  escalated: number;
}

export interface AgentActivityItem {
  agent_id: string;
  name: string;
  type: 'ai' | 'human';
  role: string;
  provider?: string | null;
  influence_weight: number;
  is_active: boolean;
  vote_count: number;
  accept_votes: number;
  reject_votes: number;
  abstain_votes: number;
  average_confidence: number;
}

export interface CommandCenterStatsResponse {
  kpis: PlatformKpis;
  decision_activity: DecisionActivityPoint[];
  category_distribution: Array<{ category: string; count: number }>;
  agent_activity: AgentActivityItem[];
  recent_decisions: DecisionSummaryItem[];
  recent_audit_logs: AuditLogItem[];
  recent_notifications: NotificationItem[];
}

export interface SystemHealthResponse {
  status: 'healthy' | 'degraded';
  timestamp: string;
  environment: string;
  services: {
    backend_api: { status: string; version: string };
    postgresql: { status: string; connected: boolean };
    redis: { connected: boolean; status: string };
    websocket: {
      status: string;
      active_connections: number;
      total_messages_sent: number;
    };
    ml_bias_engine: { status: string; models_trained: boolean };
    ai_providers: {
      openai_configured: boolean;
      anthropic_configured: boolean;
      gemini_configured: boolean;
      fallback_active: boolean;
    };
  };
}
