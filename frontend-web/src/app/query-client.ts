import { QueryClient } from '@tanstack/react-query';
import { ApiError } from '@/services/api-error';

/**
 * Centralized Query Key Conventions for ParallaxAI.
 */
export const queryKeys = {
  auth: {
    all: ['auth'] as const,
    me: () => [...queryKeys.auth.all, 'me'] as const,
    providers: () => [...queryKeys.auth.all, 'providers'] as const,
    sessions: () => [...queryKeys.auth.all, 'sessions'] as const,
  },
  system: {
    all: ['system'] as const,
    health: () => [...queryKeys.system.all, 'health'] as const,
    stats: () => [...queryKeys.system.all, 'stats'] as const,
    settings: () => [...queryKeys.system.all, 'settings'] as const,
  },
  decisions: {
    all: ['decisions'] as const,
    list: (filters?: Record<string, unknown>) =>
      [...queryKeys.decisions.all, 'list', filters ?? {}] as const,
    detail: (id: string) => [...queryKeys.decisions.all, 'detail', id] as const,
    workspace: (id: string) =>
      [...queryKeys.decisions.all, 'workspace', id] as const,
  },
  agents: {
    all: ['agents'] as const,
    list: (filters?: Record<string, unknown>) =>
      [...queryKeys.agents.all, 'list', filters ?? {}] as const,
    detail: (id: string) => [...queryKeys.agents.all, 'detail', id] as const,
    influenceGraph: () => [...queryKeys.agents.all, 'influence-graph'] as const,
  },
  votes: {
    all: ['votes'] as const,
    list: (filters?: Record<string, unknown>) =>
      [...queryKeys.votes.all, 'list', filters ?? {}] as const,
    summary: (decisionId: string) =>
      [...queryKeys.votes.all, 'summary', decisionId] as const,
  },
  bias: {
    all: ['bias'] as const,
    overview: () => [...queryKeys.bias.all, 'overview'] as const,
  },
  governance: {
    all: ['governance'] as const,
    rules: (filters?: Record<string, unknown>) =>
      [...queryKeys.governance.all, 'rules', filters ?? {}] as const,
  },
  audit: {
    all: ['audit'] as const,
    list: (filters?: Record<string, unknown>) =>
      [...queryKeys.audit.all, 'list', filters ?? {}] as const,
    decision: (decisionId: string) =>
      [...queryKeys.audit.all, 'decision', decisionId] as const,
  },
  notifications: {
    all: ['notifications'] as const,
    list: (filters?: Record<string, unknown>) =>
      [...queryKeys.notifications.all, 'list', filters ?? {}] as const,
  },
  users: {
    all: ['users'] as const,
    list: (filters?: Record<string, unknown>) =>
      [...queryKeys.users.all, 'list', filters ?? {}] as const,
    detail: (id: string) => [...queryKeys.users.all, 'detail', id] as const,
  },
  roles: {
    all: ['roles'] as const,
    list: () => [...queryKeys.roles.all, 'list'] as const,
    permissions: () => [...queryKeys.roles.all, 'permissions'] as const,
  },
};

function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  if (failureCount >= 2) return false;
  if (error instanceof ApiError) {
    // Never retry client/auth/permission/rate-limit errors
    if ([400, 401, 403, 404, 409, 422, 429].includes(error.status)) {
      return false;
    }
  }
  return true;
}

export function createAppQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        gcTime: 5 * 60_000,
        refetchOnWindowFocus: false,
        retry: shouldRetryQuery,
      },
      mutations: {
        retry: false, // Never retry non-idempotent mutations automatically
      },
    },
  });
}

export const queryClient = createAppQueryClient();

