import { apiClient } from './api-client';
import type {
  AgentItem,
  AuditLogItem,
  ConsensusSummary,
  DecisionSummaryItem,
  GovernanceRuleItem,
  NotificationItem,
  NotificationsListResponse,
  PaginatedAuditLogsResponse,
  PriorityLevel,
  VoteChoice,
  VoteItem,
} from '@/types/governance';

// --- Agents & Influence Graph Types ---
export interface InfluenceGraphNode {
  id: string;
  uuid: string;
  name: string;
  type: 'ai' | 'human';
  role: string;
  provider?: string | null;
  model_version?: string | null;
  influence_weight: number;
  confidence_threshold: number;
  vote_count: number;
  average_confidence: number;
  is_active: boolean;
}

export interface InfluenceGraphEdge {
  id: string;
  source: string;
  target: string;
  agreement_rate: number;
  shared_decisions: number;
  weight: number;
}

export interface InfluenceGraphResponse {
  nodes: InfluenceGraphNode[];
  edges: InfluenceGraphEdge[];
  metrics: {
    total_agents: number;
    active_agents: number;
    ai_agents: number;
    human_agents: number;
    network_density: number;
    average_agreement_rate: number;
    highest_influence_agent?: string | null;
  };
}

export interface AgentDetailResponse {
  agent: AgentItem;
  voting_statistics: {
    recorded_votes: number;
    historical_vote_count: number;
    accept_votes: number;
    reject_votes: number;
    abstain_votes: number;
    accept_rate: number;
    average_confidence: number;
  };
  recent_votes: VoteItem[];
  recent_activities: AuditLogItem[];
}

export interface CreateAgentPayload {
  name: string;
  code?: string;
  type: 'ai' | 'human';
  provider?: string;
  model_version?: string;
  role: string;
  description?: string;
  confidence_threshold: number;
  influence_weight: number;
  is_active?: boolean;
}

export interface UpdateAgentPayload {
  name?: string;
  provider?: string;
  model_version?: string;
  role?: string;
  description?: string;
  confidence_threshold?: number;
  influence_weight?: number;
  is_active?: boolean;
}

// --- Bias & Fairness Overview Types ---
export interface BiasOverviewResponse {
  summary: {
    total_evaluated_decisions: number;
    high_bias_count: number;
    medium_bias_count: number;
    low_bias_count: number;
    anomaly_count: number;
    average_bias_score: number;
    ml_models_trained: boolean;
  };
  fairness_metrics: {
    demographic_parity: number;
    equal_opportunity: number;
    equalized_odds: number;
    overall_fairness: number;
  };
  category_breakdown: Array<{
    category: string;
    key: string;
    average_score: number;
    max_score: number;
    flagged_count: number;
  }>;
  flagged_decisions: Array<{
    decision_id: string;
    title: string;
    application_type: string;
    status: string;
    bias_score: number;
    risk_level: string;
    is_anomalous: boolean;
    bias_indicators: string[];
    recommendations: string[];
    vote_count: number;
    created_at: string;
  }>;
  recent_bias_alerts: NotificationItem[];
}

