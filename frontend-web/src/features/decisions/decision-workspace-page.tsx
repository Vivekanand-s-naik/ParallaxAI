import * as React from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  ArrowLeft,
  Bot,
  CheckCircle2,
  Cpu,
  FileCode2,
  Gavel,
  Loader2,
  RefreshCw,
  Scale,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  UserCheck,
  Vote,
  XCircle,
} from 'lucide-react';
import { queryKeys } from '@/app/query-client';
import { decisionsService } from '@/services/decisions-service';
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { ErrorState } from '@/components/feedback/error-state';
import { LoadingSkeleton } from '@/components/feedback/loading-skeleton';
import { useUiStore } from '@/stores/ui-store';
import { normalizeApiError } from '@/services/api-error';
import { formatDateTime, formatPercent } from '@/lib/utils';
import type {
  AgentOpinionCard,
  DecisionStatus,
  VoteChoice,
} from '@/types/governance';

function statusBadgeVariant(status: DecisionStatus) {
  switch (status) {
    case 'approved':
      return 'success' as const;
    case 'rejected':
      return 'destructive' as const;
    case 'escalated':
      return 'warning' as const;
    case 'under_review':
      return 'info' as const;
    default:
      return 'outline' as const;
  }
}

function voteBadgeVariant(vote?: VoteChoice | null) {
  switch (vote) {
    case 'accept':
      return 'success' as const;
    case 'reject':
      return 'destructive' as const;
    case 'abstain':
      return 'warning' as const;
    default:
      return 'outline' as const;
  }
}

