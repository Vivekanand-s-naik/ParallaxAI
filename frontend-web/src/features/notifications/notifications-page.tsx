import * as React from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowUpRight,
  Bell,
  CheckCheck,
  CheckCircle2,
  RefreshCw,
  Trash2,
} from 'lucide-react';
import { queryKeys } from '@/app/query-client';
import { platformServices } from '@/services/platform-services';
import { PageHeader } from '@/components/common/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { EmptyState } from '@/components/feedback/empty-state';
import { ErrorState } from '@/components/feedback/error-state';
import { LoadingSkeleton } from '@/components/feedback/loading-skeleton';
import { useUiStore } from '@/stores/ui-store';
import { normalizeApiError } from '@/services/api-error';
import { formatDateTime } from '@/lib/utils';

export function NotificationsPage() {
  const queryClient = useQueryClient();
  const addToast = useUiStore((s) => s.addToast);

  const [readFilter, setReadFilter] = React.useState<'all' | 'unread'>('all');
  const [priorityFilter, setPriorityFilter] = React.useState('');

  const params = React.useMemo(
    () => ({
      is_read: readFilter === 'unread' ? false : undefined,
      priority: priorityFilter || undefined,
    }),
    [readFilter, priorityFilter]
  );

  const notifQuery = useQuery({
    queryKey: queryKeys.notifications.list(params),
    queryFn: () => platformServices.listNotifications(params),
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => platformServices.markNotificationRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.system.stats() });
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => platformServices.markAllNotificationsRead(),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.system.stats() });
      addToast({
        title: 'Notifications Marked Read',
        description: `${res.updated_count} notification(s) marked as read.`,
        variant: 'info',
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => platformServices.deleteNotification(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.system.stats() });
    },
  });

  return (
    <div className="space-y-6" data-testid="notifications-page">
      <PageHeader
        title="Governance Notification Center"
        description="Real-time operational alerts for high-bias detections, human review escalations, policy violations, and consensus deadlocks."
        badge={
          <Badge variant="warning">
            {notifQuery.data?.unread_count ?? 0} Unread
          </Badge>
        }
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => notifQuery.refetch()}
            >
              <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
              Refresh
            </Button>
            <Button
              size="sm"
              onClick={() => markAllReadMutation.mutate()}
              disabled={
                markAllReadMutation.isPending ||
                (notifQuery.data?.unread_count ?? 0) === 0
              }
            >
              <CheckCheck className="mr-1.5 h-4 w-4" />
              Mark All Read
            </Button>
          </div>
        }
      />

      <Card>
        <CardContent className="flex flex-wrap items-center gap-3 p-4">
          <Button
            variant={readFilter === 'all' ? 'default' : 'secondary'}
            size="sm"
            onClick={() => setReadFilter('all')}
          >
            All Alerts ({notifQuery.data?.total ?? 0})
          </Button>
          <Button
            variant={readFilter === 'unread' ? 'default' : 'secondary'}
            size="sm"
            onClick={() => setReadFilter('unread')}
          >
            Unread Only ({notifQuery.data?.unread_count ?? 0})
          </Button>

          <select
            aria-label="Filter notifications by priority"
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="ml-auto h-8 rounded-md border border-border bg-secondary/40 px-2.5 text-xs text-foreground"
          >
            <option value="">All Priorities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </CardContent>
      </Card>

      {notifQuery.isLoading ? (
        <LoadingSkeleton cards={2} rows={5} />
      ) : notifQuery.isError ? (
        <ErrorState
          title="Unable to load notifications"
          message={normalizeApiError(notifQuery.error).message}
          onRetry={() => notifQuery.refetch()}
        />
      ) : !notifQuery.data || notifQuery.data.items.length === 0 ? (
        <EmptyState
          icon={Bell}
          title="No active governance notifications"
          description="Operational alerts and fairness escalations will appear here."
        />
      ) : (
        <div className="space-y-3">
          {notifQuery.data.items.map((n) => (
            <Card
              key={n.id}
              className={
                n.is_read ? 'opacity-75' : 'border-primary/40 bg-secondary/20'
              }
            >
              <CardContent className="flex flex-col justify-between gap-3 p-4 sm:flex-row sm:items-center">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge
                      variant={
                        n.priority === 'critical' || n.priority === 'high'
                          ? 'destructive'
                          : n.priority === 'medium'
                            ? 'warning'
                            : 'info'
                      }
                    >
                      {n.priority}
                    </Badge>
                    <span className="text-sm font-semibold text-foreground">
                      {n.title}
                    </span>
                    {!n.is_read && <Badge variant="default">Unread</Badge>}
                  </div>
                  <p className="text-xs text-muted-foreground">{n.message}</p>
                  <div className="text-[11px] text-muted-foreground">
                    {formatDateTime(n.timestamp)}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {n.related_decision_id && (
                    <Button asChild variant="secondary" size="sm">
                      <Link to={`/app/decisions/${n.related_decision_id}`}>
                        Inspect Case
                        <ArrowUpRight className="ml-1 h-3.5 w-3.5" />
                      </Link>
                    </Button>
                  )}
                  {!n.is_read && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => markReadMutation.mutate(n.id)}
                    >
                      <CheckCircle2 className="mr-1 h-3.5 w-3.5 text-emerald-400" />
                      Mark Read
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteMutation.mutate(n.id)}
                    className="text-red-400 hover:bg-red-500/10"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