// --- Users & Roles Types ---
export interface UserAdminItem {
  id: string;
  username: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_verified: boolean;
  auth_provider: string;
  primary_role: string;
  roles: string[];
  permissions: string[];
  preferences: Record<string, unknown>;
  last_login_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedUsersResponse {
  items: UserAdminItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface RoleItem {
  id: string;
  name: string;
  description: string;
  is_system: boolean;
  permissions: string[];
  user_count: number;
  created_at: string;
  updated_at: string;
}

export interface PermissionItem {
  id: string;
  name: string;
  module: string;
  description: string;
}

export interface ActiveSessionItem {
  id: string;
  family_id: string;
  user_agent?: string | null;
  ip_address?: string | null;
  is_revoked: boolean;
  expires_at: string;
  created_at: string;
}

export interface SystemSettingsResponse {
  platform: {
    app_name: string;
    environment: string;
    default_registration_role: string;
    access_token_expire_minutes: number;
    refresh_token_expire_days: number;
  };
  infrastructure: {
    database: {
      engine: string;
      connected: boolean;
      status: string;
    };
    redis: {
      engine: string;
      connected: boolean;
      status: string;
      rate_limiting_enabled: boolean;
    };
    websocket: {
      endpoint: string;
      active_connections: number;
      total_messages_sent: number;
    };
  };
  ai_providers: {
    openai: {
      provider: string;
      model: string;
      configured: boolean;
      status: string;
    };
    anthropic: {
      provider: string;
      model: string;
      configured: boolean;
      status: string;
    };
    gemini: {
      provider: string;
      model: string;
      configured: boolean;
      status: string;
    };
    ml_bias_detector: {
      engine: string;
      trained: boolean;
      status: string;
    };
  };
  authentication: {
    password_hashing: string;
    session_strategy: string;
    google_oauth_enabled: boolean;
    email_reset_configured: boolean;
  };
  rate_limits: {
    login_per_minute: number;
    register_per_hour: number;
    password_reset_per_hour: number;
    general_api_per_minute: number;
    ai_inference_per_minute: number;
    upload_per_hour: number;
  };
}

export const platformServices = {
  // --- Agents & Influence Graph ---
  async listAgents(params?: {
    type?: string;
    is_active?: boolean;
    search?: string;
  }): Promise<AgentItem[]> {
    const { data } = await apiClient.get<AgentItem[]>('/agents', { params });
    return data;
  },

  async getAgentDetail(agentId: string): Promise<AgentDetailResponse> {
    const { data } = await apiClient.get<AgentDetailResponse>(
      `/agents/${agentId}`
    );
    return data;
  },

  async registerAgent(payload: CreateAgentPayload): Promise<AgentItem> {
    const { data } = await apiClient.post<AgentItem>('/agents', payload);
    return data;
  },

  async updateAgent(
    agentId: string,
    payload: UpdateAgentPayload
  ): Promise<AgentItem> {
    const { data } = await apiClient.patch<AgentItem>(
      `/agents/${agentId}`,
      payload
    );
    return data;
  },

  async getInfluenceGraph(): Promise<InfluenceGraphResponse> {
    const { data } = await apiClient.get<InfluenceGraphResponse>(
      '/agents/influence-graph'
    );
    return data;
  },

  // --- Multi-Agent Voting ---
  async listVotes(params?: {
    decision_id?: string;
    agent_id?: string;
    vote?: string;
    limit?: number;
  }): Promise<VoteItem[]> {
    const { data } = await apiClient.get<VoteItem[]>('/votes', { params });
    return data;
  },

  async getDecisionVotingSummary(decisionId: string): Promise<{
    decision_id: string;
    decision_title: string;
    decision_status: string;
    bias_score: number;
    risk_level: string;
    consensus: ConsensusSummary;
    votes: VoteItem[];
  }> {
    const { data } = await apiClient.get(`/votes/decision/${decisionId}/summary`);
    return data;
  },

  async submitVote(payload: {
    decision_id: string;
    agent_id?: string;
    vote: VoteChoice;
    recommendation?: string;
    confidence: number;
    justification: string;
    bias_indicators?: string[];
  }): Promise<VoteItem> {
    const { data } = await apiClient.post<VoteItem>('/votes', payload);
    return data;
  },

  // --- Bias & Fairness Scanner ---
  async getBiasOverview(): Promise<BiasOverviewResponse> {
    const { data } = await apiClient.get<BiasOverviewResponse>(
      '/bias/overview'
    );
    return data;
  },

  async analyzeDecisionBias(decisionId: string): Promise<{
    decision: DecisionSummaryItem;
    bias_analysis: Record<string, unknown>;
  }> {
    const { data } = await apiClient.post(`/bias/analyze/${decisionId}`, {});
    return data;
  },

  async triggerBiasHumanReview(payload: {
    decision_id: string;
    reason: string;
  }): Promise<{
    message: string;
    decision_id: string;
    notification: NotificationItem;
  }> {
    const { data } = await apiClient.post('/bias/trigger-review', payload);
    return data;
  },

  // --- Governance Console & Policy Engine ---
  async listGovernanceRules(params?: {
    context?: string;
    is_active?: boolean;
  }): Promise<GovernanceRuleItem[]> {
    const { data } = await apiClient.get<GovernanceRuleItem[]>(
      '/governance/rules',
      { params }
    );
    return data;
  },

  async validateGovernanceYaml(rule_definition: string): Promise<{
    valid: boolean;
    error?: string | null;
    parsed?: Record<string, unknown> | null;
    keys?: string[];
  }> {
    const { data } = await apiClient.post('/governance/validate-yaml', {
      rule_definition,
    });
    return data;
  },

  async createGovernanceRule(payload: {
    name: string;
    description: string;
    context: string;
    policy_type?: string;
    rule_definition: string;
    approval_threshold: number;
    require_human_review: boolean;
    escalation_target?: string;
    is_active: boolean;
    priority: number;
  }): Promise<GovernanceRuleItem> {
    const { data } = await apiClient.post<GovernanceRuleItem>(
      '/governance/rules',
      payload
    );
    return data;
  },

  async updateGovernanceRule(
    ruleId: string,
    payload: Partial<{
      name: string;
      description: string;
      context: string;
      policy_type: string;
      rule_definition: string;
      approval_threshold: number;
      require_human_review: boolean;
      escalation_target: string;
      is_active: boolean;
      priority: number;
    }>
  ): Promise<GovernanceRuleItem> {
    const { data } = await apiClient.put<GovernanceRuleItem>(
      `/governance/rules/${ruleId}`,
      payload
    );
    return data;
  },

  async deleteGovernanceRule(
    ruleId: string
  ): Promise<{ message: string; id: string }> {
    const { data } = await apiClient.delete(`/governance/rules/${ruleId}`);
    return data;
  },

  // --- Audit & Explainability ---
  async listAuditLogs(params?: {
    search?: string;
    compliance_status?: string;
    actor_type?: string;
    event_type?: string;
    decision_id?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedAuditLogsResponse> {
    const cleanParams: Record<string, unknown> = {};
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== '') cleanParams[k] = v;
      });
    }
    const { data } = await apiClient.get<PaginatedAuditLogsResponse>('/audit', {
      params: cleanParams,
    });
    return data;
  },

