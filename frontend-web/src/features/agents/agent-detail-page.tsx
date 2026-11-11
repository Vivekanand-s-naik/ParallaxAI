import * as React from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Bot,
  History,
  Loader2,
  Sliders,
  UserCheck,
  Vote,
} from 'lucide-react';
import { queryKeys } from '@/app/query-client';
import { platformServices } from '@/services/platform-services';
import { PermissionGate } from '@/components/navigation/permission-guard';
import { PageHeader } from '@/components/common/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ErrorState } from '@/components/feedback/error-state';
import { LoadingSkeleton } from '@/components/feedback/loading-skeleton';
import { useUiStore } from '@/stores/ui-store';
import { normalizeApiError } from '@/services/api-error';
import { formatDateTime, formatPercent } from '@/lib/utils';

export function AgentDetailPage() {
  const { agentId = '' } = useParams<{ agentId: string }>();
  const queryClient = useQueryClient();
  const addToast = useUiStore((s) => s.addToast);

  const detailQuery = useQuery({
    queryKey: queryKeys.agents.detail(agentId),
    queryFn: () => platformServices.getAgentDetail(agentId),
    enabled: Boolean(agentId),
  });

  const [weightInput, setWeightInput] = React.useState<number | null>(null);

  const updateMutation = useMutation({
    mutationFn: (
      payload: Parameters<typeof platformServices.updateAgent>[1]
    ) => platformServices.updateAgent(agentId, payload),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.agents.detail(agentId),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.all });
      addToast({
        title: 'Agent Configuration Saved',
        description: `${updated.name} influence weight is now ${updated.influence_weight.toFixed(2)}x.`,
        variant: 'success',
      });
    },
    onError: (err) => {
      addToast({
        title: 'Update failed',
        description: normalizeApiError(err).message,
        variant: 'error',
      });
    },
  });

  if (detailQuery.isLoading) {
    return <LoadingSkeleton cards={4} rows={4} />;
  }

  if (detailQuery.isError || !detailQuery.data) {
    return (
      <ErrorState
        title={`Unable to load Agent Profile (${agentId})`}
        message={
          detailQuery.error
            ? normalizeApiError(detailQuery.error).message
            : 'Agent not found.'
        }
        onRetry={() => detailQuery.refetch()}
      />
    );
  }

  const { agent, voting_statistics, recent_votes, recent_activities } =
    detailQuery.data;
  const currentWeight = weightInput ?? agent.influence_weight;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Link
          to="/app/agents"
          className="inline-flex items-center gap-1 text-muted-foreground hover:text-primary"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Agent Registry
        </Link>
        <span>/</span>
        <span className="font-mono text-foreground">{agent.code}</span>
      </div>

      <PageHeader
        title={agent.name}
        description={`${agent.role} • Provider: ${
          agent.provider ?? agent.type
        } • Model: ${agent.model_version ?? 'N/A'}`}
        badge={
          <div className="flex items-center gap-2">
            <Badge variant={agent.type === 'ai' ? 'default' : 'info'}>
              {agent.type === 'ai' ? (
                <Bot className="mr-1 h-3 w-3" />
              ) : (
                <UserCheck className="mr-1 h-3 w-3" />
              )}
              {agent.type.toUpperCase()}
            </Badge>
            <Badge variant={agent.is_active ? 'success' : 'outline'}>
              {agent.is_active ? 'Active' : 'Inactive'}
            </Badge>
          </div>
        }
      />

      {/* Metrics & Calibration Row */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Vote className="h-4 w-4 text-primary" />
              Voting Reliability & Consensus Telemetry
            </CardTitle>
            <CardDescription>
              Historical voting distribution and average confidence across
              governance cases.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-lg border border-border bg-secondary/40 p-3">
              <div className="text-[11px] text-muted-foreground">
                Total Votes
              </div>
              <div className="mt-1 font-mono text-xl font-bold text-foreground">
                {voting_statistics.historical_vote_count}
              </div>
            </div>
            <div className="rounded-lg border border-border bg-secondary/40 p-3">
              <div className="text-[11px] text-muted-foreground">
                Accept Rate
              </div>
              <div className="mt-1 font-mono text-xl font-bold text-emerald-400">
                {formatPercent(voting_statistics.accept_rate * 100)}
              </div>
            </div>
            <div className="rounded-lg border border-border bg-secondary/40 p-3">
              <div className="text-[11px] text-muted-foreground">
                Avg Confidence
              </div>
              <div className="mt-1 font-mono text-xl font-bold text-sky-400">
                {formatPercent(voting_statistics.average_confidence * 100)}
              </div>
            </div>
            <div className="rounded-lg border border-border bg-secondary/40 p-3">
              <div className="text-[11px] text-muted-foreground">
                Influence Weight
              </div>
              <div className="mt-1 font-mono text-xl font-bold text-primary">
                {agent.influence_weight.toFixed(2)}x
              </div>
            </div>
          </CardContent>
        </Card>

        <PermissionGate permissions={['agents:manage']}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sliders className="h-4 w-4 text-sky-400" />
                Weight & Status Calibration
              </CardTitle>
              <CardDescription>
                Adjust governance influence weight or toggle participation.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1">
                <Label htmlFor="calibrate-weight">
                  Influence Multiplier ({currentWeight.toFixed(2)}x)
                </Label>
                <Input
                  id="calibrate-weight"
                  type="number"
                  step="0.1"
                  min="0.1"
                  max="5.0"
                  value={currentWeight}
                  onChange={(e) => setWeightInput(Number(e.target.value))}
                />
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  disabled={updateMutation.isPending}
                  onClick={() =>
                    updateMutation.mutate({ influence_weight: currentWeight })
                  }
                >
                  {updateMutation.isPending && (
                    <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                  )}
                  Save Weight
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={updateMutation.isPending}
                  onClick={() =>
                    updateMutation.mutate({ is_active: !agent.is_active })
                  }
                >
                  {agent.is_active ? 'Deactivate' : 'Activate'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </PermissionGate>
      </div>

      {/* Recent Votes & Audit Activity */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">
              Recent Decision Votes ({recent_votes.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5">
            {recent_votes.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No recorded votes for this agent.
              </p>
            ) : (
              recent_votes.slice(0, 10).map((v) => (
                <div
                  key={v.id}
                  className="rounded-lg border border-border bg-secondary/40 p-3 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <Link
                      to={`/app/decisions/${v.decision_id}`}
                      className="font-mono text-primary hover:underline"
                    >
                      Decision {v.decision_id.slice(0, 8)}…
                    </Link>
                    <Badge
                      variant={
                        v.vote === 'accept'
                          ? 'success'
                          : v.vote === 'reject'
                            ? 'destructive'
                            : 'warning'
                      }
                    >
                      {v.vote.toUpperCase()} ({Math.round(v.confidence * 100)}%)
                    </Badge>
                  </div>
                  <p className="mt-1.5 text-muted-foreground">
                    {v.justification}
                  </p>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <History className="h-4 w-4 text-sky-400" />
              Agent Audit Trail ({recent_activities.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5">
            {recent_activities.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No audit events logged for this agent.
              </p>
            ) : (
              recent_activities.slice(0, 10).map((log) => (
                <div
                  key={log.id}
                  className="rounded-lg border border-border bg-secondary/40 p-3 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-foreground">
                      {log.event_type.replace(/_/g, ' ')}
                    </span>
                    <span className="font-mono text-[11px] text-muted-foreground">
                      {formatDateTime(log.timestamp)}
                    </span>
                  </div>
                  <p className="mt-1 text-muted-foreground">{log.action}</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

