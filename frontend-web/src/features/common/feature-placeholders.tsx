import { useParams } from 'react-router-dom';
import {
  Bell,
  Bot,
  FileSearch,
  GitBranch,
  LayoutDashboard,
  Scale,
  Settings,
  ShieldCheck,
  Split,
  Users,
  Vote,
} from 'lucide-react';
import { ModulePlaceholder } from '@/components/common/module-placeholder';

export function DashboardPlaceholderPage() {
  return (
    <ModulePlaceholder
      title="Command Center"
      description="Enterprise overview of collaborative human-AI decisions, agent participation, bias alerts, and governance health."
      phaseLabel="Phase 8"
      endpointContract="GET /api/v1/system/stats"
      requiredPermissions={['decisions:read']}
      icon={LayoutDashboard}
      capabilities={[
        'Live KPI cards calculated from PostgreSQL decision, agent, and notification records',
        'Recharts time-series visualization of approved, rejected, escalated, and pending decisions',
        'Agent participation and consensus alignment breakdown',
        'Recent decisions table and real-time governance activity feed',
      ]}
    />
  );
}

export function DecisionsListPlaceholderPage() {
  return (
    <ModulePlaceholder
      title="Decisions Registry"
      description="Search, filter, create, and govern collaborative human-AI decisions across high-stakes domains."
      phaseLabel="Phase 9"
      endpointContract="GET /api/v1/decisions"
      requiredPermissions={['decisions:read']}
      icon={Split}
      capabilities={[
        'Server-side search, status, domain category, risk level, priority, and bias score filtering',
        'Decision creation modal with applicant data, priority, and agent assignment',
        'Direct navigation to the 7-section Decision Governance Workspace',
      ]}
    />
  );
}

export function DecisionWorkspacePlaceholderPage() {
  const { decisionId } = useParams<{ decisionId: string }>();
  return (
    <ModulePlaceholder
      title={`Decision Workspace — ${decisionId ?? 'Record'}`}
      description="Comprehensive 7-section human-AI evaluation workspace for transparent consensus, bias inspection, and governance actions."
      phaseLabel="Phase 9"
      endpointContract={`GET /api/v1/decisions/${decisionId ?? ':decisionId'}/workspace`}
      requiredPermissions={['decisions:read']}
      icon={Split}
      capabilities={[
        '1. Decision Summary & Metadata, 2. Participating AI & Human Agents, 3. Multi-Agent Voting Matrix',
        '4. Consensus Analysis, 5. ML Bias & Fairness Analysis, 6. Applied Governance Policies',
        '7. Immutable Audit Trail & Governance Action Controls (Approve, Reject, Escalate with mandatory justification)',
      ]}
    />
  );
}

export function AgentRegistryPlaceholderPage() {
  return (
    <ModulePlaceholder
      title="Agent Registry"
      description="Monitor and configure AI model evaluators and authorized human governance reviewers."
      phaseLabel="Phase 10"
      endpointContract="GET /api/v1/agents"
      requiredPermissions={['agents:read']}
      icon={Bot}
      capabilities={[
        'Directory of AI agents (OpenAI, Anthropic, BERT) and Human Reviewer agents',
        'Influence weight, confidence threshold, and participation telemetry',
        'Agent registration and configuration controls for authorized administrators',
      ]}
    />
  );
}

export function AgentDetailPlaceholderPage() {
  const { agentId } = useParams<{ agentId: string }>();
  return (
    <ModulePlaceholder
      title={`Agent Profile — ${agentId ?? 'Agent'}`}
      description="Detailed voting history, confidence distribution, and influence weight configuration."
      phaseLabel="Phase 10"
      endpointContract={`GET /api/v1/agents/${agentId ?? ':agentId'}`}
      requiredPermissions={['agents:read']}
      icon={Bot}
      capabilities={[
        'Historical vote breakdown (accept, reject, abstain) and average confidence',
        'Assigned decision participation records from PostgreSQL',
        'Influence weight and active status management (requires agents:manage)',
      ]}
    />
  );
}

export function VotingMatrixPlaceholderPage() {
  return (
    <ModulePlaceholder
      title="Multi-Agent Voting"
      description="Compare AI and human recommendations, inspect weighted consensus, and submit human reviewer votes."
      phaseLabel="Phase 10"
      endpointContract="GET /api/v1/votes & POST /api/v1/votes"
      requiredPermissions={['voting:read', 'voting:participate']}
      icon={Vote}
      capabilities={[
        'Side-by-side AI vs. Human vote comparison with confidence and bias indicators',
        'Weighted consensus calculation (influence_weight × confidence)',
        'Authenticated human vote submission form triggering live consensus & ML bias recalculation',
      ]}
    />
  );
}