  async getDecisionExplainability(decisionId: string): Promise<{
    decision: DecisionSummaryItem;
    consensus: ConsensusSummary;
    votes: VoteItem[];
    audit_trail: AuditLogItem[];
  }> {
    const { data } = await apiClient.get(`/audit/decision/${decisionId}`);
    return data;
  },

  // --- Notification Center ---
  async listNotifications(params?: {
    is_read?: boolean;
    type?: string;
    priority?: PriorityLevel | string;
    limit?: number;
  }): Promise<NotificationsListResponse> {
    const cleanParams: Record<string, unknown> = {};
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== '') cleanParams[k] = v;
      });
    }
    const { data } = await apiClient.get<NotificationsListResponse>(
      '/notifications',
      { params: cleanParams }
    );
    return data;
  },

  async markNotificationRead(
    notificationId: string
  ): Promise<NotificationItem> {
    const { data } = await apiClient.put<NotificationItem>(
      `/notifications/${notificationId}/read`,
      {}
    );
    return data;
  },

  async markAllNotificationsRead(): Promise<{
    message: string;
    updated_count: number;
  }> {
    const { data } = await apiClient.post('/notifications/mark-all-read', {});
    return data;
  },

  async deleteNotification(
    notificationId: string
  ): Promise<{ message: string; id: string }> {
    const { data } = await apiClient.delete(
      `/notifications/${notificationId}`
    );
    return data;
  },

  // --- Users & Roles Administration ---
  async listUsers(params?: {
    search?: string;
    role?: string;
    is_active?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedUsersResponse> {
    const cleanParams: Record<string, unknown> = {};
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== '') cleanParams[k] = v;
      });
    }
    const { data } = await apiClient.get<PaginatedUsersResponse>('/users', {
      params: cleanParams,
    });
    return data;
  },

  async updateUserStatus(
    userId: string,
    payload: { is_active: boolean; reason?: string }
  ): Promise<UserAdminItem> {
    const { data } = await apiClient.patch<UserAdminItem>(
      `/users/${userId}/status`,
      payload
    );
    return data;
  },

  async updateUserRoles(
    userId: string,
    payload: { roles: string[]; reason?: string }
  ): Promise<UserAdminItem> {
    const { data } = await apiClient.put<UserAdminItem>(
      `/users/${userId}/roles`,
      payload
    );
    return data;
  },

  async listRoles(): Promise<RoleItem[]> {
    const { data } = await apiClient.get<RoleItem[]>('/roles');
    return data;
  },

  async listPermissions(): Promise<PermissionItem[]> {
    const { data } = await apiClient.get<PermissionItem[]>(
      '/roles/permissions'
    );
    return data;
  },

  async createRole(payload: {
    name: string;
    description: string;
    permissions: string[];
  }): Promise<RoleItem> {
    const { data } = await apiClient.post<RoleItem>('/roles', payload);
    return data;
  },

  async updateRolePermissions(
    roleId: string,
    payload: { permissions: string[]; description?: string }
  ): Promise<RoleItem> {
    const { data } = await apiClient.put<RoleItem>(
      `/roles/${roleId}/permissions`,
      payload
    );
    return data;
  },

  // --- System Settings & Active Sessions ---
  async getSystemSettings(): Promise<SystemSettingsResponse> {
    const { data } =
      await apiClient.get<SystemSettingsResponse>('/system/settings');
    return data;
  },

  async listActiveSessions(): Promise<ActiveSessionItem[]> {
    const { data } = await apiClient.get<ActiveSessionItem[]>('/auth/sessions');
    return data;
  },

  async revokeSession(sessionId: string): Promise<{ message: string }> {
    const { data } = await apiClient.delete(`/auth/sessions/${sessionId}`);
    return data;
  },

  async revokeAllSessions(): Promise<{
    message: string;
    revoked_count: number;
  }> {
    const { data } = await apiClient.post('/auth/sessions/revoke-all', {});
    return data;
  },
};
