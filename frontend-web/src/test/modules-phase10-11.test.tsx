import * as React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useRoutes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AppProviders } from '@/app/providers';
import { createAppQueryClient, queryKeys } from '@/app/query-client';
import { appRoutes } from '@/app/router';
import { useGovernanceWebSocket } from '@/hooks/use-governance-websocket';
import { platformServices } from '@/services/platform-services';
import { useAuthStore } from '@/stores/auth-store';
import { useUiStore } from '@/stores/ui-store';
import type { UserAuth } from '@/types/auth';

// Mock Recharts ResponsiveContainer for JSDOM
vi.mock('recharts', async () => {
  const actual = await vi.importActual<typeof import('recharts')>('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div style={{ width: 600, height: 260 }}>{children}</div>
    ),
  };
});

// Mock @xyflow/react for JSDOM
vi.mock('@xyflow/react', () => ({
  ReactFlow: ({
    nodes,
    edges,
    children,
  }: {
    nodes: Array<{ id: string; data: { label: string } }>;
    edges: Array<{ id: string; label?: string }>;
    children?: React.ReactNode;
  }) => (
    <div data-testid="mock-react-flow">
      {nodes.map((n) => (
        <div key={n.id} data-testid={`flow-node-${n.id}`}>
          {n.data.label}
        </div>
      ))}
      {edges.map((e) => (
        <div key={e.id} data-testid={`flow-edge-${e.id}`}>
          {e.label}
        </div>
      ))}
      {children}
    </div>
  ),
  Background: () => <div data-testid="flow-bg" />,
  Controls: () => <div data-testid="flow-controls" />,
  MiniMap: () => <div data-testid="flow-minimap" />,
}));

const SUPER_ADMIN: UserAuth = {
  id: '00000000-0000-0000-0000-000000000001',
  username: 'admin',
  email: 'admin@parallaxai.io',
  full_name: 'Marcus Vance',
  role: 'SUPER_ADMIN',
  roles: ['SUPER_ADMIN'],
  permissions: [
    'decisions:read',
    'decisions:create',
    'decisions:update',
    'decisions:approve',
    'decisions:reject',
    'decisions:escalate',
    'decisions:manage',
    'agents:read',
    'agents:manage',
    'voting:read',
    'voting:participate',
    'governance:read',
    'governance:manage',
    'bias:read',
    'audit:read',
    'notifications:read',
    'users:read',
    'users:manage',
    'roles:manage',
    'system:configure',
  ],
  is_active: true,
  is_verified: true,
  auth_provider: 'local',
  preferences: {},
};

function renderRoute(initialEntry: string) {
  const client = createAppQueryClient();
  return render(
    <AppProviders client={client}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <RoutesRenderer />
      </MemoryRouter>
    </AppProviders>
  );
}

function RoutesRenderer() {
  return useRoutes(appRoutes);
}

