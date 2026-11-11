import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useRoutes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AppProviders } from '@/app/providers';
import { createAppQueryClient } from '@/app/query-client';
import { appRoutes } from '@/app/router';
import { decisionsService } from '@/services/decisions-service';
import { useAuthStore } from '@/stores/auth-store';
import type { UserAuth } from '@/types/auth';
import type {
  DecisionWorkspaceResponse,
  PaginatedDecisionsResponse,
} from '@/types/governance';

const GOV_OFFICER_USER: UserAuth = {
  id: '00000000-0000-0000-0000-000000000033',
  username: 'sarah.chen',
  email: 'sarah.chen@parallaxai.io',
  full_name: 'Dr. Sarah Chen',
  role: 'GOVERNANCE_OFFICER',
  roles: ['GOVERNANCE_OFFICER'],
  permissions: [
    'decisions:read',
    'decisions:create',
    'decisions:update',
    'decisions:approve',
    'decisions:reject',
    'decisions:escalate',
    'agents:read',
    'voting:read',
    'voting:participate',
    'governance:read',
    'governance:manage',
    'bias:read',
    'audit:read',
    'notifications:read',
  ],
  is_active: true,
  is_verified: true,
  auth_provider: 'local',
  preferences: {},
};

const MOCK_PAGINATED_DECISIONS: PaginatedDecisionsResponse = {
  items: [
    {
      id: 'dec-7788-9900',
      title: 'Commercial Credit Line — Horizon Logistics',
      description: 'Enterprise logistics credit line evaluation',
      context:
        'Automated credit underwriting evaluation for regional logistics carrier requesting $350,000 working capital.',
      application_type: 'loan_approval',
      priority: 'high',
      status: 'under_review',
      applicant_data: { requested_amount: 350000, region: 'Midwest' },
      bias_score: 0.34,
      risk_level: 'medium',
      consensus_status: 'consensus_reached',
      consensus_score: 0.78,
      human_override: false,
      created_by_name: 'Marcus Vance',
      participant_count: 4,
      vote_count: 3,
      created_at: '2026-11-11T09:00:00Z',
      updated_at: '2026-11-11T10:30:00Z',
    },
  ],
  total: 1,
  page: 1,
  page_size: 15,
  total_pages: 1,
};

const MOCK_WORKSPACE: DecisionWorkspaceResponse = {
  decision: MOCK_PAGINATED_DECISIONS.items[0],
  participants: [],
  votes: [],
  ai_opinions: [
    {
      agent_id: 'ai_gpt4',
      agent_uuid: '00000000-0000-0000-0000-000000000101',
      agent_name: 'GPT-4o Governance Evaluator',
      agent_type: 'ai',
      role: 'Primary AI Risk Evaluator',
      provider: 'openai',
      model_version: 'gpt-4o',
      influence_weight: 1.2,
      participation_status: 'voted',
      vote: 'accept',
      recommendation: 'accept',
      confidence: 0.89,
      justification:
        'Strong DSCR and verifiable cash flow metrics satisfy commercial credit criteria.',
      bias_indicators: ['regional_proxy'],
      voted_at: '2026-11-11T09:15:00Z',
    },
  ],
  human_reviews: [
    {
      agent_id: 'human_sarah',
      agent_uuid: '00000000-0000-0000-0000-000000000201',
      agent_name: 'Dr. Sarah Chen',
      agent_type: 'human',
      role: 'Chief Governance Officer',
      provider: 'human',
      model_version: 'human-expert',
      influence_weight: 1.5,
      participation_status: 'voted',
      vote: 'accept',
      recommendation: 'accept',
      confidence: 0.94,
      justification:
        'Reviewed regional weighting; no adverse disparate impact found.',
      bias_indicators: [],
      voted_at: '2026-11-11T09:30:00Z',
    },
  ],
  consensus: {
    total_participants: 4,
    votes_cast: 3,
    pending_votes: 1,
    accept_votes: 2,
    reject_votes: 1,
    abstain_votes: 0,
    weighted_accept_score: 2.7,
    weighted_reject_score: 0.8,
    consensus_score: 0.78,
    average_confidence: 0.91,
    ai_consensus_rate: 0.82,
    human_consensus_rate: 0.94,
    consensus_status: 'consensus_reached',
    recommended_outcome: 'approve',
    explanation:
      'Weighted consensus favors approval (78.0%) with strong human reviewer alignment.',
  },
  bias_analysis: {
    overall_bias_score: 0.34,
    risk_level: 'medium',
    category_scores: {
      geographic_region: 0.34,
      gender: 0.12,
    },
    fairness_metrics: {
      demographic_parity: 0.91,
      equal_opportunity: 0.89,
      equalized_odds: 0.88,
      overall_fairness: 0.89,
    },
    recommendations: [
      'Monitor geographic zip-code proxy weighting during quarterly model calibration.',
    ],
  },
  governance_rules: [
    {
      id: 'rule-001',
      name: 'Fair Lending & Credit Governance Policy',
      description: 'Enforces ECOA fairness thresholds on commercial credit.',
      context: 'loan_approval',
      policy_type: 'threshold',
      rule_definition: 'max_bias_score: 0.50\nmin_consensus: 0.70',
      approval_threshold: 0.7,
      require_human_review: true,
      is_active: true,
      priority: 1,
      applied_count: 14,
      created_at: '2026-11-01T00:00:00Z',
      updated_at: '2026-11-01T00:00:00Z',
    },
  ],
  audit_trail: [
    {
      id: 'audit-901',
      decision_id: 'dec-7788-9900',
      decision_title: 'Commercial Credit Line — Horizon Logistics',
      actor_name: 'Dr. Sarah Chen',
      actor_type: 'human',
      event_type: 'vote_submitted',
      action: "Submitted vote 'accept' with 94% confidence",
      compliance_status: 'compliant',
      audit_hash: '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
      agent_actions: [],
      rules_applied: ['Fair Lending & Credit Governance Policy'],
      metadata: {},
      timestamp: '2026-11-11T09:30:00Z',
    },
  ],
};