function OpinionCard({ opinion }: { opinion: AgentOpinionCard }) {
  const isAi = opinion.agent_type === 'ai';
  return (
    <div className="rounded-lg border border-border bg-secondary/40 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div
            className={`flex h-9 w-9 items-center justify-center rounded-md border ${
              isAi
                ? 'border-primary/40 bg-primary/10 text-primary'
                : 'border-sky-500/40 bg-sky-500/10 text-sky-300'
            }`}
          >
            {isAi ? (
              <Bot className="h-4 w-4" />
            ) : (
              <UserCheck className="h-4 w-4" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-foreground">
                {opinion.agent_name}
              </span>
              <Badge variant={isAi ? 'default' : 'info'}>{opinion.role}</Badge>
            </div>
            <div className="mt-0.5 flex flex-wrap items-center gap-2 font-mono text-[11px] text-muted-foreground">
              <span>{opinion.agent_id}</span>
              {opinion.model_version && <span>• {opinion.model_version}</span>}
              <span>• Weight: {opinion.influence_weight.toFixed(2)}x</span>
            </div>
          </div>
        </div>

        <div className="text-right">
          {opinion.participation_status === 'voted' && opinion.vote ? (
            <div className="space-y-1">
              <Badge variant={voteBadgeVariant(opinion.vote)}>
                {opinion.vote.toUpperCase()}
              </Badge>
              {opinion.confidence !== null &&
                opinion.confidence !== undefined && (
                  <div className="font-mono text-[11px] text-muted-foreground">
                    Conf: {formatPercent(opinion.confidence * 100)}
                  </div>
                )}
            </div>
          ) : (
            <Badge variant="outline">Pending Vote</Badge>
          )}
        </div>
      </div>

      {opinion.justification ? (
        <p className="mt-3 rounded border border-border/60 bg-card/70 p-2.5 text-xs leading-relaxed text-muted-foreground">
          {opinion.justification}
        </p>
      ) : (
        <p className="mt-3 text-xs italic text-muted-foreground">
          No formal justification submitted yet.
        </p>
      )}

      {opinion.bias_indicators && opinion.bias_indicators.length > 0 && (
        <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] text-muted-foreground">
            Flagged Factors:
          </span>
          {opinion.bias_indicators.map((ind) => (
            <Badge key={ind} variant="warning">
              {ind}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

export function DecisionWorkspacePage() {
  const { decisionId = '' } = useParams<{ decisionId: string }>();
  const queryClient = useQueryClient();
  const addToast = useUiStore((s) => s.addToast);

  // Vote submission state
  const [voteChoice, setVoteChoice] = React.useState<VoteChoice>('accept');
  const [voteConfidence, setVoteConfidence] = React.useState(0.88);
  const [voteJustification, setVoteJustification] = React.useState('');
  const [voteIndicatorsInput, setVoteIndicatorsInput] = React.useState('');

  // Governance action modal state
  const [govActionModal, setGovActionModal] = React.useState<{
    open: boolean;
    action: 'approve' | 'reject' | 'escalate' | 'request_review';
    label: string;
  }>({
    open: false,
    action: 'approve',
    label: 'Approve Decision',
  });
  const [govJustification, setGovJustification] = React.useState('');

  const workspaceQuery = useQuery({
    queryKey: queryKeys.decisions.workspace(decisionId),
    queryFn: () => decisionsService.getDecisionWorkspace(decisionId),
    enabled: Boolean(decisionId),
  });

  const analyzeMutation = useMutation({
    mutationFn: () => decisionsService.runAiAnalysis(decisionId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.decisions.workspace(decisionId),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.decisions.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.system.stats() });
      addToast({
        title: 'AI & ML Fairness Evaluation Complete',
        description:
          'Multi-provider AI synthesis and ML fairness metrics have been updated.',
        variant: 'success',
      });
    },
    onError: (err) => {
      addToast({
        title: 'Evaluation failed',
        description: normalizeApiError(err).message,
        variant: 'error',
      });
    },
  });

  const submitVoteMutation = useMutation({
    mutationFn: (payload: Parameters<typeof decisionsService.submitVote>[0]) =>
      decisionsService.submitVote(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.decisions.workspace(decisionId),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.votes.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.system.stats() });
      setVoteJustification('');
      setVoteIndicatorsInput('');
      addToast({
        title: 'Vote recorded in governance ledger',
        description:
          'Weighted consensus and audit records have been recalculated.',
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

  const governanceActionMutation = useMutation({
    mutationFn: (payload: {
      action: 'approve' | 'reject' | 'escalate' | 'request_review';
      justification: string;
    }) => decisionsService.executeGovernanceAction(decisionId, payload),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.decisions.workspace(decisionId),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.decisions.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.audit.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.system.stats() });
      setGovActionModal((prev) => ({ ...prev, open: false }));
      setGovJustification('');
      addToast({
        title: `Governance action executed: ${updated.status.toUpperCase()}`,
        description: `Decision ${updated.id} status updated with cryptographic audit record.`,
        variant: 'success',
      });
    },
    onError: (err) => {
      addToast({
        title: 'Governance action rejected',
        description: normalizeApiError(err).message,
        variant: 'error',
      });
    },
  });

  const handleVoteSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (voteJustification.trim().length < 5) {
      addToast({
        title: 'Justification required',
        description:
          'Provide at least 5 characters explaining your assessment.',
        variant: 'warning',
      });
      return;
    }
    const indicators = voteIndicatorsInput
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    submitVoteMutation.mutate({
      decision_id: decisionId,
      vote: voteChoice,
      recommendation: voteChoice,
      confidence: voteConfidence,
      justification: voteJustification.trim(),
      bias_indicators: indicators,
    });
  };

  const handleGovernanceActionSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (govJustification.trim().length < 5) {
      addToast({
        title: 'Mandatory audit justification',
        description:
          'Please enter a clear governance justification (minimum 5 characters).',
        variant: 'warning',
      });
      return;
    }
    governanceActionMutation.mutate({
      action: govActionModal.action,
      justification: govJustification.trim(),
    });
  };

  if (workspaceQuery.isLoading) {
    return (
      <div className="space-y-4" data-testid="decision-workspace-loading">
        <h1 className="text-lg font-semibold text-foreground">
          Decision Workspace — {decisionId}
        </h1>
        <LoadingSkeleton cards={4} rows={5} />
      </div>
    );
  }

  if (workspaceQuery.isError || !workspaceQuery.data) {
    return (
      <div className="space-y-4">
        <h1 className="text-lg font-semibold text-foreground">
          Decision Workspace — {decisionId}
        </h1>
        <ErrorState
          title={`Unable to load Decision Workspace (${decisionId})`}
          message={
            workspaceQuery.error
              ? normalizeApiError(workspaceQuery.error).message
              : 'Decision case not found.'
          }
          onRetry={() => workspaceQuery.refetch()}
        />
      </div>
    );
  }

  const {
    decision,
    ai_opinions,
    human_reviews,
    consensus,
    bias_analysis,
    governance_rules,
    audit_trail,
  } = workspaceQuery.data;

  const fairness = bias_analysis.fairness_metrics ?? {};
  const categoryScores = Object.entries(bias_analysis.category_scores ?? {});

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Header */}
      <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <Link
            to="/app/decisions"
            className="inline-flex items-center gap-1 text-muted-foreground hover:text-primary"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Decision Registry
          </Link>
          <span>/</span>
          <span className="font-mono text-foreground">{decision.id}</span>
        </div>
        <h2 className="font-mono text-xs font-medium text-muted-foreground">
          Decision Workspace — {decision.id}
        </h2>
      </div>

      <PageHeader
        title={decision.title}
        description={`Category: ${decision.application_type.replace(
          /_/g,
          ' '
        )} • Created by ${decision.created_by_name} • Last updated ${formatDateTime(
          decision.updated_at
        )}`}
        badge={
          <div className="flex items-center gap-2">
            <Badge variant={statusBadgeVariant(decision.status)}>
              {decision.status.replace(/_/g, ' ').toUpperCase()}
            </Badge>
            <Badge
              variant={
                decision.risk_level === 'high'
                  ? 'destructive'
                  : decision.risk_level === 'medium'
                    ? 'warning'
                    : 'success'
              }
            >
              Risk: {decision.risk_level.toUpperCase()}
            </Badge>
          </div>
        }
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => workspaceQuery.refetch()}
              disabled={workspaceQuery.isFetching}
            >
              <RefreshCw
                className={`mr-1.5 h-3.5 w-3.5 ${
                  workspaceQuery.isFetching ? 'animate-spin' : ''
                }`}
              />
              Refresh Workspace
            </Button>
            <PermissionGate
              permissions={['decisions:update', 'decisions:create']}
            >
              <Button
                size="sm"
                onClick={() => analyzeMutation.mutate()}
                disabled={analyzeMutation.isPending}
              >
                {analyzeMutation.isPending ? (
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Sparkles className="mr-1.5 h-3.5 w-3.5" />
                )}
                Run AI & Fairness Scan
              </Button>
            </PermissionGate>
          </div>
        }
      />

      {/* SECTION 1: Decision Context, Applicant Data & Metadata */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-primary" />
            1. Decision Case Context & Structured Parameters
          </CardTitle>
          <CardDescription>
            Primary case narrative, applicant attributes, and active governance
            assignment.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="rounded-lg border border-border bg-secondary/40 p-4 lg:col-span-2">
              <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Evaluation Context
              </div>
              <p className="mt-2 text-sm leading-relaxed text-foreground">
                {decision.context}
              </p>
              {decision.description &&
                decision.description !== decision.context && (
                  <p className="mt-2 text-xs text-muted-foreground">
                    {decision.description}
                  </p>
                )}
              {decision.human_override && (
                <div className="mt-3 flex items-start gap-2 rounded border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-300">
                  <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
                  <div>
                    <span className="font-semibold">
                      Human Governance Override Recorded:
                    </span>{' '}
                    {decision.override_reason}
                  </div>
                </div>
              )}
            </div>

            <div className="rounded-lg border border-border bg-secondary/40 p-4">
              <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Structured Applicant Context
              </div>
              {decision.applicant_data &&
              Object.keys(decision.applicant_data).length > 0 ? (
                <dl className="mt-2.5 space-y-1.5 text-xs">
                  {Object.entries(decision.applicant_data).map(([key, val]) => (
                    <div
                      key={key}
                      className="flex items-center justify-between border-b border-border/40 pb-1"
                    >
                      <dt className="text-muted-foreground">
                        {key.replace(/_/g, ' ')}
                      </dt>
                      <dd className="font-mono text-foreground">
                        {typeof val === 'object'
                          ? JSON.stringify(val)
                          : String(val)}
                      </dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <p className="mt-2 text-xs text-muted-foreground">
                  No structured applicant attributes attached.
                </p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* SECTION 2: Weighted Consensus Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Scale className="h-4 w-4 text-sky-400" />
            2. Weighted Multi-Agent Consensus Summary
          </CardTitle>
          <CardDescription>{consensus.explanation}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <div className="rounded-lg border border-border bg-secondary/40 p-3">
              <div className="text-[11px] text-muted-foreground">
                Consensus Score
              </div>
              <div className="mt-1 font-mono text-xl font-bold text-foreground">
                {formatPercent(consensus.consensus_score * 100)}
              </div>
              <div className="mt-0.5 text-[11px] capitalize text-sky-400">
                {consensus.consensus_status.replace(/_/g, ' ')}
              </div>
            </div>

            <div className="rounded-lg border border-border bg-secondary/40 p-3">
              <div className="text-[11px] text-muted-foreground">
                Recommended Outcome
              </div>
              <div className="mt-1 font-mono text-lg font-bold uppercase text-foreground">
                {consensus.recommended_outcome}
              </div>
              <div className="mt-0.5 text-[11px] text-muted-foreground">
                Avg Conf: {formatPercent(consensus.average_confidence * 100)}
              </div>
            </div>

            <div className="rounded-lg border border-border bg-secondary/40 p-3">
              <div className="text-[11px] text-muted-foreground">
                Weighted Accept
              </div>
              <div className="mt-1 font-mono text-xl font-bold text-emerald-400">
                {consensus.weighted_accept_score.toFixed(2)}
              </div>
              <div className="mt-0.5 text-[11px] text-muted-foreground">
                {consensus.accept_votes} accept vote(s)
              </div>
            </div>

            <div className="rounded-lg border border-border bg-secondary/40 p-3">
              <div className="text-[11px] text-muted-foreground">
                Weighted Reject
              </div>
              <div className="mt-1 font-mono text-xl font-bold text-red-400">
                {consensus.weighted_reject_score.toFixed(2)}
              </div>
              <div className="mt-0.5 text-[11px] text-muted-foreground">
                {consensus.reject_votes} reject vote(s)
              </div>
            </div>

            <div className="rounded-lg border border-border bg-secondary/40 p-3">
              <div className="text-[11px] text-muted-foreground">
                AI Agent Consensus
              </div>
              <div className="mt-1 font-mono text-xl font-bold text-primary">
                {formatPercent(consensus.ai_consensus_rate * 100)}
              </div>
              <div className="mt-0.5 text-[11px] text-muted-foreground">
                {ai_opinions.length} AI evaluators
              </div>
            </div>

            <div className="rounded-lg border border-border bg-secondary/40 p-3">
              <div className="text-[11px] text-muted-foreground">
                Human Reviewer Consensus
              </div>
              <div className="mt-1 font-mono text-xl font-bold text-sky-400">
                {formatPercent(consensus.human_consensus_rate * 100)}
              </div>
              <div className="mt-0.5 text-[11px] text-muted-foreground">
                {human_reviews.length} human reviewers
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* SECTION 3 & SECTION 4: AI Agent Opinions & Human Reviewer Assessments */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bot className="h-4 w-4 text-primary" />
              3. AI Agent Opinions ({ai_opinions.length})
            </CardTitle>
            <CardDescription>
              Autonomous model evaluations, confidence thresholds, and
              justification traces.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {ai_opinions.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No AI agents assigned to this decision.
              </p>
            ) : (
              ai_opinions.map((op) => (
                <OpinionCard key={op.agent_id} opinion={op} />
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserCheck className="h-4 w-4 text-sky-400" />
              4. Human Reviewer Assessments ({human_reviews.length})
            </CardTitle>
            <CardDescription>
              Human domain oversight, ethical review notes, and interactive vote
              submission.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              {human_reviews.length === 0 ? (
                <p className="text-xs text-muted-foreground">
                  No human reviewers have recorded assessments yet.
                </p>
              ) : (
                human_reviews.map((op) => (
                  <OpinionCard key={op.agent_id} opinion={op} />
                ))
              )}
            </div>

            {/* Interactive Vote Submission Form */}
            <PermissionGate permissions={['voting:participate']}>
              <form
                onSubmit={handleVoteSubmit}
                className="space-y-3 rounded-lg border border-sky-500/30 bg-secondary/40 p-4"
              >
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                    <Vote className="h-4 w-4 text-sky-400" />
                    Submit Human Co-Governance Vote
                  </span>
                  <Badge variant="info">Live Ledger</Badge>
                </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div className="space-y-1">
                    <Label htmlFor="vote-choice" className="text-xs">
                      Vote Position
                    </Label>
                    <select
                      id="vote-choice"
                      value={voteChoice}
                      onChange={(e) =>
                        setVoteChoice(e.target.value as VoteChoice)
                      }
                      className="h-9 w-full rounded-md border border-border bg-secondary/60 px-3 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    >
                      <option value="accept">Accept / Recommend Approval</option>
                      <option value="reject">Reject / Flag Violation</option>
                      <option value="abstain">
                        Abstain / Request Escalation
                      </option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <Label htmlFor="vote-confidence" className="text-xs">
                      Confidence ({Math.round(voteConfidence * 100)}%)
                    </Label>
                    <Input
                      id="vote-confidence"
                      type="number"
                      step="0.01"
                      min="0.1"
                      max="1"
                      value={voteConfidence}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                        setVoteConfidence(
                          Math.min(1, Math.max(0.1, Number(e.target.value)))
                        )
                      }
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <Label htmlFor="vote-justification" className="text-xs">
                    Assessment Justification
                  </Label>
                  <Textarea
                    id="vote-justification"
                    rows={2}
                    placeholder="Provide domain reasoning for audit explainability..."
                    value={voteJustification}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                      setVoteJustification(e.target.value)
                    }
                  />
                </div>

                <div className="space-y-1">
                  <Label htmlFor="vote-indicators" className="text-xs">
                    Observed Bias Indicators (comma-separated, optional)
                  </Label>
                  <Input
                    id="vote-indicators"
                    placeholder="e.g., age_proxy, regional_disparity"
                    value={voteIndicatorsInput}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      setVoteIndicatorsInput(e.target.value)
                    }
                  />
                </div>

                <div className="flex justify-end">
                  <Button
                    type="submit"
                    size="sm"
                    disabled={submitVoteMutation.isPending}
                  >
                    {submitVoteMutation.isPending && (
                      <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    )}
                    Record Assessment Vote
                  </Button>
                </div>
              </form>
            </PermissionGate>
          </CardContent>
        </Card>
      </div>

      {/* SECTION 5 & SECTION 6: ML Bias & Fairness Analysis + Governance Rules */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-400" />
              5. ML Bias & Fairness Analysis
            </CardTitle>
            <CardDescription>
              Isolation Forest & Random Forest fairness diagnostics across
              protected categories.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-lg border border-border bg-secondary/40 p-3">
                <div className="text-[11px] text-muted-foreground">
                  Overall Bias Score
                </div>
                <div className="mt-1 font-mono text-lg font-bold text-foreground">
                  {(
                    (bias_analysis.overall_bias_score ?? decision.bias_score) *
                    100
                  ).toFixed(1)}
                  %
                </div>
              </div>
              <div className="rounded-lg border border-border bg-secondary/40 p-3">
                <div className="text-[11px] text-muted-foreground">
                  Demographic Parity
                </div>
                <div className="mt-1 font-mono text-lg font-bold text-sky-400">
                  {formatPercent((fairness.demographic_parity ?? 0.91) * 100)}
                </div>
              </div>
              <div className="rounded-lg border border-border bg-secondary/40 p-3">
                <div className="text-[11px] text-muted-foreground">
                  Equal Opportunity
                </div>
                <div className="mt-1 font-mono text-lg font-bold text-primary">
                  {formatPercent((fairness.equal_opportunity ?? 0.89) * 100)}
                </div>
              </div>
              <div className="rounded-lg border border-border bg-secondary/40 p-3">
                <div className="text-[11px] text-muted-foreground">
                  Equalized Odds
                </div>
                <div className="mt-1 font-mono text-lg font-bold text-foreground">
                  {formatPercent((fairness.equalized_odds ?? 0.88) * 100)}
                </div>
              </div>
            </div>

            {categoryScores.length > 0 && (
              <div className="space-y-2">
                <div className="text-xs font-semibold text-muted-foreground">
                  Protected Category Sensitivity Breakdown
                </div>
                <div className="space-y-2">
                  {categoryScores.map(([cat, score]) => {
                    const pct = Math.min(100, Math.round(Number(score) * 100));
                    return (
                      <div key={cat} className="space-y-1">
                        <div className="flex justify-between text-xs">
                          <span className="capitalize text-muted-foreground">
                            {cat.replace(/_/g, ' ')}
                          </span>
                          <span className="font-mono text-foreground">
                            {pct}%
                          </span>
                        </div>
                        <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
                          <div
                            className={`h-full rounded-full ${
                              pct >= 50
                                ? 'bg-red-500'
                                : pct >= 30
                                  ? 'bg-amber-500'
                                  : 'bg-sky-400'
                            }`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {bias_analysis.recommendations &&
              bias_analysis.recommendations.length > 0 && (
                <div className="rounded-lg border border-border bg-secondary/40 p-3">
                  <div className="text-xs font-semibold text-foreground">
                    Fairness Engine Recommendations
                  </div>
                  <ul className="mt-1.5 list-disc space-y-1 pl-4 text-xs text-muted-foreground">
                    {bias_analysis.recommendations.map((rec, idx) => (
                      <li key={idx}>{rec}</li>
                    ))}
                  </ul>
                </div>
              )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileCode2 className="h-4 w-4 text-primary" />
              6. Applicable Governance Policies ({governance_rules.length})
            </CardTitle>
            <CardDescription>
              Active YAML policy rules and mandatory approval thresholds
              enforced on this category.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {governance_rules.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No active governance policies matched this decision context.
              </p>
            ) : (
              governance_rules.map((rule) => (
                <div
                  key={rule.id}
                  className="space-y-2 rounded-lg border border-border bg-secondary/40 p-3.5"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <div className="text-xs font-semibold text-foreground">
                        {rule.name}
                      </div>
                      <div className="text-[11px] text-muted-foreground">
                        {rule.description}
                      </div>
                    </div>
                    <Badge variant="default">
                      Threshold: {formatPercent(rule.approval_threshold * 100)}
                    </Badge>
                  </div>
                  <pre className="max-h-32 overflow-x-auto rounded border border-border/60 bg-background p-2.5 font-mono text-[11px] text-muted-foreground">
                    {rule.rule_definition}
                  </pre>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      {/* SECTION 7: Governance Action Controls & Cryptographic Audit Trail */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Gavel className="h-4 w-4 text-sky-400" />
                7. Governance Resolution Controls & Cryptographic Audit Trail
              </CardTitle>
              <CardDescription>
                Execute role-authorized governance actions and inspect SHA-256
                tamper-evident audit entries.
              </CardDescription>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <PermissionGate permissions={['decisions:approve']}>
                <Button
                  size="sm"
                  onClick={() =>
                    setGovActionModal({
                      open: true,
                      action: 'approve',
                      label: 'Approve Decision Case',
                    })
                  }
                  className="bg-emerald-600 text-white hover:bg-emerald-500"
                >
                  <CheckCircle2 className="mr-1.5 h-4 w-4" />
                  Approve
                </Button>
              </PermissionGate>

              <PermissionGate permissions={['decisions:reject']}>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() =>
                    setGovActionModal({
                      open: true,
                      action: 'reject',
                      label: 'Reject Decision Case',
                    })
                  }
                >
                  <XCircle className="mr-1.5 h-4 w-4" />
                  Reject
                </Button>
              </PermissionGate>

              <PermissionGate permissions={['decisions:escalate']}>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() =>
                    setGovActionModal({
                      open: true,
                      action: 'escalate',
                      label: 'Escalate to Ethics Committee',
                    })
                  }
                >
                  <ShieldAlert className="mr-1.5 h-4 w-4 text-amber-400" />
                  Escalate
                </Button>
              </PermissionGate>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2.5">
            {audit_trail.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No audit events recorded for this decision yet.
              </p>
            ) : (
              audit_trail.map((entry) => (
                <div
                  key={entry.id}
                  className="flex flex-col justify-between gap-2 rounded-lg border border-border bg-secondary/40 p-3 text-xs sm:flex-row sm:items-center"
                >
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge
                        variant={
                          entry.compliance_status === 'compliant'
                            ? 'success'
                            : entry.compliance_status === 'non_compliant'
                              ? 'destructive'
                              : 'warning'
                        }
                      >
                        {entry.compliance_status.replace(/_/g, ' ')}
                      </Badge>
                      <span className="font-semibold text-foreground">
                        {entry.event_type.replace(/_/g, ' ').toUpperCase()}
                      </span>
                      <span className="text-muted-foreground">
                        by {entry.actor_name} ({entry.actor_type})
                      </span>
                    </div>
                    <p className="text-muted-foreground">{entry.action}</p>
                  </div>

                  <div className="text-right font-mono text-[11px] text-muted-foreground">
                    <div>{formatDateTime(entry.timestamp)}</div>
                    <div className="inline-flex items-center gap-1 text-sky-400">
                      <ShieldCheck className="h-3 w-3" />
                      SHA256: {entry.audit_hash.slice(0, 14)}...
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Governance Action Confirmation Modal */}
      <Dialog
        open={govActionModal.open}
        onOpenChange={(open) =>
          setGovActionModal((prev) => ({ ...prev, open }))
        }
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{govActionModal.label}</DialogTitle>
            <DialogDescription>
              This action updates the official status of{' '}
              <span className="font-mono text-foreground">{decision.id}</span>{' '}
              and records a permanent cryptographic entry in the governance
              audit ledger.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleGovernanceActionSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="gov-action-justification">
                Mandatory Governance Justification
              </Label>
              <Textarea
                id="gov-action-justification"
                rows={4}
                placeholder="State the policy basis, fairness review findings, or override rationale..."
                value={govJustification}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                  setGovJustification(e.target.value)
                }
              />
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="ghost"
                onClick={() =>
                  setGovActionModal((prev) => ({ ...prev, open: false }))
                }
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={governanceActionMutation.isPending}
              >
                {governanceActionMutation.isPending && (
                  <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                )}
                Confirm & Sign Audit Record
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