describe('Phase 10 & Phase 11 — Platform Modules & Real-Time WebSockets', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useAuthStore.getState().setSession(SUPER_ADMIN, 'super-admin-jwt');
  });

  it('renders AgentRegistryPage and InfluenceGraphPage with React Flow topology', async () => {
    vi.spyOn(platformServices, 'listAgents').mockResolvedValue([
      {
        id: 'ai_gpt4',
        uuid: '00000000-0000-0000-0000-000000000101',
        code: 'ai_gpt4',
        name: 'GPT-4o Governance Evaluator',
        type: 'ai',
        provider: 'openai',
        model_version: 'gpt-4o',
        role: 'Primary AI Risk Evaluator',
        confidence_threshold: 0.75,
        influence_weight: 1.2,
        vote_count: 12,
        average_confidence: 0.89,
        is_active: true,
        metadata: {},
        created_at: '2026-11-11T00:00:00Z',
        updated_at: '2026-11-11T00:00:00Z',
      },
    ]);

    vi.spyOn(platformServices, 'getInfluenceGraph').mockResolvedValue({
      nodes: [
        {
          id: 'ai_gpt4',
          uuid: '00000000-0000-0000-0000-000000000101',
          name: 'GPT-4o Governance Evaluator',
          type: 'ai',
          role: 'Primary AI Risk Evaluator',
          provider: 'openai',
          model_version: 'gpt-4o',
          influence_weight: 1.2,
          confidence_threshold: 0.75,
          vote_count: 12,
          average_confidence: 0.89,
          is_active: true,
        },
        {
          id: 'human_sarah',
          uuid: '00000000-0000-0000-0000-000000000201',
          name: 'Dr. Sarah Chen',
          type: 'human',
          role: 'Chief Governance Officer',
          provider: 'human',
          model_version: 'human-expert',
          influence_weight: 1.5,
          confidence_threshold: 0.8,
          vote_count: 10,
          average_confidence: 0.94,
          is_active: true,
        },
      ],
      edges: [
        {
          id: 'ai_gpt4-human_sarah',
          source: 'ai_gpt4',
          target: 'human_sarah',
          agreement_rate: 0.85,
          shared_decisions: 8,
          weight: 0.85,
        },
      ],
      metrics: {
        total_agents: 2,
        active_agents: 2,
        ai_agents: 1,
        human_agents: 1,
        network_density: 1.0,
        average_agreement_rate: 0.85,
        highest_influence_agent: 'Dr. Sarah Chen',
      },
    });

    renderRoute('/app/agents');
    await waitFor(() => {
      expect(
        screen.getByText('GPT-4o Governance Evaluator')
      ).toBeInTheDocument();
    });

    renderRoute('/app/influence');
    await waitFor(() => {
      expect(screen.getByTestId('influence-graph-page')).toBeInTheDocument();
    });
    expect(screen.getByTestId('flow-node-ai_gpt4')).toHaveTextContent(
      'GPT-4o Governance Evaluator (1.20x)'
    );
    expect(
      screen.getByTestId('flow-edge-ai_gpt4-human_sarah')
    ).toHaveTextContent('85% (8)');
  });

  it('renders BiasScannerPage and triggers human review escalation', async () => {
    vi.spyOn(platformServices, 'getBiasOverview').mockResolvedValue({
      summary: {
        total_evaluated_decisions: 5,
        high_bias_count: 1,
        medium_bias_count: 2,
        low_bias_count: 2,
        anomaly_count: 1,
        average_bias_score: 0.42,
        ml_models_trained: true,
      },
      fairness_metrics: {
        demographic_parity: 0.91,
        equal_opportunity: 0.88,
        equalized_odds: 0.87,
        overall_fairness: 0.89,
      },
      category_breakdown: [
        {
          category: 'Demographic',
          key: 'demographic',
          average_score: 0.35,
          max_score: 0.74,
          flagged_count: 1,
        },
      ],
      flagged_decisions: [
        {
          decision_id: 'dec-flagged-001',
          title: 'High-Sensitivity Credit Application #882',
          application_type: 'loan_approval',
          status: 'pending',
          bias_score: 0.74,
          risk_level: 'high',
          is_anomalous: true,
          bias_indicators: ['age_proxy'],
          recommendations: ['Mandatory human review'],
          vote_count: 3,
          created_at: '2026-11-11T10:00:00Z',
        },
      ],
      recent_bias_alerts: [],
    });

    const triggerSpy = vi
      .spyOn(platformServices, 'triggerBiasHumanReview')
      .mockResolvedValue({
        message: 'Bias review triggered and notification created',
        decision_id: 'dec-flagged-001',
        notification: {
          id: 'notif-999',
          type: 'bias_alert',
          title: 'Bias Review Requested',
          message: 'Escalated',
          priority: 'high',
          is_read: false,
          metadata: {},
          timestamp: '2026-11-11T12:00:00Z',
        },
      });

    renderRoute('/app/bias');

    await waitFor(() => {
      expect(
        screen.getByText('High-Sensitivity Credit Application #882')
      ).toBeInTheDocument();
    });

    fireEvent.click(
      screen.getByRole('button', { name: /Trigger Human Review/i })
    );

    await waitFor(() => {
      expect(triggerSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          decision_id: 'dec-flagged-001',
        })
      );
    });
  });

  it('renders GovernanceConsolePage, UsersAndRolesPage, and SystemSettingsPage', async () => {
    vi.spyOn(platformServices, 'listGovernanceRules').mockResolvedValue([
      {
        id: 'rule-1',
        name: 'Fair Lending Policy',
        description: 'Requires human review when bias exceeds 0.50',
        context: 'loan_approval',
        policy_type: 'threshold',
        rule_definition: 'max_bias_score: 0.50',
        approval_threshold: 0.75,
        require_human_review: true,
        is_active: true,
        priority: 1,
        applied_count: 5,
        created_at: '2026-11-11T00:00:00Z',
        updated_at: '2026-11-11T00:00:00Z',
      },
    ]);

    vi.spyOn(platformServices, 'listUsers').mockResolvedValue({
      items: [
        {
          id: SUPER_ADMIN.id,
          username: 'admin',
          email: 'admin@parallaxai.io',
          full_name: 'Marcus Vance',
          is_active: true,
          is_verified: true,
          auth_provider: 'local',
          primary_role: 'SUPER_ADMIN',
          roles: ['SUPER_ADMIN'],
          permissions: SUPER_ADMIN.permissions,
          preferences: {},
          created_at: '2026-11-11T00:00:00Z',
          updated_at: '2026-11-11T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });
    vi.spyOn(platformServices, 'listRoles').mockResolvedValue([
      {
        id: 'role-super',
        name: 'SUPER_ADMIN',
        description: 'Full platform governance control',
        is_system: true,
        permissions: SUPER_ADMIN.permissions,
        user_count: 1,
        created_at: '2026-11-11T00:00:00Z',
        updated_at: '2026-11-11T00:00:00Z',
      },
    ]);
    vi.spyOn(platformServices, 'listPermissions').mockResolvedValue([
      {
        id: 'perm-1',
        name: 'decisions:read',
        module: 'decisions',
        description: 'View decisions',
      },
    ]);

    vi.spyOn(platformServices, 'getSystemSettings').mockResolvedValue({
      platform: {
        app_name: 'ParallaxAI',
        environment: 'development',
        default_registration_role: 'VIEWER',
        access_token_expire_minutes: 30,
        refresh_token_expire_days: 7,
      },
      infrastructure: {
        database: {
          engine: 'PostgreSQL 16 (SQLAlchemy 2.0 + Alembic)',
          connected: true,
          status: 'healthy',
        },
        redis: {
          engine: 'Redis 7',
          connected: true,
          status: 'healthy',
          rate_limiting_enabled: true,
        },
        websocket: {
          endpoint: '/ws',
          active_connections: 2,
          total_messages_sent: 14,
        },
      },
      ai_providers: {
        openai: {
          provider: 'OpenAI',
          model: 'gpt-4o',
          configured: false,
          status: 'fallback_mode',
        },
        anthropic: {
          provider: 'Anthropic',
          model: 'claude-3-5-sonnet-20241022',
          configured: false,
          status: 'fallback_mode',
        },
        gemini: {
          provider: 'Google Gemini',
          model: 'gemini-2.5-pro',
          configured: false,
          status: 'fallback_mode',
        },
        ml_bias_detector: {
          engine: 'Scikit-learn IsolationForest + RandomForest',
          trained: true,
          status: 'ready',
        },
      },
      authentication: {
        password_hashing: 'Argon2id (argon2-cffi)',
        session_strategy: 'JWT Access Token + HttpOnly Refresh Cookie Rotation',
        google_oauth_enabled: false,
        email_reset_configured: false,
      },
      rate_limits: {
        login_per_minute: 10,
        register_per_hour: 10,
        password_reset_per_hour: 5,
        general_api_per_minute: 120,
        ai_inference_per_minute: 20,
        upload_per_hour: 20,
      },
    });
    vi.spyOn(platformServices, 'listActiveSessions').mockResolvedValue([]);

    renderRoute('/app/governance');
    await waitFor(() => {
      expect(screen.getByText('Fair Lending Policy')).toBeInTheDocument();
    });

    renderRoute('/app/users');
    await waitFor(() => {
      expect(screen.getByTestId('users-roles-page')).toBeInTheDocument();
    });

    renderRoute('/app/settings');
    await waitFor(() => {
      expect(screen.getByTestId('system-settings-page')).toBeInTheDocument();
    });
    expect(
      screen.getByText('PostgreSQL 16 (SQLAlchemy 2.0 + Alembic)')
    ).toBeInTheDocument();
  });

  it('connects useGovernanceWebSocket, updates connection state honestly, and invalidates queries on events', async () => {
    const client = createAppQueryClient();
    const invalidateSpy = vi.spyOn(client, 'invalidateQueries');

    class MockWebSocket {
      public static instances: MockWebSocket[] = [];
      public onopen: (() => void) | null = null;
      public onmessage: ((ev: { data: string }) => void) | null = null;
      public onerror: (() => void) | null = null;
      public onclose: (() => void) | null = null;
      public close = vi.fn();

      constructor(public url: string) {
        MockWebSocket.instances.push(this);
      }
    }

    vi.stubGlobal('WebSocket', MockWebSocket);

    function WsHarness() {
      useGovernanceWebSocket({ enabled: true, wsUrl: 'ws://localhost:8000/ws' });
      const wsState = useUiStore((s) => s.wsConnectionState);
      return <div data-testid="ws-state">{wsState}</div>;
    }

    render(
      <AppProviders client={client}>
        <WsHarness />
      </AppProviders>
    );

    expect(screen.getByTestId('ws-state')).toHaveTextContent('connecting');
    const activeSocket = MockWebSocket.instances[0];
    expect(activeSocket).toBeDefined();

    act(() => {
      activeSocket?.onopen?.();
    });
    expect(screen.getByTestId('ws-state')).toHaveTextContent('connected');

    act(() => {
      activeSocket?.onmessage?.({
        data: JSON.stringify({
          type: 'vote_created',
          data: { decision_id: 'dec-123' },
        }),
      });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: queryKeys.votes.all,
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: queryKeys.decisions.all,
    });

    vi.unstubAllGlobals();
  });
});
