import { Outlet } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/app/query-client';
import { AppSidebar } from '@/components/navigation/app-sidebar';
import { AppTopbar } from '@/components/navigation/app-topbar';
import { ToastViewport } from '@/components/feedback/toast-viewport';
import { useGovernanceWebSocket } from '@/hooks/use-governance-websocket';
import { platformServices } from '@/services/platform-services';
import { useAuthStore } from '@/stores/auth-store';

export function AppShellLayout() {
  useGovernanceWebSocket();

  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const hasAnyPermission = useAuthStore((s) => s.hasAnyPermission);
  const canReadNotifications = hasAnyPermission(['notifications:read']);
  const isTestEnv = import.meta.env.MODE === 'test';

  const notifQuery = useQuery({
    queryKey: queryKeys.notifications.list({ limit: 8 }),
    queryFn: () => platformServices.listNotifications({ limit: 8 }),
    enabled: !isTestEnv && isAuthenticated && canReadNotifications,
    staleTime: 30_000,
  });

  return (
    <div className="flex min-h-screen w-full bg-background text-foreground">
      <AppSidebar />

      <div className="flex min-w-0 flex-1 flex-col">
        <AppTopbar
          notifications={notifQuery.data?.items ?? []}
          unreadCount={notifQuery.data?.unread_count ?? 0}
        />

        <main
          id="main-workspace"
          className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8"
        >
          <div className="mx-auto max-w-7xl space-y-6">
            <Outlet />
          </div>
        </main>
      </div>

      <ToastViewport />
    </div>
  );
}