export function InfluenceGraphPlaceholderPage() {
  return (
    <ModulePlaceholder
      title="Influence Graph"
      description="Interactive React Flow topology of AI agents, human reviewers, decisions, and pairwise agreement edges."
      phaseLabel="Phase 10"
      endpointContract="GET /api/v1/agents/influence-graph"
      requiredPermissions={['agents:read']}
      icon={GitBranch}
      capabilities={[
        'Interactive @xyflow/react canvas with custom Agent and Decision nodes',
        'Real vote edges and pairwise agent alignment edges computed from PostgreSQL',
        'Node inspection drawer with influence weight and agreement metrics',
      ]}
    />
  );
}

export function BiasScannerPlaceholderPage() {
  return (
    <ModulePlaceholder
      title="Bias & Fairness Scanner"
      description="ML-driven fairness metrics, demographic parity analysis, and anomaly detection across decisions."
      phaseLabel="Phase 10"
      endpointContract="GET /api/v1/bias/overview"
      requiredPermissions={['bias:read']}
      icon={Scale}
      capabilities={[
        'Demographic parity, equal opportunity, equalized odds, and overall fairness indicators',
        'Category bias breakdown (Demographic, Geographic, Economic, Experiential, Procedural)',
        'On-demand ML bias scan and human governance review escalation trigger',
      ]}
    />
  );
}

export function GovernanceConsolePlaceholderPage() {
  return (
    <ModulePlaceholder
      title="Governance Console"
      description="Author, validate, and enforce YAML-based governance rules and escalation thresholds."
      phaseLabel="Phase 10"
      endpointContract="GET /api/v1/governance/rules"
      requiredPermissions={['governance:read', 'governance:manage']}
      icon={ShieldCheck}
      capabilities={[
        'Policy rule table with context, priority, approval thresholds, and active status',
        'YAML policy editor with real-time syntax validation via POST /api/v1/governance/validate-yaml',
        'Role-gated rule creation, activation, and deletion',
      ]}
    />
  );
}

export function AuditExplainabilityPlaceholderPage() {
  return (
    <ModulePlaceholder
      title="Audit & Explainability"
      description="Immutable SHA-256 governance audit records, compliance status verification, and decision trace."
      phaseLabel="Phase 10"
      endpointContract="GET /api/v1/audit"
      requiredPermissions={['audit:read']}
      icon={FileSearch}
      capabilities={[
        'Read-only, tamper-evident audit log with actor, event type, status transition, and SHA-256 hash',
        'Searchable and filterable by compliance status, actor type, decision, and date range',
        'Decision-level explainability trace combining votes, rules applied, and status history',
      ]}
    />
  );
}

export function NotificationsPlaceholderPage() {
  return (
    <ModulePlaceholder
      title="Notifications Center"
      description="Governance alerts, high-bias warnings, rule violations, and human review escalations."
      phaseLabel="Phase 10"
      endpointContract="GET /api/v1/notifications"
      requiredPermissions={['notifications:read']}
      icon={Bell}
      capabilities={[
        'Filterable list of unread and historical governance notifications',
        'Mark individual or all notifications as read in PostgreSQL',
        'Direct links from bias and escalation alerts to the affected decision workspace',
      ]}
    />
  );
}

export function UsersAndRolesPlaceholderPage() {
  return (
    <ModulePlaceholder
      title="Users & Roles"
      description="Manage operator accounts, RBAC role assignments, and the 19-permission governance matrix."
      phaseLabel="Phase 10"
      endpointContract="GET /api/v1/users & GET /api/v1/roles"
      requiredPermissions={['users:read', 'roles:manage']}
      icon={Users}
      capabilities={[
        'Operator directory with account status activation/deactivation and session revocation',
        'Role assignment modal with SUPER_ADMIN privilege escalation safeguards',
        'Interactive role-permission matrix for system and custom governance roles',
      ]}
    />
  );
}

export function SettingsPlaceholderPage() {
  return (
    <ModulePlaceholder
      title="System Settings"
      description="Inspect platform infrastructure health, AI provider readiness, authentication security, and rate limits."
      phaseLabel="Phase 10"
      endpointContract="GET /api/v1/system/settings & GET /api/v1/system/health"
      requiredPermissions={['system:configure']}
      icon={Settings}
      capabilities={[
        'Live connectivity status for PostgreSQL 16, Redis 7, WebSocket hub, and ML Bias Engine',
        'Safe AI provider configuration status (OpenAI, Anthropic, Gemini) without exposing secrets',
        'Active Redis rate-limiting thresholds and Argon2id + JWT session parameters',
      ]}
    />
  );
}

