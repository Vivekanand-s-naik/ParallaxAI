import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/app/query-client';
import { API_CONFIG } from '@/lib/api-config';
import { useAuthStore } from '@/stores/auth-store';
import { useUiStore } from '@/stores/ui-store';

export interface GovernanceWsEvent {
  type: string;
  data?: Record<string, unknown>;
  timestamp?: string;
}

export interface UseGovernanceWebSocketOptions {
  enabled?: boolean;
  wsUrl?: string;
}

export function useGovernanceWebSocket(
  options?: UseGovernanceWebSocketOptions
) {
  const queryClient = useQueryClient();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const accessToken = useAuthStore((s) => s.accessToken);
  const setWsConnectionState = useUiStore((s) => s.setWsConnectionState);
  const addToast = useUiStore((s) => s.addToast);

  const isTestEnv = import.meta.env.MODE === 'test';
  const enabled = options?.enabled ?? !isTestEnv;
  const baseUrl = options?.wsUrl ?? API_CONFIG.wsUrl;

  const wsRef = React.useRef<WebSocket | null>(null);
  const reconnectTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(
    null
  );
  const attemptRef = React.useRef(0);

  React.useEffect(() => {
    if (!enabled || !isAuthenticated || !accessToken) {
      setWsConnectionState('disconnected');
      return;
    }

    let unmounted = false;

    const handleIncomingEvent = (payload: GovernanceWsEvent) => {
      switch (payload.type) {
        case 'decision_created':
        case 'decision_updated':
        case 'decision_deleted':
          queryClient.invalidateQueries({ queryKey: queryKeys.decisions.all });
          queryClient.invalidateQueries({
            queryKey: queryKeys.system.stats(),
          });
          queryClient.invalidateQueries({ queryKey: queryKeys.audit.all });
          break;

        case 'vote_created':
          queryClient.invalidateQueries({ queryKey: queryKeys.votes.all });
          queryClient.invalidateQueries({ queryKey: queryKeys.decisions.all });
          queryClient.invalidateQueries({ queryKey: queryKeys.agents.all });
          queryClient.invalidateQueries({
            queryKey: queryKeys.system.stats(),
          });
          break;

        case 'governance_rule_created':
        case 'governance_rule_updated':
        case 'governance_rule_deleted':
          queryClient.invalidateQueries({
            queryKey: queryKeys.governance.all,
          });
          queryClient.invalidateQueries({
            queryKey: queryKeys.system.stats(),
          });
          break;

        case 'notification_created':
        case 'notification_updated':
        case 'notifications_marked_all_read':
          queryClient.invalidateQueries({
            queryKey: queryKeys.notifications.all,
          });
          queryClient.invalidateQueries({
            queryKey: queryKeys.system.stats(),
          });
          break;

        case 'bias_review_triggered':
          queryClient.invalidateQueries({ queryKey: queryKeys.bias.all });
          queryClient.invalidateQueries({ queryKey: queryKeys.decisions.all });
          queryClient.invalidateQueries({
            queryKey: queryKeys.notifications.all,
          });
          queryClient.invalidateQueries({
            queryKey: queryKeys.system.stats(),
          });
          addToast({
            title: 'Real-Time Fairness Alert',
            description:
              'A decision case was escalated for human bias & fairness review.',
            variant: 'warning',
          });
          break;

        case 'stats_update':
          queryClient.invalidateQueries({
            queryKey: queryKeys.system.stats(),
          });
          break;

        default:
          break;
      }
    };

    const connect = () => {
      if (unmounted) return;
      setWsConnectionState(
        attemptRef.current === 0 ? 'connecting' : 'reconnecting'
      );

      try {
        const separator = baseUrl.includes('?') ? '&' : '?';
        const socket = new WebSocket(
          `${baseUrl}${separator}token=${encodeURIComponent(accessToken)}`
        );
        wsRef.current = socket;

        socket.onopen = () => {
          if (unmounted) return;
          attemptRef.current = 0;
          setWsConnectionState('connected');
        };

        socket.onmessage = (event: MessageEvent) => {
          if (unmounted) return;
          try {
            const parsed = JSON.parse(String(event.data)) as GovernanceWsEvent;
            if (parsed && typeof parsed.type === 'string') {
              handleIncomingEvent(parsed);
            }
          } catch {
            // Ignore malformed non-JSON frames
          }
        };

        socket.onerror = () => {
          if (unmounted) return;
        };

        socket.onclose = () => {
          if (unmounted) return;
          setWsConnectionState('disconnected');
          attemptRef.current += 1;
          const delayMs = Math.min(15_000, 1000 * 2 ** attemptRef.current);
          reconnectTimerRef.current = setTimeout(connect, delayMs);
        };
      } catch {
        setWsConnectionState('disconnected');
      }
    };

    connect();

    return () => {
      unmounted = true;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setWsConnectionState('disconnected');
    };
  }, [
    enabled,
    isAuthenticated,
    accessToken,
    baseUrl,
    queryClient,
    setWsConnectionState,
    addToast,
  ]);
}
