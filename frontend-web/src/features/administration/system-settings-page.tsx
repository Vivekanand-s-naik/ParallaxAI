import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Cpu,
  Database,
  Lock,
  LogOut,
  RefreshCw,
  Server,
  ShieldCheck,
  Trash2,
} from 'lucide-react';
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
import { formatDateTime } from '@/lib/utils';

export function SystemSettingsPage() {
  const queryClient = useQueryClient();
  const addToast = useUiStore((s) => s.addToast);

  const settingsQuery = useQuery({
    queryKey: queryKeys.system.settings(),
    queryFn: () => platformServices.getSystemSettings(),
  });

  const sessionsQuery = useQuery({
    queryKey: queryKeys.auth.sessions(),
    queryFn: () => platformServices.listActiveSessions(),
  });

  const revokeSessionMutation = useMutation({
    mutationFn: (sessionId: string) =>
      platformServices.revokeSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.auth.sessions() });
      addToast({
        title: 'Session Revoked',
        description: 'Refresh token family invalidated in PostgreSQL.',
        variant: 'info',
      });
    },
  });

  const revokeAllMutation = useMutation({
    mutationFn: () => platformServices.revokeAllSessions(),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.auth.sessions() });
      addToast({
        title: 'All Sessions Revoked',
        description: `${res.revoked_count} active session(s) revoked.`,
        variant: 'warning',
      });
    },
  });

  if (settingsQuery.isLoading) {
    return <LoadingSkeleton cards={4} rows={4} />;
  }

  if (settingsQuery.isError || !settingsQuery.data) {
    return (
      <ErrorState
        title="Unable to load System Settings"
        message={
          settingsQuery.error
            ? normalizeApiError(settingsQuery.error).message
            : 'Configuration unavailable.'
        }
        onRetry={() => settingsQuery.refetch()}
      />
    );
  }

  const {
    platform,
    infrastructure,
    ai_providers,
    authentication,
    rate_limits,
  } = settingsQuery.data;

  return (
    <div className="space-y-6" data-testid="system-settings-page">
      <PageHeader
        title="Platform Infrastructure & Security Configuration"
        description="Inspect live PostgreSQL, Redis, AI provider integrations, Argon2id/JWT security parameters, Redis rate-limit policies, and active refresh sessions."
        badge={
          <Badge variant="info">{platform.environment.toUpperCase()}</Badge>
        }
        actions={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              settingsQuery.refetch();
              sessionsQuery.refetch();
            }}
          >
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            Refresh Telemetry
          </Button>
        }
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Infrastructure Status */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Database className="h-4 w-4 text-primary" />
              Core Infrastructure Services
            </CardTitle>
            <CardDescription>
              Database persistence, Redis rate-limit store, and real-time
              WebSocket broker.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex items-center justify-between rounded-lg border border-border bg-secondary/40 p-3">
              <div>
                <div className="font-semibold text-foreground">
                  {infrastructure.database.engine}
                </div>
                <div className="text-muted-foreground">
                  Primary relational governance store
                </div>
              </div>
              <Badge
                variant={
                  infrastructure.database.connected ? 'success' : 'destructive'
                }
              >
                {infrastructure.database.status}
              </Badge>
            </div>

            <div className="flex items-center justify-between rounded-lg border border-border bg-secondary/40 p-3">
              <div>
                <div className="font-semibold text-foreground">
                  {infrastructure.redis.engine}
                </div>
                <div className="text-muted-foreground">
                  Rate limiting:{' '}
                  {infrastructure.redis.rate_limiting_enabled
                    ? 'Enabled'
                    : 'Disabled'}
                </div>
              </div>
              <Badge
                variant={
                  infrastructure.redis.connected ? 'success' : 'warning'
                }
              >
                {infrastructure.redis.status}
              </Badge>
            </div>

            <div className="flex items-center justify-between rounded-lg border border-border bg-secondary/40 p-3">
              <div>
                <div className="font-semibold text-foreground">
                  WebSocket Event Broker ({infrastructure.websocket.endpoint})
                </div>
                <div className="text-muted-foreground">
                  Active clients: {infrastructure.websocket.active_connections}{' '}
                  • Messages sent:{' '}
                  {infrastructure.websocket.total_messages_sent}
                </div>
              </div>
              <Badge variant="info">Live</Badge>
            </div>
          </CardContent>
        </Card>

        {/* AI Providers & ML Fairness Engine */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Cpu className="h-4 w-4 text-sky-400" />
              AI Provider & ML Fairness Runtime
            </CardTitle>
            <CardDescription>
              Honest runtime availability without exposing API keys to the
              browser.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2.5 text-xs">
            {[
              ai_providers.openai,
              ai_providers.anthropic,
              ai_providers.gemini,
            ].map((prov) => (
              <div
                key={prov.provider}
                className="flex items-center justify-between rounded-lg border border-border bg-secondary/40 p-3"
              >
                <div>
                  <div className="font-semibold text-foreground">
                    {prov.provider}
                  </div>
                  <div className="font-mono text-[11px] text-muted-foreground">
                    Model: {prov.model}
                  </div>
                </div>
                <Badge variant={prov.configured ? 'success' : 'warning'}>
                  {prov.configured
                    ? 'API Key Configured'
                    : 'Deterministic Fallback'}
                </Badge>
              </div>
            ))}

            <div className="flex items-center justify-between rounded-lg border border-border bg-secondary/40 p-3">
              <div>
                <div className="font-semibold text-foreground">
                  {ai_providers.ml_bias_detector.engine}
                </div>
                <div className="text-muted-foreground">
                  Bias & Fairness ML Detector
                </div>
              </div>
              <Badge
                variant={
                  ai_providers.ml_bias_detector.trained ? 'success' : 'warning'
                }
              >
                {ai_providers.ml_bias_detector.status}
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Authentication Security & Rate Limits */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Lock className="h-4 w-4 text-primary" />
              Authentication & Identity Security
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5 text-xs">
            <div className="flex justify-between border-b border-border/60 pb-2">
              <span className="text-muted-foreground">Password Hashing</span>
              <span className="font-mono text-foreground">
                {authentication.password_hashing}
              </span>
            </div>
            <div className="flex justify-between border-b border-border/60 pb-2">
              <span className="text-muted-foreground">Session Strategy</span>
              <span className="font-mono text-foreground">
                {authentication.session_strategy}
              </span>
            </div>
            <div className="flex justify-between border-b border-border/60 pb-2">
              <span className="text-muted-foreground">
                Default Self-Registration Role
              </span>
              <Badge variant="outline">
                {platform.default_registration_role}
              </Badge>
            </div>
            <div className="flex justify-between border-b border-border/60 pb-2">
              <span className="text-muted-foreground">
                Google OAuth 2.0 / OIDC
              </span>
              <Badge
                variant={
                  authentication.google_oauth_enabled ? 'success' : 'outline'
                }
              >
                {authentication.google_oauth_enabled
                  ? 'Configured'
                  : 'Not Configured'}
              </Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">
                Outbound SMTP Password Reset
              </span>
              <Badge
                variant={
                  authentication.email_reset_configured ? 'success' : 'outline'
                }
              >
                {authentication.email_reset_configured
                  ? 'Configured'
                  : 'Not Configured'}
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Server className="h-4 w-4 text-sky-400" />
              Active Rate Limit Quotas
            </CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3 text-xs">
            <div className="rounded border border-border bg-secondary/40 p-2.5">
              <div className="text-muted-foreground">Login Attempts</div>
              <div className="mt-1 font-mono font-bold text-foreground">
                {rate_limits.login_per_minute} / min
              </div>
            </div>
            <div className="rounded border border-border bg-secondary/40 p-2.5">
              <div className="text-muted-foreground">Registrations</div>
              <div className="mt-1 font-mono font-bold text-foreground">
                {rate_limits.register_per_hour} / hour
              </div>
            </div>
            <div className="rounded border border-border bg-secondary/40 p-2.5">
              <div className="text-muted-foreground">General API</div>
              <div className="mt-1 font-mono font-bold text-foreground">
                {rate_limits.general_api_per_minute} / min
              </div>
            </div>
            <div className="rounded border border-border bg-secondary/40 p-2.5">
              <div className="text-muted-foreground">AI Evaluations</div>
              <div className="mt-1 font-mono font-bold text-foreground">
                {rate_limits.ai_inference_per_minute} / min
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Active Refresh Token Sessions */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-sm">
              <ShieldCheck className="h-4 w-4 text-emerald-400" />
              Active Refresh Token Sessions (
              {sessionsQuery.data?.length ?? 0})
            </CardTitle>
            <CardDescription>
              Manage your active authenticated device sessions stored in
              PostgreSQL.
            </CardDescription>
          </div>
          <Button
            variant="destructive"
            size="sm"
            disabled={
              revokeAllMutation.isPending ||
              (sessionsQuery.data?.length ?? 0) === 0
            }
            onClick={() => revokeAllMutation.mutate()}
          >
            <LogOut className="mr-1.5 h-3.5 w-3.5" />
            Revoke All Sessions
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {(sessionsQuery.data ?? []).map((sess) => (
              <div
                key={sess.id}
                className="flex items-center justify-between rounded-lg border border-border bg-secondary/40 p-3 text-xs"
              >
                <div>
                  <div className="font-mono text-foreground">
                    IP: {sess.ip_address ?? '127.0.0.1'} • Family:{' '}
                    {sess.family_id.slice(0, 8)}…
                  </div>
                  <div className="text-muted-foreground">
                    {sess.user_agent ?? 'Browser Session'} • Expires{' '}
                    {formatDateTime(sess.expires_at)}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => revokeSessionMutation.mutate(sess.id)}
                  className="text-red-400 hover:bg-red-500/10"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

