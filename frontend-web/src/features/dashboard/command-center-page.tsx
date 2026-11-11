import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Bot,
  CheckCircle2,
  Clock,
  Database,
  Eye,
  FileSearch,
  RefreshCw,
  Scale,
  Server,
  ShieldAlert,
  Split,
  Users,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { queryKeys } from '@/app/query-client';
import { PageHeader, SectionHeader } from '@/components/common/page-header';
import { StatCard } from '@/components/common/stat-card';
import { StatusBadge } from '@/components/common/status-badge';
import { EmptyState } from '@/components/feedback/empty-state';
import { ErrorState } from '@/components/feedback/error-state';
import { LoadingSkeleton } from '@/components/feedback/loading-skeleton';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { formatShortId, formatTimestamp } from '@/lib/utils';
import { normalizeApiError } from '@/services/api-error';
import { systemService } from '@/services/system-service';

export function CommandCenterPage() {
  const navigate = useNavigate();

  const {
    data: statsData,
    isLoading: isStatsLoading,
    isError: isStatsError,
    error: statsError,
    refetch: refetchStats,
    isFetching: isStatsFetching,
  } = useQuery({
    queryKey: queryKeys.system.stats(),
    queryFn: () => systemService.getCommandCenterStats(),
  });

  const { data: healthData } = useQuery({
    queryKey: queryKeys.system.health(),
    queryFn: () => systemService.getSystemHealth(),
  });

  if (isStatsLoading) {
    return (
      <div className="space-y-6" data-testid="command-center-loading">
        <PageHeader
          title="Command Center"
          description="Loading platform-wide human-AI governance telemetry…"
        />
        <LoadingSkeleton cards={6} rows={5} />
      </div>
    );
  }

  if (isStatsError || !statsData) {
    const apiErr = normalizeApiError(statsError);
    return (
      <div className="space-y-6">
        <PageHeader
          title="Command Center"
          description="Enterprise overview of collaborative human-AI decisions, agent participation, bias alerts, and governance health."
        />
        <ErrorState
          title="Failed to load Command Center telemetry"
          message={apiErr.message}
          onRetry={() => void refetchStats()}
        />
      </div>
    );
  }

  const {
    kpis,
    decision_activity,
    agent_activity,
    recent_decisions,
    recent_audit_logs,
    recent_notifications,
  } = statsData;

  const fairnessWarningsCount =
    kpis.high_bias_decisions + kpis.medium_bias_decisions;

  return (
    <div className="space-y-6" data-testid="command-center-page">
      <PageHeader
        title="Command Center"
        description="Real-time operational overview of collaborative human-AI decisions, multi-agent consensus, fairness posture, and compliance auditability."
        badge={
          <StatusBadge
            status={healthData?.status ?? 'healthy'}
            label={
              healthData?.status === 'degraded'
                ? 'System Degraded'
                : 'Platform Operational'
            }
          />
        }
        actions={
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void refetchStats()}
              disabled={isStatsFetching}
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${
                  isStatsFetching ? 'animate-spin' : ''
                }`}
              />
              <span>Refresh Telemetry</span>
            </Button>
            <Button asChild size="sm">
              <Link to="/app/decisions">
                <span>Open Decisions Workspace</span>
                <ArrowUpRight className="h-3.5 w-3.5" />
              </Link>
            </Button>
          </div>
        }
      />

      {/* Top-Level KPI Cards (6 Cards backed by PostgreSQL) */}
      <section
        aria-label="Key governance metrics"
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6"
      >
        <StatCard
          label="Total Decisions"
          value={kpis.total_decisions}
          sublabel={`${(kpis.approval_rate * 100).toFixed(0)}% approval rate`}
          icon={Split}
          tone="primary"
        />
        <StatCard
          label="Pending Decisions"
          value={kpis.pending_decisions}
          sublabel={`${kpis.decisions_last_24h} created in last 24h`}
          icon={Clock}
          tone="warning"
        />
        <StatCard
          label="Active AI Agents"
          value={kpis.ai_agents}
          sublabel={`${(kpis.ai_accuracy * 100).toFixed(0)}% historical alignment`}
          icon={Bot}
          tone="primary"
        />
        <StatCard
          label="Human Participants"
          value={kpis.human_agents}
          sublabel={`${kpis.total_votes} total votes cast`}
          icon={Users}
          tone="secondary"
        />
        <StatCard
          label="Requiring Review"
          value={kpis.decisions_requiring_review}
          sublabel={`${kpis.escalated_decisions} escalated decisions`}
          icon={ShieldAlert}
          tone={kpis.decisions_requiring_review > 0 ? 'warning' : 'success'}
        />
        <StatCard
          label="Bias Alerts"
          value={kpis.bias_incidents}
          sublabel={`${kpis.high_bias_decisions} high-risk decisions`}
          icon={Scale}
          tone={kpis.bias_incidents > 0 ? 'critical' : 'success'}
        />
      </section>

      {/* Main Analytics Row: A. Decision Activity & B. Agent Activity */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* A. Decision Activity Chart */}
        <Card className="lg:col-span-7">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Decision Activity</CardTitle>
                <CardDescription>
                  Approved, rejected, pending, and escalated decisions over time
                </CardDescription>
              </div>
              <Badge variant="outline" className="font-mono text-[11px]">
                {kpis.total_decisions} Total Records
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            {decision_activity.length === 0 ? (
              <EmptyState
                title="No decision activity recorded"
                description="Create a decision to populate timeline metrics."
              />
            ) : (
              <div
                data-testid="decision-activity-chart"
                className="h-72 w-full pt-2"
              >
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={decision_activity}
                    margin={{ top: 8, right: 12, left: -16, bottom: 0 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="hsl(217 26% 17%)"
                    />
                    <XAxis
                      dataKey="label"
                      tick={{ fill: '#94A3B8', fontSize: 11 }}
                      axisLine={{ stroke: '#1E293B' }}
                    />
                    <YAxis
                      allowDecimals={false}
                      tick={{ fill: '#94A3B8', fontSize: 11 }}
                      axisLine={{ stroke: '#1E293B' }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0F172A',
                        borderColor: '#1E293B',
                        borderRadius: '0.5rem',
                        fontSize: '12px',
                        color: '#F1F5F9',
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: '12px' }} />
                    <Bar
                      dataKey="approved"
                      name="Approved"
                      stackId="decisions"
                      fill="#10B981"
                      radius={[0, 0, 0, 0]}
                    />
                    <Bar
                      dataKey="pending"
                      name="Pending / Review"
                      stackId="decisions"
                      fill="#F59E0B"
                    />
                    <Bar
                      dataKey="rejected"
                      name="Rejected"
                      stackId="decisions"
                      fill="#EF4444"
                    />
                    <Bar
                      dataKey="escalated"
                      name="Escalated"
                      stackId="decisions"
                      fill="#8B5CF6"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        {/* B. Agent Activity & Participation */}
        <Card className="lg:col-span-5">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Agent Activity & Participation</CardTitle>
                <CardDescription>
                  Voting volume and confidence across AI and human evaluators
                </CardDescription>
              </div>
              <Link
                to="/app/agents"
                className="text-xs font-medium text-primary hover:underline"
              >
                Agent Registry →
              </Link>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {agent_activity.length === 0 ? (
              <EmptyState
                title="No active agents"
                description="Register AI or human evaluators in the Agent Registry."
              />
            ) : (
              <>
                <div
                  data-testid="agent-activity-chart"
                  className="h-44 w-full"
                >
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={agent_activity}
                      margin={{ top: 6, right: 8, left: -20, bottom: 0 }}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="hsl(217 26% 17%)"
                      />
                      <XAxis
                        dataKey="agent_id"
                        tick={{ fill: '#94A3B8', fontSize: 10 }}
                      />
                      <YAxis
                        allowDecimals={false}
                        tick={{ fill: '#94A3B8', fontSize: 10 }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#0F172A',
                          borderColor: '#1E293B',
                          borderRadius: '0.5rem',
                          fontSize: '12px',
                        }}
                      />
                      <Bar
                        dataKey="accept_votes"
                        name="Accept Votes"
                        stackId="votes"
                        fill="#06B6D4"
                      />
                      <Bar
                        dataKey="reject_votes"
                        name="Reject Votes"
                        stackId="votes"
                        fill="#8B5CF6"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                <div className="max-h-36 divide-y divide-border/60 overflow-y-auto rounded-md border border-border bg-background/50 px-3">
                  {agent_activity.map((agent) => (
                    <div
                      key={agent.agent_id}
                      className="flex items-center justify-between py-2 text-xs"
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="truncate font-medium text-foreground">
                            {agent.name}
                          </span>
                          <Badge
                            variant={
                              agent.type === 'ai' ? 'default' : 'secondary'
                            }
                            className="px-1.5 py-0 text-[10px]"
                          >
                            {agent.type.toUpperCase()}
                          </Badge>
                        </div>
                        <p className="truncate text-[11px] text-muted-foreground">
                          {agent.role}
                        </p>
                      </div>
                      <div className="text-right font-mono text-[11px]">
                        <span className="font-semibold text-foreground">
                          {agent.vote_count} votes
                        </span>
                        <p className="text-muted-foreground">
                          {(agent.average_confidence * 100).toFixed(0)}% conf ·{' '}
                          {agent.influence_weight.toFixed(1)}x
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* C. Governance Health & F. System Status */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* C. Governance Health */}
        <Card className="lg:col-span-7" data-testid="governance-health-card">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Governance Health & Policy Posture</CardTitle>
                <CardDescription>
                  Compliance rate, fairness warnings, escalations, and active
                  YAML policies
                </CardDescription>
              </div>
              <Link
                to="/app/governance"
                className="text-xs font-medium text-primary hover:underline"
              >
                Governance Console →
              </Link>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-lg border border-border bg-background/60 p-3">
                <p className="text-[11px] uppercase tracking-wider text-muted-foreground">
                  Governance Violations
                </p>
                <p className="mt-1 font-mono text-xl font-semibold text-foreground">
                  {kpis.governance_violations}
                </p>
                <p className="mt-0.5 text-[11px] text-muted-foreground">
                  Policy threshold alerts
                </p>
              </div>

              <div className="rounded-lg border border-border bg-background/60 p-3">
                <p className="text-[11px] uppercase tracking-wider text-muted-foreground">
                  Fairness Warnings
                </p>
                <p className="mt-1 font-mono text-xl font-semibold text-amber-300">
                  {fairnessWarningsCount}
                </p>
                <p className="mt-0.5 text-[11px] text-muted-foreground">
                  {kpis.high_bias_decisions} high / {kpis.medium_bias_decisions}{' '}
                  medium bias
                </p>
              </div>

              <div className="rounded-lg border border-border bg-background/60 p-3">
                <p className="text-[11px] uppercase tracking-wider text-muted-foreground">
                  Escalated Decisions
                </p>
                <p className="mt-1 font-mono text-xl font-semibold text-red-300">
                  {kpis.escalated_decisions}
                </p>
                <p className="mt-0.5 text-[11px] text-muted-foreground">
                  Awaiting officer action
                </p>
              </div>

              <div className="rounded-lg border border-border bg-background/60 p-3">
                <p className="text-[11px] uppercase tracking-wider text-muted-foreground">
                  Pending Human Reviews
                </p>
                <p className="mt-1 font-mono text-xl font-semibold text-primary">
                  {kpis.decisions_requiring_review}
                </p>
                <p className="mt-0.5 text-[11px] text-muted-foreground">
                  Human-in-the-loop queue
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="flex items-center justify-between rounded-md border border-border bg-card px-3.5 py-2.5 text-xs">
                <span className="text-muted-foreground">
                  Audit Compliance Rate
                </span>
                <span className="font-mono font-semibold text-emerald-300">
                  {(kpis.compliance_rate * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex items-center justify-between rounded-md border border-border bg-card px-3.5 py-2.5 text-xs">
                <span className="text-muted-foreground">
                  Weighted Consensus Rate
                </span>
                <span className="font-mono font-semibold text-primary">
                  {(kpis.consensus_rate * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex items-center justify-between rounded-md border border-border bg-card px-3.5 py-2.5 text-xs">
                <span className="text-muted-foreground">
                  Active Governance Rules
                </span>
                <span className="font-mono font-semibold text-foreground">
                  {kpis.active_rules} / {kpis.total_rules}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* F. System Status */}
        <Card className="lg:col-span-5" data-testid="system-status-card">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>System & Infrastructure Status</CardTitle>
                <CardDescription>
                  Live readiness of database, cache, ML models, and AI providers
                </CardDescription>
              </div>
              <Server className="h-4 w-4 text-primary" />
            </div>
          </CardHeader>
          <CardContent className="space-y-2.5 text-xs">
            <ServiceStatusRow
              label="FastAPI Governance Engine"
              detail={`v${healthData?.services.backend_api.version ?? '2.0.0'}`}
              status={healthData?.services.backend_api.status ?? 'healthy'}
            />
            <ServiceStatusRow
              label="PostgreSQL 16 Persistence"
              detail={
                healthData?.services.postgresql.connected
                  ? 'Connected (SQLAlchemy 2.0)'
                  : 'Connection Degraded'
              }
              status={healthData?.services.postgresql.status ?? 'healthy'}
            />
            <ServiceStatusRow
              label="Redis 7 Rate Limiter"
              detail={
                healthData?.services.redis.connected
                  ? 'Active Window Enforcement'
                  : 'In-Memory Fallback Active'
              }
              status={healthData?.services.redis.status ?? 'healthy'}
            />
            <ServiceStatusRow
              label="ML Bias & Anomaly Detector"
              detail={
                healthData?.services.ml_bias_engine.models_trained
                  ? 'IsolationForest + RandomForest Ready'
                  : 'Heuristic Fallback Mode'
              }
              status={healthData?.services.ml_bias_engine.status ?? 'healthy'}
            />
            <ServiceStatusRow
              label="AI Provider Integrations"
              detail={
                healthData?.services.ai_providers.openai_configured ||
                healthData?.services.ai_providers.anthropic_configured
                  ? 'Live LLM Providers Connected'
                  : 'Deterministic Governance Fallback'
              }
              status="healthy"
            />
          </CardContent>
        </Card>
      </div>

      {/* D. Recent Decisions Table & E. Real-Time Activity Feed */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* D. Recent Decisions Table */}
        <Card className="lg:col-span-8" data-testid="recent-decisions-card">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Recent Decisions</CardTitle>
                <CardDescription>
                  Latest collaborative human-AI decisions evaluated by the
                  platform
                </CardDescription>
              </div>
              <Button asChild variant="outline" size="sm">
                <Link to="/app/decisions">View All Decisions</Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {recent_decisions.length === 0 ? (
              <EmptyState
                title="No decisions recorded yet"
                description="Create a decision in the Decisions workspace to begin evaluation."
              />
            ) : (
              <div className="overflow-x-auto rounded-lg border border-border">
                <table className="w-full border-collapse text-left text-xs">
                  <thead>
                    <tr className="border-b border-border bg-muted/40 font-semibold uppercase tracking-wider text-muted-foreground">
                      <th className="px-3.5 py-2.5">ID</th>
                      <th className="px-3.5 py-2.5">Title / Context</th>
                      <th className="px-3.5 py-2.5">Category</th>
                      <th className="px-3.5 py-2.5">Status</th>
                      <th className="px-3.5 py-2.5">Consensus</th>
                      <th className="px-3.5 py-2.5">Bias Score</th>
                      <th className="px-3.5 py-2.5">Created</th>
                      <th className="px-3.5 py-2.5 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {recent_decisions.map((dec) => (
                      <tr
                        key={dec.id}
                        className="transition-colors hover:bg-accent/40"
                      >
                        <td className="px-3.5 py-2.5 font-mono text-[11px] text-muted-foreground">
                          {formatShortId(dec.id)}
                        </td>
                        <td className="max-w-xs px-3.5 py-2.5">
                          <p className="truncate font-semibold text-foreground">
                            {dec.title}
                          </p>
                          <p className="truncate text-[11px] text-muted-foreground">
                            {dec.context}
                          </p>
                        </td>
                        <td className="px-3.5 py-2.5">
                          <Badge variant="outline" className="font-mono">
                            {dec.application_type}
                          </Badge>
                        </td>
                        <td className="px-3.5 py-2.5">
                          <StatusBadge status={dec.status} />
                        </td>
                        <td className="px-3.5 py-2.5 font-mono">
                          {(dec.consensus_score * 100).toFixed(0)}% (
                          {dec.vote_count} votes)
                        </td>
                        <td className="px-3.5 py-2.5">
                          <span
                            className={`font-mono font-semibold ${
                              dec.bias_score > 0.7
                                ? 'text-red-400'
                                : dec.bias_score > 0.4
                                  ? 'text-amber-300'
                                  : 'text-emerald-300'
                            }`}
                          >
                            {dec.bias_score.toFixed(2)}
                          </span>
                        </td>
                        <td className="px-3.5 py-2.5 font-mono text-[11px] text-muted-foreground">
                          {formatTimestamp(dec.created_at)}
                        </td>
                        <td className="px-3.5 py-2.5 text-right">
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              navigate(`/app/decisions/${dec.id}`)
                            }
                          >
                            <Eye className="h-3.5 w-3.5" />
                            <span>Inspect</span>
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* E. Real-Time Activity Feed */}
        <Card className="lg:col-span-4" data-testid="activity-feed-card">
          <CardHeader className="pb-3">
            <SectionHeader
              title="Governance Activity Feed"
              description="Recent audit events, votes, and alerts from PostgreSQL"
              actions={<Activity className="h-4 w-4 text-primary" />}
            />
          </CardHeader>
          <CardContent className="space-y-3">
            {recent_audit_logs.length === 0 &&
            recent_notifications.length === 0 ? (
              <EmptyState
                title="No recent governance events"
                description="Audit events and notifications will appear here as decisions are evaluated."
              />
            ) : (
              <ul className="max-h-96 divide-y divide-border/60 overflow-y-auto pr-1">
                {recent_audit_logs.slice(0, 6).map((log) => (
                  <li key={log.id} className="py-2.5 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <FileSearch className="h-3.5 w-3.5 text-primary" />
                        <span className="font-semibold text-foreground">
                          {log.actor_name}
                        </span>
                      </div>
                      <span className="font-mono text-[10px] text-muted-foreground">
                        {formatTimestamp(log.timestamp)}
                      </span>
                    </div>
                    <p className="mt-1 text-muted-foreground">{log.action}</p>
                    <div className="mt-1.5 flex items-center gap-2">
                      <StatusBadge status={log.compliance_status} />
                      <span className="font-mono text-[10px] text-muted-foreground">
                        {log.audit_hash.slice(0, 16)}…
                      </span>
                    </div>
                  </li>
                ))}

                {recent_notifications.slice(0, 4).map((notif) => (
                  <li key={notif.id} className="py-2.5 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                        <span className="font-semibold text-foreground">
                          {notif.title}
                        </span>
                      </div>
                      <StatusBadge status={notif.priority} />
                    </div>
                    <p className="mt-1 text-muted-foreground">
                      {notif.message}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function ServiceStatusRow({
  label,
  detail,
  status,
}: {
  label: string;
  detail: string;
  status: string;
}) {
  const isHealthy = status === 'healthy' || status === 'ready';
  return (
    <div className="flex items-center justify-between rounded-md border border-border bg-background/60 px-3 py-2">
      <div className="min-w-0">
        <p className="truncate font-medium text-foreground">{label}</p>
        <p className="truncate font-mono text-[11px] text-muted-foreground">
          {detail}
        </p>
      </div>
      <div className="flex items-center gap-1.5">
        {isHealthy ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
        ) : (
          <Database className="h-4 w-4 text-amber-400" />
        )}
        <StatusBadge status={status} showDot={false} />
      </div>
    </div>
  );
}
