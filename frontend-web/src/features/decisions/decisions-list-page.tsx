import * as React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  AlertTriangle,
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  FileCheck2,
  Filter,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  ShieldAlert,
  Trash2,
  Users,
} from 'lucide-react';
import { queryKeys } from '@/app/query-client';
import { decisionsService } from '@/services/decisions-service';
import { PermissionGate } from '@/components/navigation/permission-guard';
import { PageHeader } from '@/components/common/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
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
import { EmptyState } from '@/components/feedback/empty-state';
import { ErrorState } from '@/components/feedback/error-state';
import { LoadingSkeleton } from '@/components/feedback/loading-skeleton';
import { useAuthStore } from '@/stores/auth-store';
import { useUiStore } from '@/stores/ui-store';
import { normalizeApiError } from '@/services/api-error';
import { formatDateTime, formatPercent } from '@/lib/utils';
import type {
  DecisionStatus,
  PriorityLevel,
  RiskLevel,
} from '@/types/governance';

const createDecisionSchema = z.object({
  title: z
    .string()
    .min(3, 'Decision title must be at least 3 characters')
    .max(255, 'Decision title cannot exceed 255 characters'),
  application_type: z.enum([
    'loan_approval',
    'medical_diagnosis',
    'hiring_assessment',
    'content_moderation',
    'financial_trading',
    'general',
  ]),
  priority: z.enum(['low', 'medium', 'high', 'critical']),
  context: z
    .string()
    .min(10, 'Decision context must be at least 10 characters'),
  description: z.string().optional(),
  applicant_json: z.string().optional(),
});

type CreateDecisionFormValues = z.infer<typeof createDecisionSchema>;

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

function riskBadgeVariant(risk: RiskLevel) {
  switch (risk) {
    case 'high':
      return 'destructive' as const;
    case 'medium':
      return 'warning' as const;
    default:
      return 'success' as const;
  }
}

function priorityBadgeVariant(priority: PriorityLevel) {
  switch (priority) {
    case 'critical':
      return 'destructive' as const;
    case 'high':
      return 'warning' as const;
    case 'medium':
      return 'info' as const;
    default:
      return 'outline' as const;
  }
}

