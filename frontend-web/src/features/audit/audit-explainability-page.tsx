import * as React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ChevronLeft,
  ChevronRight,
  FileSearch,
  RefreshCw,
  Search,
  ShieldCheck,
} from 'lucide-react';
import { queryKeys } from '@/app/query-client';
import { platformServices } from '@/services/platform-services';
import { PageHeader } from '@/components/common/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { EmptyState } from '@/components/feedback/empty-state';
import { ErrorState } from '@/components/feedback/error-state';
import { LoadingSkeleton } from '@/components/feedback/loading-skeleton';
import { normalizeApiError } from '@/services/api-error';
import { formatDateTime } from '@/lib/utils';

export function AuditExplainabilityPage() {
  const [search, setSearch] = React.useState('');
  const [complianceFilter, setComplianceFilter] = React.useState('');
  const [actorFilter, setActorFilter] = React.useState('');
  const [page, setPage] = React.useState(1);
  const pageSize = 20;

  const params = React.useMemo(
    () => ({
      search: search.trim() || undefined,
      compliance_status: complianceFilter || undefined,
      actor_type: actorFilter || undefined,
      page,
      page_size: pageSize,
    }),
    [search, complianceFilter, actorFilter, page]
  );

  const auditQuery = useQuery({
    queryKey: queryKeys.audit.list(params),
    queryFn: () => platformServices.listAuditLogs(params),
  });

  return (
    <div className="space-y-6" data-testid="audit-explainability-page">
      <PageHeader
        title="Cryptographic Audit Ledger & Explainability"
        description="Immutable SHA-256 governance audit records tracking every decision evaluation, multi-agent vote, policy rule application, and human override."
        badge={
          <Badge variant="default">
            {auditQuery.data?.total ?? 0} Audit Entries
          </Badge>
        }
        actions={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => auditQuery.refetch()}
          >
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            Refresh Ledger
          </Button>
        }
      />

      {/* Filter Bar */}
      <Card>
        <CardContent className="grid grid-cols-1 gap-3 p-4 md:grid-cols-4">
          <div className="relative md:col-span-2">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Search action description, actor name, event type, or SHA-256 hash..."
              className="pl-9"
              aria-label="Search audit ledger"
            />
          </div>

          <select
            aria-label="Filter by compliance status"
            value={complianceFilter}
            onChange={(e) => {
              setComplianceFilter(e.target.value);
              setPage(1);
            }}
            className="h-9 rounded-md border border-border bg-secondary/40 px-3 text-xs text-foreground"
          >
            <option value="">All Compliance States</option>
            <option value="compliant">Compliant</option>
            <option value="under_review">Under Review</option>
            <option value="non_compliant">Non-Compliant</option>
          </select>

          <select
            aria-label="Filter by actor type"
            value={actorFilter}
            onChange={(e) => {
              setActorFilter(e.target.value);
              setPage(1);
            }}
            className="h-9 rounded-md border border-border bg-secondary/40 px-3 text-xs text-foreground"
          >
            <option value="">All Actor Types</option>
            <option value="user">Human Operator</option>
            <option value="human">Human Reviewer Agent</option>
            <option value="ai">AI Evaluator Agent</option>
            <option value="system">System Governance Engine</option>
          </select>
        </CardContent>
      </Card>

      {auditQuery.isLoading ? (
        <LoadingSkeleton cards={2} rows={6} />
      ) : auditQuery.isError ? (
        <ErrorState
          title="Unable to load cryptographic audit ledger"
          message={normalizeApiError(auditQuery.error).message}
          onRetry={() => auditQuery.refetch()}
        />
      ) : !auditQuery.data || auditQuery.data.items.length === 0 ? (
        <EmptyState
          icon={FileSearch}
          title="No matching audit records"
          description="Try clearing search or compliance filters."
        />
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-muted-foreground">
                  <th className="px-4 py-3 font-medium">Event & Actor</th>
                  <th className="px-4 py-3 font-medium">
                    Explainability Action Trace
                  </th>
                  <th className="px-4 py-3 font-medium">Decision Context</th>
                  <th className="px-4 py-3 font-medium">Compliance</th>
                  <th className="px-4 py-3 font-medium">SHA-256 Hash</th>
                  <th className="px-4 py-3 font-medium">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {auditQuery.data.items.map((entry) => (
                  <tr key={entry.id} className="hover:bg-muted/20">
                    <td className="px-4 py-3">
                      <div className="font-semibold text-foreground">
                        {entry.event_type.replace(/_/g, ' ').toUpperCase()}
                      </div>
                      <div className="text-[11px] text-muted-foreground">
                        {entry.actor_name} ({entry.actor_type})
                      </div>
                    </td>
                    <td className="max-w-md px-4 py-3 text-muted-foreground">
                      <div>{entry.action}</div>
                      {entry.rules_applied.length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {entry.rules_applied.map((r) => (
                            <Badge key={r} variant="outline">
                              Rule: {r}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {entry.decision_id ? (
                        <Link
                          to={`/app/decisions/${entry.decision_id}`}
                          className="font-mono text-primary hover:underline"
                        >
                          {entry.decision_title ??
                            entry.decision_id.slice(0, 12)}
                        </Link>
                      ) : (
                        <span className="text-muted-foreground">
                          Platform-level
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
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
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px] text-sky-400">
                      <span className="inline-flex items-center gap-1">
                        <ShieldCheck className="h-3.5 w-3.5" />
                        {entry.audit_hash.slice(0, 16)}…
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {formatDateTime(entry.timestamp)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between border-t border-border px-4 py-3 text-xs text-muted-foreground">
            <div>
              Page{' '}
              <span className="font-mono text-foreground">
                {auditQuery.data.page}
              </span>{' '}
              of{' '}
              <span className="font-mono text-foreground">
                {auditQuery.data.total_pages}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft className="mr-1 h-3.5 w-3.5" />
                Prev
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={page >= auditQuery.data.total_pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
                <ChevronRight className="ml-1 h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}

