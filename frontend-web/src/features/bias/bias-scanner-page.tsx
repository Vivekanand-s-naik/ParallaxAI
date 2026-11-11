import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  ArrowUpRight,
  Loader2,
  RefreshCw,
  Scale,
  ShieldAlert,
  Sparkles,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { queryKeys } from '@/app/query-client';
import { platformServices } from '@/services/platform-services';
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
import { ErrorState } from '@/components/feedback/error-state';
import { LoadingSkeleton } from '@/components/feedback/loading-skeleton';
import { useUiStore } from '@/stores/ui-store';
import { normalizeApiError } from '@/services/api-error';
import { formatPercent } from '@/lib/utils';

export function BiasScannerPage() {
  const queryClient = useQueryClient();
  const addToast = useUiStore((s) => s.addToast);

  const overviewQuery = useQuery({
    queryKey: queryKeys.bias.overview(),
    queryFn: () => platformServices.getBiasOverview(),
  });

  const triggerReviewMutation = useMutation({
    mutationFn: (
      payload: Parameters<typeof platformServices.triggerBiasHumanReview>[0]
    ) => platformServices.triggerBiasHumanReview(payload),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.bias.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.decisions.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.system.stats() });
      addToast({
        title: 'Human Fairness Review Triggered',
        description: res.message,
        variant: 'warning',
      });
    },
    onError: (err) => {
      addToast({
        title: 'Failed to trigger review',
        description: normalizeApiError(err).message,
        variant: 'error',
      });
    },
  });

  const rescanMutation = useMutation({
    mutationFn: (decisionId: string) =>
      platformServices.analyzeDecisionBias(decisionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.bias.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.decisions.all });
      addToast({
        title: 'ML Bias Rescan Complete',
        description:
          'Updated IsolationForest and RandomForest fairness scores.',
        variant: 'success',
      });
    },
    onError: (err) => {
      addToast({
        title: 'Rescan failed',
        description: normalizeApiError(err).message,
        variant: 'error',
      });
    },
  });

  if (overviewQuery.isLoading) {
    return <LoadingSkeleton cards={4} rows={5} />;
  }

  if (overviewQuery.isError || !overviewQuery.data) {
    return (
      <ErrorState
        title="Unable to load Bias & Fairness Scanner"
        message={
          overviewQuery.error
            ? normalizeApiError(overviewQuery.error).message
            : 'Fairness telemetry unavailable.'
        }
        onRetry={() => overviewQuery.refetch()}
      />
    );
  }

  const { summary, fairness_metrics, category_breakdown, flagged_decisions } =
    overviewQuery.data;

  return (
    <div className="space-y-6" data-testid="bias-scanner-page">
      <PageHeader
        title="ML Bias & Fairness Scanner"
        description="Continuous IsolationForest anomaly detection and RandomForest protected-category sensitivity monitoring across all governance decisions."
        badge={
          <Badge variant={summary.ml_models_trained ? 'success' : 'warning'}>
            {summary.ml_models_trained
              ? 'ML Models Active'
              : 'Rule-Based Fallback'}
          </Badge>
        }
        actions={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => overviewQuery.refetch()}
          >
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            Refresh Diagnostics
          </Button>
        }
      />

      {/* Fairness Metrics Row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">
              Demographic Parity
            </div>
            <div className="mt-1 font-mono text-2xl font-bold text-sky-400">
              {formatPercent(fairness_metrics.demographic_parity * 100)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">
              Equal Opportunity
            </div>
            <div className="mt-1 font-mono text-2xl font-bold text-primary">
              {formatPercent(fairness_metrics.equal_opportunity * 100)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">Equalized Odds</div>
            <div className="mt-1 font-mono text-2xl font-bold text-foreground">
              {formatPercent(fairness_metrics.equalized_odds * 100)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">
              High Bias / Anomalies
            </div>
            <div className="mt-1 font-mono text-2xl font-bold text-amber-400">
              {summary.high_bias_count} / {summary.anomaly_count}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Category Breakdown Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Scale className="h-4 w-4 text-primary" />
            Protected Category Sensitivity Breakdown
          </CardTitle>
          <CardDescription>
            Average and peak bias sensitivity across demographic, geographic,
            economic, experiential, and procedural axes.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={category_breakdown}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="category" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderColor: '#1e293b',
                    fontSize: '12px',
                  }}
                />
                <Bar
                  dataKey="average_score"
                  name="Average Score"
                  fill="#3b82f6"
                  radius={[4, 4, 0, 0]}
                />
                <Bar
                  dataKey="max_score"
                  name="Max Observed Score"
                  fill="#f59e0b"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Flagged Decisions Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <AlertTriangle className="h-4 w-4 text-amber-400" />
            Flagged Decisions Requiring Fairness Oversight (
            {flagged_decisions.length})
          </CardTitle>
          <CardDescription>
            Decisions exceeding the 0.40 bias sensitivity threshold or flagged
            by IsolationForest anomaly detection.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {flagged_decisions.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              No decisions currently exceed bias or anomaly thresholds.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-border bg-muted/40 text-muted-foreground">
                    <th className="px-4 py-2.5 font-medium">Decision Case</th>
                    <th className="px-4 py-2.5 font-medium">Category</th>
                    <th className="px-4 py-2.5 font-medium">Bias Score</th>
                    <th className="px-4 py-2.5 font-medium">
                      Flagged Indicators
                    </th>
                    <th className="px-4 py-2.5 text-right font-medium">
                      Governance Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {flagged_decisions.map((item) => (
                    <tr key={item.decision_id} className="hover:bg-muted/20">
                      <td className="px-4 py-3">
                        <Link
                          to={`/app/decisions/${item.decision_id}`}
                          className="font-medium text-foreground hover:text-primary"
                        >
                          {item.title}
                        </Link>
                        <div className="font-mono text-[11px] text-muted-foreground">
                          {item.decision_id}
                        </div>
                      </td>
                      <td className="px-4 py-3 capitalize text-muted-foreground">
                        {item.application_type.replace(/_/g, ' ')}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-foreground">
                            {(item.bias_score * 100).toFixed(1)}%
                          </span>
                          <Badge
                            variant={
                              item.risk_level === 'high'
                                ? 'destructive'
                                : 'warning'
                            }
                          >
                            {item.risk_level}
                          </Badge>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {item.bias_indicators.length === 0 ? (
                            <span className="text-muted-foreground">
                              ML Anomaly Flag
                            </span>
                          ) : (
                            item.bias_indicators.map((ind) => (
                              <Badge key={ind} variant="outline">
                                {ind}
                              </Badge>
                            ))
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="inline-flex items-center gap-1.5">
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={rescanMutation.isPending}
                            onClick={() =>
                              rescanMutation.mutate(item.decision_id)
                            }
                          >
                            <Sparkles className="mr-1 h-3.5 w-3.5" />
                            Rescan
                          </Button>
                          <Button
                            variant="secondary"
                            size="sm"
                            disabled={triggerReviewMutation.isPending}
                            onClick={() =>
                              triggerReviewMutation.mutate({
                                decision_id: item.decision_id,
                                reason: `Bias score ${(
                                  item.bias_score * 100
                                ).toFixed(1)}% flagged in Fairness Scanner`,
                              })
                            }
                          >
                            {triggerReviewMutation.isPending ? (
                              <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <ShieldAlert className="mr-1 h-3.5 w-3.5 text-amber-400" />
                            )}
                            Trigger Human Review
                          </Button>
                          <Button asChild variant="outline" size="sm">
                            <Link to={`/app/decisions/${item.decision_id}`}>
                              <ArrowUpRight className="h-3.5 w-3.5" />
                            </Link>
                          </Button>
                        </div>
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

