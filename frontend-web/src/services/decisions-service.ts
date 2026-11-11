import { apiClient } from './api-client';
import type {
  DecisionSummaryItem,
  DecisionWorkspaceResponse,
  PaginatedDecisionsResponse,
  PriorityLevel,
  VoteChoice,
  VoteItem,
} from '@/types/governance';

export interface ListDecisionsParams {
  search?: string;
  status?: string;
  priority?: string;
  application_type?: string;
  risk_level?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface CreateDecisionPayload {
  title: string;
  description?: string;
  context: string;
  application_type: string;
  priority: PriorityLevel;
  applicant_data?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface GovernanceActionPayload {
  action: 'approve' | 'reject' | 'escalate' | 'request_review';
  justification: string;
}

export interface CreateVotePayload {
  decision_id: string;
  agent_id?: string;
  vote: VoteChoice;
  recommendation?: string;
  confidence: number;
  justification: string;
  bias_indicators?: string[];
}

export const decisionsService = {
  async listDecisions(
    params?: ListDecisionsParams
  ): Promise<PaginatedDecisionsResponse> {
    const cleanParams: Record<string, unknown> = {};
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== '') {
          cleanParams[k] = v;
        }
      });
    }
    const { data } = await apiClient.get<PaginatedDecisionsResponse>(
      '/decisions',
      { params: cleanParams }
    );
    return data;
  },

  async getDecisionWorkspace(
    decisionId: string
  ): Promise<DecisionWorkspaceResponse> {
    const { data } = await apiClient.get<DecisionWorkspaceResponse>(
      `/decisions/${decisionId}/workspace`
    );
    return data;
  },

  async createDecision(
    payload: CreateDecisionPayload
  ): Promise<DecisionSummaryItem> {
    const { data } = await apiClient.post<DecisionSummaryItem>(
      '/decisions',
      payload
    );
    return data;
  },

  async executeGovernanceAction(
    decisionId: string,
    payload: GovernanceActionPayload
  ): Promise<DecisionSummaryItem> {
    const { data } = await apiClient.post<DecisionSummaryItem>(
      `/decisions/${decisionId}/governance-action`,
      payload
    );
    return data;
  },

  async runAiAnalysis(decisionId: string): Promise<{
    decision_id: string;
    ai_analysis: Record<string, unknown>;
    bias_analysis: Record<string, unknown>;
  }> {
    const { data } = await apiClient.post<{
      decision_id: string;
      ai_analysis: Record<string, unknown>;
      bias_analysis: Record<string, unknown>;
    }>(`/decisions/${decisionId}/analyze`, {});
    return data;
  },

  async submitVote(payload: CreateVotePayload): Promise<VoteItem> {
    const { data } = await apiClient.post<VoteItem>('/votes', payload);
    return data;
  },

  async deleteDecision(decisionId: string): Promise<{ message: string }> {
    const { data } = await apiClient.delete<{ message: string }>(
      `/decisions/${decisionId}`
    );
    return data;
  },
};

