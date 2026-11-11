/**
 * Core domain types matching backend/schemas/governance_domain.py.
 */

export type DecisionStatus =
  | 'pending'
  | 'under_review'
  | 'approved'
  | 'rejected'
  | 'escalated';

export type RiskLevel = 'low' | 'medium' | 'high';
export type PriorityLevel = 'low' | 'medium' | 'high' | 'critical';

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
  bias_score: number;
  risk_level: RiskLevel;
  consensus_status: string;
  consensus_score: number;
  human_override: boolean;
  created_by_name: string;
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
