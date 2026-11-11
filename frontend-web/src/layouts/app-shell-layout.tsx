import { Outlet } from 'react-router-dom';
import { AppSidebar } from '@/components/navigation/app-sidebar';
import { AppTopbar } from '@/components/navigation/app-topbar';
import { ToastViewport } from '@/components/feedback/toast-viewport';

export function AppShellLayout() {
  return (
    <div className="flex min-h-screen w-full bg-background text-foreground">
      <AppSidebar />

      <div className="flex min-w-0 flex-1 flex-col">
        <AppTopbar />

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

