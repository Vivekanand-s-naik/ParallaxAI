import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useRoutes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AppProviders } from '@/app/providers';
import { createAppQueryClient } from '@/app/query-client';
import { appRoutes } from '@/app/router';
import { decisionsService } from '@/services/decisions-service';
import { systemService } from '@/services/system-service';
import { useAuthStore } from '@/stores/auth-store';
import type { UserAuth } from '@/types/auth';
import type {
  CommandCenterStatsResponse,
  SystemHealthResponse,
} from '@/types/governance';

// Mock ResponsiveContainer size in JSDOM
vi.mock('recharts', async () => {
  const actual = await vi.importActual<typeof import('recharts')>('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div style={{ width: 600, height: 260 }}>{children}</div>
    ),
  };
});

const ANALYST_USER: UserAuth = {
  id: '00000000-0000-0000-0000-000000000022',
  username: 'analyst',
  email: 'analyst@parallaxai.io',
  full_name: 'David Park',
  role: 'ANALYST',
  roles: ['ANALYST'],
  permissions: [
    'decisions:read',
    'decisions:create',
    'agents:read',
    'voting:read',
    'governance:read',
    'bias:read',
    'audit:read',
    'notifications:read',
  ],
  is_active: true,
  is_verified: true,
  auth_provider: 'local',
  preferences: {},
};

const MOCK_STATS: CommandCenterStatsResponse = {
  kpis: {
    total_decisions: 5,
    approved_decisions: 2,
    rejected_decisions: 1,
    escalated_decisions: 1,
    pending_decisions: 1,
    decisions_requiring_review: 2,
    approval_rate: 0.4,
    total_agents: 6,
    active_agents: 6,
    ai_agents: 3,
    human_agents: 3,
    high_influence_agents: 2,
    high_bias_decisions: 1,
    medium_bias_decisions: 2,
    low_bias_decisions: 2,
    bias_incidents: 3,
    governance_violations: 1,
    ai_accuracy: 0.88,
    override_rate: 0.2,
    unread_notifications: 3,
    total_notifications: 5,
    active_rules: 3,
    total_rules: 3,
    compliance_rate: 0.95,
    consensus_rate: 0.82,
    average_processing_time: 14.5,
    override_events: 1,
    network_density: 0.8,
    total_votes: 15,
    total_audit_logs: 8,
    decisions_last_24h: 2,
    votes_last_24h: 6,
    alerts_last_24h: 1,
  },
  decision_activity: [
    {
      date: '2026-11-10',
      label: 'Nov 10',
      total: 3,
      approved: 1,
      rejected: 1,
      pending: 1,
      escalated: 0,
    },
    {
      date: '2026-11-11',
      label: 'Nov 11',
      total: 2,
      approved: 1,
      rejected: 0,
      pending: 0,
      escalated: 1,
    },
  ],
  category_distribution: [
    { category: 'loan_approval', count: 2 },
    { category: 'medical_diagnosis', count: 2 },
    { category: 'hiring_assessment', count: 1 },
  ],
  agent_activity: [
    {
      agent_id: 'ai_gpt4',
      name: 'GPT-4o Governance Evaluator',
      type: 'ai',
      role: 'Primary AI Risk Evaluator',
      provider: 'openai',
      influence_weight: 1.2,
      is_active: true,
      vote_count: 5,
      accept_votes: 3,
      reject_votes: 2,
      abstain_votes: 0,
      average_confidence: 0.89,
    },
    {
      agent_id: 'human_sarah',
      name: 'Dr. Sarah Chen',
      type: 'human',
      role: 'Chief Governance Officer',
      provider: 'human',
      influence_weight: 1.5,
      is_active: true,
      vote_count: 4,
      accept_votes: 2,
      reject_votes: 2,
      abstain_votes: 0,
      average_confidence: 0.94,
    },
  ],
  recent_decisions: [
    {
      id: 'dec-1111-2222-3333',
      title: 'Commercial Small Business Credit Line #4092',
      context: 'Automated credit underwriting evaluation for regional manufacturer',
      application_type: 'loan_approval',
      priority: 'high',
      status: 'under_review',
      bias_score: 0.74,
      risk_level: 'high',
      consensus_status: 'escalated_for_review',
      consensus_score: 0.68,
      human_override: false,
      created_by_name: 'Marcus Vance',
      participant_count: 6,
      vote_count: 4,
      created_at: '2026-11-11T10:00:00Z',
      updated_at: '2026-11-11T11:00:00Z',
    },
  ],
  recent_audit_logs: [
    {
      id: 'audit-001',
      decision_id: 'dec-1111-2222-3333',
      decision_title: 'Commercial Small Business Credit Line #4092',
      actor_name: 'Dr. Sarah Chen',
      actor_type: 'human',
      event_type: 'vote_submitted',
      action: "Submitted vote 'reject' due to demographic disparity",
      compliance_status: 'compliant',
      audit_hash: 'sha256_9a8b7c6d5e4f3a2b1c0d',
      agent_actions: ['human_sarah:reject'],
      rules_applied: ['Fair Lending Policy'],
      metadata: {},
      timestamp: '2026-11-11T11:00:00Z',
    },
  ],
  recent_notifications: [
    {
      id: 'notif-001',
      type: 'bias_alert',
      title: 'High Bias Risk Detected',
      message: 'Credit Line #4092 exceeded 0.70 bias threshold.',
      priority: 'high',
      is_read: false,
      metadata: {},
      timestamp: '2026-11-11T11:01:00Z',
    },
  ],
};