export function DecisionsListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const addToast = useUiStore((s) => s.addToast);
  const hasRole = useAuthStore((s) => s.hasRole);
  const canDeleteDecision = hasRole('SUPER_ADMIN') || hasRole('ADMIN');

  const [search, setSearch] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState('');
  const [categoryFilter, setCategoryFilter] = React.useState('');
  const [riskFilter, setRiskFilter] = React.useState('');
  const [priorityFilter, setPriorityFilter] = React.useState('');
  const [sortBy, setSortBy] = React.useState('updated_at');
  const [sortOrder, setSortOrder] = React.useState<'asc' | 'desc'>('desc');
  const [page, setPage] = React.useState(1);
  const pageSize = 15;

  const [createDialogOpen, setCreateDialogOpen] = React.useState(false);
  const [jsonParseError, setJsonParseError] = React.useState<string | null>(
    null
  );

  const filterParams = React.useMemo(
    () => ({
      search: search.trim() || undefined,
      status: statusFilter || undefined,
      application_type: categoryFilter || undefined,
      risk_level: riskFilter || undefined,
      priority: priorityFilter || undefined,
      sort_by: sortBy,
      sort_order: sortOrder,
      page,
      page_size: pageSize,
    }),
    [
      search,
      statusFilter,
      categoryFilter,
      riskFilter,
      priorityFilter,
      sortBy,
      sortOrder,
      page,
    ]
  );

  const decisionsQuery = useQuery({
    queryKey: queryKeys.decisions.list(filterParams),
    queryFn: () => decisionsService.listDecisions(filterParams),
  });

  const form = useForm<CreateDecisionFormValues>({
    resolver: zodResolver(createDecisionSchema),
    defaultValues: {
      title: '',
      application_type: 'loan_approval',
      priority: 'medium',
      context: '',
      description: '',
      applicant_json:
        '{\n  "applicant_tier": "enterprise",\n  "requested_amount": 250000\n}',
    },
  });

  const createDecisionMutation = useMutation({
    mutationFn: (payload: Parameters<typeof decisionsService.createDecision>[0]) =>
      decisionsService.createDecision(payload),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.decisions.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.system.stats() });
      addToast({
        title: 'Decision created',
        description: `Created "${created.title}" (${created.id}) and assigned active governance agents.`,
        variant: 'success',
      });
      setCreateDialogOpen(false);
      form.reset();
      navigate(`/app/decisions/${created.id}`);
    },
    onError: (err) => {
      const apiErr = normalizeApiError(err);
      addToast({
        title: 'Failed to create decision',
        description: apiErr.message,
        variant: 'error',
      });
    },
  });

  const deleteDecisionMutation = useMutation({
    mutationFn: (id: string) => decisionsService.deleteDecision(id),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.decisions.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.system.stats() });
      addToast({
        title: 'Decision deleted',
        description: res.message,
        variant: 'info',
      });
    },
    onError: (err) => {
      const apiErr = normalizeApiError(err);
      addToast({
        title: 'Failed to delete decision',
        description: apiErr.message,
        variant: 'error',
      });
    },
  });

  const handleCreateSubmit = form.handleSubmit((values) => {
    setJsonParseError(null);
    let parsedApplicantData: Record<string, unknown> = {};
    if (values.applicant_json && values.applicant_json.trim()) {
      try {
        const parsed = JSON.parse(values.applicant_json);
        if (
          typeof parsed === 'object' &&
          parsed !== null &&
          !Array.isArray(parsed)
        ) {
          parsedApplicantData = parsed as Record<string, unknown>;
        } else {
          setJsonParseError('Applicant data must be a valid JSON object.');
          return;
        }
      } catch {
        setJsonParseError('Invalid JSON syntax in applicant context.');
        return;
      }
    }

    createDecisionMutation.mutate({
      title: values.title,
      application_type: values.application_type,
      priority: values.priority,
      context: values.context,
      description: values.description || values.context,
      applicant_data: parsedApplicantData,
    });
  });

  const resetFilters = () => {
    setSearch('');
    setStatusFilter('');
    setCategoryFilter('');
    setRiskFilter('');
    setPriorityFilter('');
    setSortBy('updated_at');
    setSortOrder('desc');
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Decision Registry & Governance Queue"
        description="Evaluate high-stakes human-AI decisions, inspect multi-agent consensus, monitor ML fairness thresholds, and execute auditable governance actions."
        badge={
          <Badge variant="default">
            {decisionsQuery.data?.total ?? 0} Registered Decisions
          </Badge>
        }
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => decisionsQuery.refetch()}
              disabled={decisionsQuery.isFetching}
            >
              <RefreshCw
                className={`mr-1.5 h-3.5 w-3.5 ${
                  decisionsQuery.isFetching ? 'animate-spin' : ''
                }`}
              />
              Refresh
            </Button>
            <PermissionGate permissions={['decisions:create']}>
              <Button size="sm" onClick={() => setCreateDialogOpen(true)}>
                <Plus className="mr-1.5 h-4 w-4" />
                New Decision
              </Button>
            </PermissionGate>
          </div>
        }
      />

      {/* Search & Multi-Facet Filter Bar */}
      <Card>
        <CardContent className="p-4">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-6">
            <div className="relative lg:col-span-2">
              <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                placeholder="Search by ID, title, context, or category..."
                className="pl-9"
                aria-label="Search decisions"
              />
            </div>

            <select
              aria-label="Filter by status"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="h-9 rounded-md border border-border bg-secondary/40 px-3 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="under_review">Under Review</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="escalated">Escalated</option>
            </select>

            <select
              aria-label="Filter by category"
              value={categoryFilter}
              onChange={(e) => {
                setCategoryFilter(e.target.value);
                setPage(1);
              }}
              className="h-9 rounded-md border border-border bg-secondary/40 px-3 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">All Categories</option>
              <option value="loan_approval">Loan Approval</option>
              <option value="medical_diagnosis">Medical Diagnosis</option>
              <option value="hiring_assessment">Hiring Assessment</option>
              <option value="content_moderation">Content Moderation</option>
              <option value="financial_trading">Financial Trading</option>
              <option value="general">General</option>
            </select>

            <select
              aria-label="Filter by risk level"
              value={riskFilter}
              onChange={(e) => {
                setRiskFilter(e.target.value);
                setPage(1);
              }}
              className="h-9 rounded-md border border-border bg-secondary/40 px-3 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">All Risk Levels</option>
              <option value="low">Low Risk</option>
              <option value="medium">Medium Risk</option>
              <option value="high">High Risk</option>
            </select>

            <div className="flex items-center gap-2">
              <select
                aria-label="Sort decisions by"
                value={`${sortBy}:${sortOrder}`}
                onChange={(e) => {
                  const [field, order] = e.target.value.split(':');
                  setSortBy(field);
                  setSortOrder(order as 'asc' | 'desc');
                  setPage(1);
                }}
                className="h-9 flex-1 rounded-md border border-border bg-secondary/40 px-2.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="updated_at:desc">Updated (Newest)</option>
                <option value="created_at:desc">Created (Newest)</option>
                <option value="bias_score:desc">Bias Risk (Highest)</option>
                <option value="priority:desc">Priority (Highest)</option>
                <option value="status:asc">Status (A-Z)</option>
              </select>
              {(search ||
                statusFilter ||
                categoryFilter ||
                riskFilter ||
                priorityFilter) && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={resetFilters}
                  title="Clear filters"
                >
                  <Filter className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Decisions Table */}
      {decisionsQuery.isLoading ? (
        <LoadingSkeleton rows={6} />
      ) : decisionsQuery.isError ? (
        <ErrorState
          title="Unable to load decisions registry"
          message={normalizeApiError(decisionsQuery.error).message}
          onRetry={() => decisionsQuery.refetch()}
        />
      ) : !decisionsQuery.data || decisionsQuery.data.items.length === 0 ? (
        <EmptyState
          icon={FileCheck2}
          title="No governance decisions match your filters"
          description="Try clearing active search filters or submit a new decision case for multi-agent evaluation."
          action={
            <PermissionGate permissions={['decisions:create']}>
              <Button size="sm" onClick={() => setCreateDialogOpen(true)}>
                <Plus className="mr-1.5 h-4 w-4" />
                Create Decision Case
              </Button>
            </PermissionGate>
          }
        />
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-muted-foreground">
                  <th className="px-4 py-3 font-medium">Decision Case</th>
                  <th className="px-4 py-3 font-medium">Category</th>
                  <th className="px-4 py-3 font-medium">Priority</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Consensus</th>
                  <th className="px-4 py-3 font-medium">Bias & Risk</th>
                  <th className="px-4 py-3 font-medium">Agents / Votes</th>
                  <th className="px-4 py-3 font-medium">Updated</th>
                  <th className="px-4 py-3 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {decisionsQuery.data.items.map((dec) => (
                  <tr
                    key={dec.id}
                    className="transition-colors hover:bg-muted/30"
                  >
                    <td className="px-4 py-3.5">
                      <Link
                        to={`/app/decisions/${dec.id}`}
                        className="font-medium text-foreground hover:text-primary"
                      >
                        {dec.title}
                      </Link>
                      <div className="mt-0.5 flex items-center gap-2 font-mono text-[11px] text-muted-foreground">
                        <span>{dec.id}</span>
                        {dec.human_override && (
                          <span className="inline-flex items-center gap-1 text-amber-400">
                            <ShieldAlert className="h-3 w-3" /> Override
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3.5 capitalize text-muted-foreground">
                      {dec.application_type.replace(/_/g, ' ')}
                    </td>
                    <td className="px-4 py-3.5">
                      <Badge variant={priorityBadgeVariant(dec.priority)}>
                        {dec.priority}
                      </Badge>
                    </td>
                    <td className="px-4 py-3.5">
                      <Badge variant={statusBadgeVariant(dec.status)}>
                        {dec.status.replace(/_/g, ' ')}
                      </Badge>
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="font-mono text-foreground">
                        {formatPercent(dec.consensus_score * 100)}
                      </div>
                      <div className="text-[11px] capitalize text-muted-foreground">
                        {dec.consensus_status.replace(/_/g, ' ')}
                      </div>
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-foreground">
                          {(dec.bias_score * 100).toFixed(1)}%
                        </span>
                        <Badge variant={riskBadgeVariant(dec.risk_level)}>
                          {dec.risk_level}
                        </Badge>
                      </div>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="inline-flex items-center gap-1 font-mono text-muted-foreground">
                        <Users className="h-3.5 w-3.5 text-muted-foreground" />
                        {dec.vote_count}/{dec.participant_count}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-muted-foreground">
                      {formatDateTime(dec.updated_at)}
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      <div className="inline-flex items-center gap-1.5">
                        <Button asChild variant="secondary" size="sm">
                          <Link to={`/app/decisions/${dec.id}`}>
                            Workspace
                            <ArrowUpRight className="ml-1 h-3.5 w-3.5" />
                          </Link>
                        </Button>
                        {canDeleteDecision && (
                          <Button
                            variant="ghost"
                            size="sm"
                            aria-label={`Delete ${dec.title}`}
                            disabled={deleteDecisionMutation.isPending}
                            onClick={() =>
                              deleteDecisionMutation.mutate(dec.id)
                            }
                            className="text-red-400 hover:bg-red-500/10 hover:text-red-300"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div className="flex items-center justify-between border-t border-border px-4 py-3 text-xs text-muted-foreground">
            <div>
              Showing page{' '}
              <span className="font-mono text-foreground">
                {decisionsQuery.data.page}
              </span>{' '}
              of{' '}
              <span className="font-mono text-foreground">
                {decisionsQuery.data.total_pages}
              </span>{' '}
              ({decisionsQuery.data.total} total decisions)
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft className="mr-1 h-3.5 w-3.5" />
                Previous
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={page >= decisionsQuery.data.total_pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
                <ChevronRight className="ml-1 h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Create Decision Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Create Governance Decision Case</DialogTitle>
            <DialogDescription>
              Submit a new decision case for multi-agent AI evaluation, ML
              fairness scanning, and human co-governance review.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreateSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="decision-title">Decision Title</Label>
              <Input
                id="decision-title"
                placeholder="e.g., Commercial Credit Line — Horizon Logistics"
                {...form.register('title')}
              />
              {form.formState.errors.title && (
                <p className="text-xs text-red-400">
                  {form.formState.errors.title.message}
                </p>
              )}
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="decision-category">Domain Category</Label>
                <select
                  id="decision-category"
                  {...form.register('application_type')}
                  className="h-9 w-full rounded-md border border-border bg-secondary/40 px-3 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="loan_approval">Loan Approval</option>
                  <option value="medical_diagnosis">Medical Diagnosis</option>
                  <option value="hiring_assessment">Hiring Assessment</option>
                  <option value="content_moderation">Content Moderation</option>
                  <option value="financial_trading">Financial Trading</option>
                  <option value="general">General</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="decision-priority">Governance Priority</Label>
                <select
                  id="decision-priority"
                  {...form.register('priority')}
                  className="h-9 w-full rounded-md border border-border bg-secondary/40 px-3 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="decision-context">
                Case Context & Evaluation Prompt
              </Label>
              <Textarea
                id="decision-context"
                rows={4}
                placeholder="Describe the applicant profile, financial/clinical/operational parameters, and potential fairness considerations..."
                {...form.register('context')}
              />
              {form.formState.errors.context && (
                <p className="text-xs text-red-400">
                  {form.formState.errors.context.message}
                </p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="decision-applicant-json">
                Structured Applicant Context (JSON)
              </Label>
              <Textarea
                id="decision-applicant-json"
                rows={3}
                className="font-mono text-xs"
                {...form.register('applicant_json')}
              />
              {jsonParseError && (
                <p className="flex items-center gap-1 text-xs text-red-400">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  {jsonParseError}
                </p>
              )}
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="ghost"
                onClick={() => setCreateDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={createDecisionMutation.isPending}
              >
                {createDecisionMutation.isPending && (
                  <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                )}
                Register & Run Evaluation
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