function renderWithRoutes(initialEntries: string[]) {
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

describe('Phase 9 — Decision Registry & 7-Section Decision Workspace', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useAuthStore.getState().setSession(GOV_OFFICER_USER, 'gov-officer-jwt');
    vi.spyOn(decisionsService, 'listDecisions').mockResolvedValue(
      MOCK_PAGINATED_DECISIONS
    );
    vi.spyOn(decisionsService, 'getDecisionWorkspace').mockResolvedValue(
      MOCK_WORKSPACE
    );
  });

  it('renders DecisionsListPage with filtering and navigates to DecisionWorkspacePage', async () => {
    renderWithRoutes(['/app/decisions']);

    await waitFor(() => {
      expect(
        screen.getByText('Commercial Credit Line — Horizon Logistics')
      ).toBeInTheDocument();
    });

    expect(screen.getByText('1 Registered Decisions')).toBeInTheDocument();

    const workspaceLink = screen.getByRole('link', { name: /workspace/i });
    fireEvent.click(workspaceLink);

    await waitFor(() => {
      expect(
        screen.getByText('1. Decision Case Context & Structured Parameters')
      ).toBeInTheDocument();
    });
  });

  it('renders all 7 sections of DecisionWorkspacePage and submits votes and governance actions', async () => {
    const voteSpy = vi
      .spyOn(decisionsService, 'submitVote')
      .mockResolvedValue({
        id: 'vote-new',
        agent_id: 'human_sarah',
        decision_id: 'dec-7788-9900',
        influence_weight: 1.5,
        vote: 'accept',
        confidence: 0.88,
        justification: 'Confirmed cash flow coverage ratio meets policy.',
        bias_indicators: [],
        timestamp: '2026-11-11T12:00:00Z',
      });

    const govActionSpy = vi
      .spyOn(decisionsService, 'executeGovernanceAction')
      .mockResolvedValue({
        ...MOCK_PAGINATED_DECISIONS.items[0],
        status: 'approved',
      });

    renderWithRoutes(['/app/decisions/dec-7788-9900']);

    await waitFor(() => {
      expect(
        screen.getByText('1. Decision Case Context & Structured Parameters')
      ).toBeInTheDocument();
    });

    // Verify all 7 sections are rendered
    expect(
      screen.getByText('2. Weighted Multi-Agent Consensus Summary')
    ).toBeInTheDocument();
    expect(screen.getByText(/3. AI Agent Opinions/i)).toBeInTheDocument();
    expect(
      screen.getByText(/4. Human Reviewer Assessments/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText('5. ML Bias & Fairness Analysis')
    ).toBeInTheDocument();
    expect(
      screen.getByText(/6. Applicable Governance Policies/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        '7. Governance Resolution Controls & Cryptographic Audit Trail'
      )
    ).toBeInTheDocument();

    // Submit a vote
    const justificationInput = screen.getByLabelText(
      /Assessment Justification/i
    );
    fireEvent.change(justificationInput, {
      target: { value: 'Confirmed cash flow coverage ratio meets policy.' },
    });
    fireEvent.click(
      screen.getByRole('button', { name: /Record Assessment Vote/i })
    );

    await waitFor(() => {
      expect(voteSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          decision_id: 'dec-7788-9900',
          vote: 'accept',
          justification: 'Confirmed cash flow coverage ratio meets policy.',
        })
      );
    });

    // Execute Approve governance action
    fireEvent.click(screen.getByRole('button', { name: /^Approve$/i }));
    const govJustificationInput = screen.getByLabelText(
      /Mandatory Governance Justification/i
    );
    fireEvent.change(govJustificationInput, {
      target: {
        value: 'Consensus threshold met and fairness metrics verified.',
      },
    });
    fireEvent.click(
      screen.getByRole('button', { name: /Confirm & Sign Audit Record/i })
    );

    await waitFor(() => {
      expect(govActionSpy).toHaveBeenCalledWith('dec-7788-9900', {
        action: 'approve',
        justification: 'Consensus threshold met and fairness metrics verified.',
      });
    });
  });
});

