import * as React from 'react';
import { BrowserRouter, useRoutes } from 'react-router-dom';
import { AppProviders } from './providers';
import { appRoutes } from './router';
import { authService } from '@/services/auth-service';
import { useAuthStore } from '@/stores/auth-store';

function AppRoutesRenderer() {
  return useRoutes(appRoutes);
}

export function App() {
  const isInitialized = useAuthStore((s) => s.isInitialized);

  React.useEffect(() => {
    if (!isInitialized) {
      void authService.bootstrapSession();
    }
  }, [isInitialized]);

  return (
    <AppProviders>
      <BrowserRouter>
        <AppRoutesRenderer />
      </BrowserRouter>
    </AppProviders>
  );
}

