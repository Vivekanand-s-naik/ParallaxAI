import { NavLink, useLocation } from 'react-router-dom';
import {
  ChevronLeft,
  ChevronRight,
  Layers,
  Shield,
  X,
} from 'lucide-react';
import { API_CONFIG } from '@/lib/api-config';
import {
  getVisibleNavigationItems,
  NAVIGATION_GROUPS,
} from '@/lib/navigation-config';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth-store';
import { useUiStore } from '@/stores/ui-store';
import { Skeleton } from '@/components/ui/skeleton';

export function AppSidebar() {
  const location = useLocation();
  const isCollapsed = useUiStore((s) => s.isSidebarCollapsed);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);
  const isMobileOpen = useUiStore((s) => s.isMobileSidebarOpen);
  const setMobileOpen = useUiStore((s) => s.setMobileSidebarOpen);

  const user = useAuthStore((s) => s.user);
  const permissionsLoaded = useAuthStore((s) => s.permissionsLoaded);

  const isSuperAdmin = Boolean(user?.roles?.includes('SUPER_ADMIN'));
  const visibleItems = getVisibleNavigationItems({
    permissionsLoaded,
    isSuperAdmin,
    userPermissions: user?.permissions ?? [],
  });

  const renderSidebarContent = (mobileMode: boolean) => {
    const collapsed = mobileMode ? false : isCollapsed;

    return (
      <div className="flex h-full flex-col bg-sidebar text-sidebar-foreground">
        {/* Branding Header */}
        <div
          className={cn(
            'flex h-16 shrink-0 items-center border-b border-sidebar-border px-4',
            collapsed ? 'justify-center px-2' : 'justify-between'
          )}
        >
          <div className="flex items-center gap-3 overflow-hidden">
            <div
              aria-hidden="true"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-primary/40 bg-primary/15 text-primary shadow-xs"
            >
              <Layers className="h-5 w-5" />
            </div>
            {!collapsed && (
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="truncate text-sm font-bold tracking-wider text-foreground">
                    PARALLAXAI
                  </span>
                  <span className="rounded border border-primary/30 bg-primary/10 px-1.5 py-0.2 font-mono text-[10px] font-semibold uppercase text-primary">
                    {API_CONFIG.environment === 'production' ? 'PROD' : 'GOV'}
                  </span>
                </div>
                <p className="truncate text-[10px] font-medium tracking-widest text-muted-foreground">
                  AI GOVERNANCE COMMAND CENTER
                </p>
              </div>
            )}
          </div>

          {mobileMode && (
            <button
              type="button"
              aria-label="Close navigation drawer"
              onClick={() => setMobileOpen(false)}
              className="rounded-md p-1.5 text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Navigation Groups */}
        <nav
          aria-label="Primary governance navigation"
          className="flex-1 space-y-5 overflow-y-auto px-3 py-4"
        >
          {!permissionsLoaded ? (
            <div
              data-testid="sidebar-permissions-loading"
              aria-label="Loading authorized navigation"
              className="space-y-3 px-1"
            >
              {Array.from({ length: 5 }).map((_, idx) => (
                <Skeleton key={idx} className="h-8 w-full" />
              ))}
            </div>
          ) : (
            NAVIGATION_GROUPS.map((group) => {
              const groupItems = visibleItems.filter(
                (item) => item.group === group.key
              );
              if (groupItems.length === 0) return null;

              return (
                <div key={group.key} className="space-y-1">
                  {!collapsed && (
                    <div className="px-2.5 pb-1 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/80">
                      {group.label}
                    </div>
                  )}
                  <ul className="space-y-1">
                    {groupItems.map((item) => {
                      const Icon = item.icon;
                      const isActive =
                        location.pathname === item.path ||
                        location.pathname.startsWith(`${item.path}/`);

                      return (
                        <li key={item.id}>
                          <NavLink
                            to={item.path}
                            title={collapsed ? `${item.label} — ${item.description}` : undefined}
                            aria-label={collapsed ? item.label : undefined}
                            onClick={() => {
                              if (mobileMode) setMobileOpen(false);
                            }}
                            className={cn(
                              'group flex items-center gap-3 rounded-md px-2.5 py-2 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                              collapsed && 'justify-center px-2',
                              isActive
                                ? 'border-l-2 border-primary bg-primary/15 text-primary font-semibold'
                                : 'text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-foreground'
                            )}
                          >
                            <Icon
                              aria-hidden="true"
                              className={cn(
                                'h-4 w-4 shrink-0 transition-colors',
                                isActive
                                  ? 'text-primary'
                                  : 'text-muted-foreground group-hover:text-foreground'
                              )}
                            />
                            {!collapsed && (
                              <span className="truncate">{item.label}</span>
                            )}
                          </NavLink>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              );
            })
          )}
        </nav>

        {/* Footer: Governance posture & Collapse toggle */}
        <div className="border-t border-sidebar-border p-3">
          {!collapsed && user && (
            <div className="mb-2.5 flex items-center gap-2 rounded-md border border-sidebar-border bg-sidebar-accent/60 px-2.5 py-2 text-[11px]">
              <Shield className="h-3.5 w-3.5 shrink-0 text-primary" />
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium text-foreground">
                  RBAC Policy Active
                </p>
                <p className="truncate font-mono text-[10px] text-muted-foreground">
                  Role: {user.role}
                </p>
              </div>
            </div>
          )}

          {!mobileMode && (
            <button
              type="button"
              onClick={toggleSidebar}
              aria-label={
                collapsed ? 'Expand sidebar navigation' : 'Collapse sidebar navigation'
              }
              aria-expanded={!collapsed}
              className={cn(
                'flex w-full items-center gap-2 rounded-md border border-sidebar-border bg-sidebar-accent/40 px-2.5 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                collapsed && 'justify-center px-0'
              )}
            >
              {collapsed ? (
                <ChevronRight className="h-4 w-4" />
              ) : (
                <>
                  <ChevronLeft className="h-4 w-4" />
                  <span>Collapse Sidebar</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>
    );
  };

  return (
    <>
      {/* Desktop Sidebar */}
      <aside
        data-testid="desktop-sidebar"
        data-collapsed={isCollapsed ? 'true' : 'false'}
        className={cn(
          'hidden shrink-0 border-r border-sidebar-border transition-[width] duration-200 md:block',
          isCollapsed ? 'w-16' : 'w-64'
        )}
      >
        {renderSidebarContent(false)}
      </aside>

      {/* Mobile Responsive Drawer */}
      {isMobileOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Mobile navigation drawer"
          data-testid="mobile-sidebar-drawer"
          className="fixed inset-0 z-50 flex md:hidden"
        >
          <div
            className="fixed inset-0 bg-black/70 backdrop-blur-xs"
            onClick={() => setMobileOpen(false)}
          />
          <div className="relative z-10 flex w-72 max-w-[85vw] flex-col border-r border-sidebar-border bg-sidebar">
            {renderSidebarContent(true)}
          </div>
        </div>
      )}
    </>
  );
}