const MOCK_HEALTH: SystemHealthResponse = {
  status: 'healthy',
  timestamp: '2026-11-11T12:00:00Z',
  environment: 'development',
  services: {
    backend_api: { status: 'healthy', version: '2.0.0' },
    postgresql: { status: 'healthy', connected: true },
    redis: { status: 'healthy', connected: true },
    websocket: {
      status: 'healthy',
      active_connections: 1,
      total_messages_sent: 10,
    },
    ml_bias_engine: { status: 'healthy', models_trained: true },
    ai_providers: {
      openai_configured: false,
      anthropic_configured: false,
      gemini_configured: false,
      fallback_active: true,
    },
  },
};

function renderDashboard(initialEntries = ['/app/dashboard']) {
  const client = createAppQueryClient();
  return render(
    <AppProviders client={client}>
      <MemoryRouter initialEntries={initialEntries}>
        <RoutesRenderer />
      </MemoryRouter>
    </AppProviders>
  );
}

function RoutesRenderer() {
  return useRoutes(appRoutes);
}

describe('Phase 8 — Command Center Dashboard', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useAuthStore.getState().setSession(ANALYST_USER, 'analyst-jwt-token');
    vi.spyOn(systemService, 'getCommandCenterStats').mockResolvedValue(
      MOCK_STATS
    );
    vi.spyOn(systemService, 'getSystemHealth').mockResolvedValue(MOCK_HEALTH);
    vi.spyOn(decisionsService, 'getDecisionWorkspace').mockReturnValue(
      new Promise(() => {})
    );
  });

  it('renders all 6 KPI cards, Recharts sections, Governance Health, System Status, Activity Feed, and navigates from Recent Decisions', async () => {
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId('command-center-page')).toBeInTheDocument();
    });

    // Verify KPI Cards
    expect(screen.getByText('Total Decisions')).toBeInTheDocument();
    expect(screen.getByText('Pending Decisions')).toBeInTheDocument();
    expect(screen.getByText('Active AI Agents')).toBeInTheDocument();
    expect(screen.getByText('Human Participants')).toBeInTheDocument();
    expect(screen.getByText('Requiring Review')).toBeInTheDocument();
    expect(screen.getByText('Bias Alerts')).toBeInTheDocument();

    // Verify Charts & Cards
    expect(screen.getByTestId('decision-activity-chart')).toBeInTheDocument();
    expect(screen.getByTestId('agent-activity-chart')).toBeInTheDocument();
    expect(screen.getByTestId('governance-health-card')).toHaveTextContent(
      '95.0%'
    );
    expect(screen.getByTestId('system-status-card')).toHaveTextContent(
      'PostgreSQL 16 Persistence'
    );
    expect(screen.getByTestId('activity-feed-card')).toHaveTextContent(
      "Submitted vote 'reject' due to demographic disparity"
    );

    // Recent Decisions table row & navigation to /app/decisions/:decisionId
    expect(
      screen.getByText('Commercial Small Business Credit Line #4092')
    ).toBeInTheDocument();

    const inspectBtn = screen.getByRole('button', { name: /inspect/i });
    fireEvent.click(inspectBtn);

    await waitFor(() => {
      expect(
        screen.getByRole('heading', {
          name: /Decision Workspace — dec-1111-2222-3333/i,
        })
      ).toBeInTheDocument();
    });
  });
});

