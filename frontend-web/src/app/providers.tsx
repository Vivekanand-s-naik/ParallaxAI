import * as React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppErrorBoundary } from '@/components/feedback/error-boundary';
import { queryClient as defaultQueryClient } from './query-client';

export interface AppProvidersProps {
  children: React.ReactNode;
  client?: QueryClient;
}

export function AppProviders({
  children,
  client = defaultQueryClient,
}: AppProvidersProps) {
  return (
    <AppErrorBoundary>
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    </AppErrorBoundary>
  );
}

