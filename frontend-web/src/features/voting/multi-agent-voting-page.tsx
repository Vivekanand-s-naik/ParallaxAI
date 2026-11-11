import * as React from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowUpRight,
  Bot,
  Loader2,
  RefreshCw,
  Scale,
  UserCheck,
  Vote,
} from 'lucide-react';
import { queryKeys } from '@/app/query-client';
import { decisionsService } from '@/services/decisions-service';
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
import { Textarea } from '@/components/ui/textarea';
import { EmptyState } from '@/components/feedback/empty-state';
import { ErrorState } from '@/components/feedback/error-state';
import { LoadingSkeleton } from '@/components/feedback/loading-skeleton';
import { useUiStore } from '@/stores/ui-store';
import { normalizeApiError } from '@/services/api-error';
import { formatDateTime, formatPercent } from '@/lib/utils';
import type { VoteChoice } from '@/types/governance';

export function MultiAgentVotingPage() {
  const queryClient = useQueryClient();
  const addToast = useUiStore((s) => s.addToast);

  const [selectedDecisionId, setSelectedDecisionId] = React.useState('');
  const [voteFilter, setVoteFilter] = React.useState('');

  // Quick vote form
  const [voteChoice, setVoteChoice] = React.useState<VoteChoice>('accept');
  const [confidence, setConfidence] = React.useState(0.9);
  const [justification, setJustification] = React.useState('');

  const decisionsQuery = useQuery({
    queryKey: queryKeys.decisions.list({ page_size: 50 }),
    queryFn: () => decisionsService.listDecisions({ page_size: 50 }),
  });

  const activeDecisionId =
    selectedDecisionId || decisionsQuery.data?.items[0]?.id || '';

  const votesQuery = useQuery({
    queryKey: queryKeys.votes.list({
      decision_id: selectedDecisionId || undefined,
      vote: voteFilter || undefined,
    }),
    queryFn: () =>
      platformServices.listVotes({
        decision_id: selectedDecisionId || undefined,
        vote: voteFilter || undefined,
      }),
  });

  const summaryQuery = useQuery({
    queryKey: queryKeys.votes.summary(activeDecisionId),
    queryFn: () => platformServices.getDecisionVotingSummary(activeDecisionId),
    enabled: Boolean(activeDecisionId),
  });

  const submitVoteMutation = useMutation({
    mutationFn: (payload: Parameters<typeof platformServices.submitVote>[0]) =>
      platformServices.submitVote(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.votes.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.decisions.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.system.stats() });
      setJustification('');
      addToast({
        title: 'Governance Vote Recorded',
        description:
          'Consensus matrix and weighted agreement scores updated in real time.',
        variant: 'success',
      });
    },
    onError: (err) => {
      addToast({
        title: 'Unable to submit vote',
        description: normalizeApiError(err).message,
        variant: 'error',
      });
    },
  });

  const handleVoteSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeDecisionId) return;
    if (justification.trim().length < 5) {
      addToast({
        title: 'Justification required',
        description: 'Enter at least 5 characters explaining your vote.',
        variant: 'warning',
      });
      return;
    }
    submitVoteMutation.mutate({
      decision_id: activeDecisionId,
      vote: voteChoice,
      recommendation: voteChoice,
      confidence,
      justification: justification.trim(),
    });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Multi-Agent Voting & Consensus Matrix"
        description="Compare AI model recommendations and human reviewer votes side-by-side, inspect weighted consensus breakdowns, and cast auditable governance votes."
        badge={
          <Badge variant="default">
            {votesQuery.data?.length ?? 0} Recorded Votes
          </Badge>
        }
        actions={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              votesQuery.refetch();
              if (activeDecisionId) summaryQuery.refetch();
            }}
          >
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            Refresh Ledger
          </Button>
        }
      />

      {/* Decision Selector & Consensus Summary */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Scale className="h-4 w-4 text-sky-400" />
                  Decision Consensus Inspector
                </CardTitle>
                <CardDescription>
                  Select a decision case to inspect weighted AI vs. human
                  consensus.
                </CardDescription>
              </div>
              <select
                aria-label="Select decision for consensus inspection"
                value={selectedDecisionId}
                onChange={(e) => setSelectedDecisionId(e.target.value)}
                className="h-9 rounded-md border border-border bg-secondary/40 px-3 text-xs text-foreground"
              >
                <option value="">All Decisions (Showing Latest Summary)</option>
                {decisionsQuery.data?.items.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.title} ({d.status})
                  </option>
                ))}
              </select>
            </div>
          </CardHeader>
          <CardContent>
            {summaryQuery.data ? (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-secondary/40 p-3">
                  <div>
                    <div className="text-sm font-semibold text-foreground">
                      {summaryQuery.data.decision_title}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {summaryQuery.data.consensus.explanation}
                    </div>
                  </div>
                  <Button asChild variant="secondary" size="sm">
                    <Link
                      to={`/app/decisions/${summaryQuery.data.decision_id}`}
                    >
                      Open Workspace
                      <ArrowUpRight className="ml-1 h-3.5 w-3.5" />
                    </Link>
                  </Button>
                </div>

                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <div className="rounded-lg border border-border bg-secondary/30 p-3">
                    <div className="text-[11px] text-muted-foreground">
                      Consensus Score
                    </div>
                    <div className="mt-1 font-mono text-xl font-bold text-foreground">
                      {formatPercent(
                        summaryQuery.data.consensus.consensus_score * 100
                      )}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border bg-secondary/30 p-3">
                    <div className="text-[11px] text-muted-foreground">
                      Weighted Accept
                    </div>
                    <div className="mt-1 font-mono text-xl font-bold text-emerald-400">
                      {summaryQuery.data.consensus.weighted_accept_score.toFixed(
                        2
                      )}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border bg-secondary/30 p-3">
                    <div className="text-[11px] text-muted-foreground">
                      Weighted Reject
                    </div>
                    <div className="mt-1 font-mono text-xl font-bold text-red-400">
                      {summaryQuery.data.consensus.weighted_reject_score.toFixed(
                        2
                      )}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border bg-secondary/30 p-3">
                    <div className="text-[11px] text-muted-foreground">
                      Recommended
                    </div>
                    <div className="mt-1 font-mono text-lg font-bold uppercase text-sky-400">
                      {summaryQuery.data.consensus.recommended_outcome}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                Select a decision case to view consensus metrics.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Submit Vote Card */}
        <PermissionGate
          permissions={['voting:participate']}
          fallback={
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Read-Only Voting Access</CardTitle>
                <CardDescription>
                  Your role has permission to inspect multi-agent votes.
                  Submitting votes requires the <code>voting:participate</code>{' '}
                  permission.
                </CardDescription>
              </CardHeader>
            </Card>
          }
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <Vote className="h-4 w-4 text-sky-400" />
                Cast Governance Vote
              </CardTitle>
              <CardDescription>
                Submit or update your vote for the selected decision case.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleVoteSubmit} className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <Label htmlFor="matrix-vote-choice">Vote</Label>
                    <select
                      id="matrix-vote-choice"
                      value={voteChoice}
                      onChange={(e) =>
                        setVoteChoice(e.target.value as VoteChoice)
                      }
                      className="h-9 w-full rounded-md border border-border bg-secondary/40 px-2.5 text-xs text-foreground"
                    >
                      <option value="accept">Accept</option>
                      <option value="reject">Reject</option>
                      <option value="abstain">Abstain</option>
                    </select>
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="matrix-vote-conf">
                      Confidence ({Math.round(confidence * 100)}%)
                    </Label>
                    <Input
                      id="matrix-vote-conf"
                      type="number"
                      step="0.05"
                      min="0.1"
                      max="1.0"
                      value={confidence}
                      onChange={(e) => setConfidence(Number(e.target.value))}
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  <Label htmlFor="matrix-vote-just">Justification</Label>
                  <Textarea
                    id="matrix-vote-just"
                    rows={2}
                    placeholder="Provide domain rationale..."
                    value={justification}
                    onChange={(e) => setJustification(e.target.value)}
                  />
                </div>
                <Button
                  type="submit"
                  size="sm"
                  className="w-full"
                  disabled={submitVoteMutation.isPending || !activeDecisionId}
                >
                  {submitVoteMutation.isPending && (
                    <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                  )}
                  Submit Vote
                </Button>
              </form>
            </CardContent>
          </Card>
        </PermissionGate>
      </div>

      {/* Votes Ledger Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-sm">
              Recorded Multi-Agent Votes Ledger
            </CardTitle>
            <CardDescription>
              Chronological audit of AI and human participant votes.
            </CardDescription>
          </div>
          <select
            aria-label="Filter votes by position"
            value={voteFilter}
            onChange={(e) => setVoteFilter(e.target.value)}
            className="h-8 rounded-md border border-border bg-secondary/40 px-2.5 text-xs text-foreground"
          >
            <option value="">All Positions</option>
            <option value="accept">Accept</option>
            <option value="reject">Reject</option>
            <option value="abstain">Abstain</option>
          </select>
        </CardHeader>
        <CardContent>
          {votesQuery.isLoading ? (
            <LoadingSkeleton cards={2} rows={5} />
          ) : votesQuery.isError ? (
            <ErrorState
              title="Unable to load votes ledger"
              message={normalizeApiError(votesQuery.error).message}
              onRetry={() => votesQuery.refetch()}
            />
          ) : !votesQuery.data || votesQuery.data.length === 0 ? (
            <EmptyState
              icon={Vote}
              title="No votes recorded for this filter"
              description="Cast a vote or clear the position filter to view the ledger."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-border bg-muted/40 text-muted-foreground">
                    <th className="px-4 py-2.5 font-medium">Participant</th>
                    <th className="px-4 py-2.5 font-medium">Decision Case</th>
                    <th className="px-4 py-2.5 font-medium">Vote</th>
                    <th className="px-4 py-2.5 font-medium">
                      Confidence / Weight
                    </th>
                    <th className="px-4 py-2.5 font-medium">Justification</th>
                    <th className="px-4 py-2.5 font-medium">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {votesQuery.data.map((v) => (
                    <tr key={v.id} className="hover:bg-muted/20">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2 font-medium text-foreground">
                          {v.agent_type === 'ai' ? (
                            <Bot className="h-3.5 w-3.5 text-primary" />
                          ) : (
                            <UserCheck className="h-3.5 w-3.5 text-sky-400" />
                          )}
                          <span>{v.agent_name ?? v.agent_id}</span>
                        </div>
                        <div className="text-[11px] text-muted-foreground">
                          {v.agent_role}
                        </div>
                      </td>
                      <td className="px-4 py-3 font-mono">
                        <Link
                          to={`/app/decisions/${v.decision_id}`}
                          className="text-primary hover:underline"
                        >
                          {v.decision_id.slice(0, 12)}…
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        <Badge
                          variant={
                            v.vote === 'accept'
                              ? 'success'
                              : v.vote === 'reject'
                                ? 'destructive'
                                : 'warning'
                          }
                        >
                          {v.vote.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 font-mono text-foreground">
                        {formatPercent(v.confidence * 100)} •{' '}
                        {v.influence_weight.toFixed(2)}x
                      </td>
                      <td className="max-w-md px-4 py-3 text-muted-foreground">
                        {v.justification}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {formatDateTime(v.timestamp)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

