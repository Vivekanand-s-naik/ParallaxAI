import * as React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Bell,
  ChevronRight,
  LogOut,
  Menu,
  PanelRight,
  Radio,
  Search,
  Settings,
  Shield,
  User as UserIcon,
} from 'lucide-react';
import {
  generateBreadcrumbs,
  getVisibleNavigationItems,
} from '@/lib/navigation-config';
import { cn, formatTimestamp, getInitials } from '@/lib/utils';
import { authService } from '@/services/auth-service';
import { useAuthStore } from '@/stores/auth-store';
import { useUiStore } from '@/stores/ui-store';
import type { NotificationItem } from '@/types/governance';
import type { WebSocketConnectionState } from '@/types/navigation';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';

const WS_STATE_CONFIG: Record<
  WebSocketConnectionState,
  { label: string; dotClass: string; badgeClass: string }
> = {
  connected: {
    label: 'WS Connected',
    dotClass: 'bg-emerald-400',
    badgeClass: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  },
  connecting: {
    label: 'WS Connecting',
    dotClass: 'bg-amber-400 animate-pulse',
    badgeClass: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
  },
  reconnecting: {
    label: 'WS Reconnecting',
    dotClass: 'bg-amber-400 animate-pulse',
    badgeClass: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
  },
  disconnected: {
    label: 'WS Disconnected',
    dotClass: 'bg-slate-400',
    badgeClass: 'border-border bg-muted/50 text-muted-foreground',
  },
  unavailable: {
    label: 'WS Unavailable',
    dotClass: 'bg-red-400',
    badgeClass: 'border-red-500/30 bg-red-500/10 text-red-300',
  },
};

export interface AppTopbarProps {
  notifications?: NotificationItem[];
  unreadCount?: number;
  hasContextualPanel?: boolean;
}

export function AppTopbar({
  notifications = [],
  unreadCount = 0,
  hasContextualPanel = false,
}: AppTopbarProps) {
  const location = useLocation();
  const navigate = useNavigate();

  const user = useAuthStore((s) => s.user);
  const permissionsLoaded = useAuthStore((s) => s.permissionsLoaded);

  const setMobileSidebarOpen = useUiStore((s) => s.setMobileSidebarOpen);
  const wsConnectionState = useUiStore((s) => s.wsConnectionState);
  const isCommandSearchOpen = useUiStore((s) => s.isCommandSearchOpen);
  const setCommandSearchOpen = useUiStore((s) => s.setCommandSearchOpen);
  const isRightPanelOpen = useUiStore((s) => s.isRightPanelOpen);
  const setRightPanelOpen = useUiStore((s) => s.setRightPanelOpen);

  const [searchQuery, setSearchQuery] = React.useState('');
  const [isNotifOpen, setIsNotifOpen] = React.useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = React.useState(false);

  const breadcrumbs = React.useMemo(
    () => generateBreadcrumbs(location.pathname),
    [location.pathname]
  );

  // Keyboard shortcut Ctrl+K / Cmd+K for Global Search
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setCommandSearchOpen(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [setCommandSearchOpen]);

  const visibleModules = React.useMemo(() => {
    const items = getVisibleNavigationItems({
      permissionsLoaded,
      isSuperAdmin: Boolean(user?.roles?.includes('SUPER_ADMIN')),
      userPermissions: user?.permissions ?? [],
    });
    if (!searchQuery.trim()) return items;
    const q = searchQuery.toLowerCase().trim();
    return items.filter(
      (item) =>
        item.label.toLowerCase().includes(q) ||
        item.description.toLowerCase().includes(q)
    );
  }, [permissionsLoaded, user, searchQuery]);

  const wsInfo = WS_STATE_CONFIG[wsConnectionState] ?? WS_STATE_CONFIG.disconnected;

  const handleLogout = async () => {
    setIsUserMenuOpen(false);
    await authService.logout();
    navigate('/login');
  };

  return (
    <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center justify-between gap-4 border-b border-border bg-background/95 px-4 backdrop-blur-xs sm:px-6">
      {/* Left: Mobile Menu Trigger + Breadcrumbs */}
      <div className="flex min-w-0 items-center gap-3">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label="Open navigation menu"
          onClick={() => setMobileSidebarOpen(true)}
          className="md:hidden"
        >
          <Menu className="h-5 w-5" />
        </Button>

        <nav aria-label="Breadcrumb" className="min-w-0">
          <ol className="flex items-center gap-1.5 text-xs sm:text-sm">
            {breadcrumbs.map((crumb, index) => (
              <li
                key={crumb.path}
                className="flex min-w-0 items-center gap-1.5"
              >
                {index > 0 && (
                  <ChevronRight
                    aria-hidden="true"
                    className="h-3.5 w-3.5 shrink-0 text-muted-foreground"
                  />
                )}
                {crumb.isCurrent ? (
                  <span
                    aria-current="page"
                    className="truncate font-semibold text-foreground"
                  >
                    {crumb.label}
                  </span>
                ) : (
                  <Link
                    to={crumb.path}
                    className="truncate text-muted-foreground transition-colors hover:text-foreground"
                  >
                    {crumb.label}
                  </Link>
                )}
              </li>
            ))}
          </ol>
        </nav>
      </div>

      {/* Right: Global Search, WebSocket Status, Notifications, User Menu */}
      <div className="flex items-center gap-2.5">
        {/* Global Command Search Trigger */}
        <button
          type="button"
          aria-label="Open global command search"
          onClick={() => setCommandSearchOpen(true)}
          className="flex h-9 items-center gap-2.5 rounded-md border border-border bg-card/70 px-3 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:w-60"
        >
          <Search className="h-3.5 w-3.5 shrink-0" />
          <span className="hidden flex-1 truncate text-left sm:inline">
            Search governance workspace…
          </span>
          <kbd className="hidden rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground sm:inline-block">
            Ctrl+K
          </kbd>
        </button>

        {/* Honest WebSocket Connection Status Indicator */}
        <div
          data-testid="ws-status-indicator"
          data-ws-state={wsConnectionState}
          title={`Real-time event channel state: ${wsInfo.label}`}
          className={cn(
            'hidden items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium lg:inline-flex',
            wsInfo.badgeClass
          )}
        >
          <span
            aria-hidden="true"
            className={cn('h-2 w-2 rounded-full', wsInfo.dotClass)}
          />
          <Radio className="h-3 w-3" aria-hidden="true" />
          <span>{wsInfo.label}</span>
        </div>

        {/* Optional Contextual Panel Toggle */}
        {hasContextualPanel && (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label={
              isRightPanelOpen
                ? 'Hide contextual intelligence panel'
                : 'Show contextual intelligence panel'
            }
            onClick={() => setRightPanelOpen(!isRightPanelOpen)}
          >
            <PanelRight className="h-4 w-4" />
          </Button>
        )}

        {/* Notifications Dropdown */}
        <div className="relative">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label="Notifications"
            aria-expanded={isNotifOpen}
            onClick={() => {
              setIsNotifOpen((prev) => !prev);
              setIsUserMenuOpen(false);
            }}
            className="relative"
          >
            <Bell className="h-4 w-4" />
            {unreadCount > 0 && (
              <span
                data-testid="notification-unread-badge"
                className="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 font-mono text-[10px] font-bold text-primary-foreground"
              >
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </Button>

          {isNotifOpen && (
            <div
              role="region"
              aria-label="Notifications panel"
              data-testid="notifications-dropdown"
              className="absolute right-0 mt-2 w-80 rounded-lg border border-border bg-popover p-3 text-popover-foreground shadow-xl sm:w-96"
            >
              <div className="flex items-center justify-between border-b border-border pb-2.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold uppercase tracking-wider">
                    Governance Alerts
                  </span>
                  <Badge variant="outline">{unreadCount} unread</Badge>
                </div>
                <Link
                  to="/app/notifications"
                  onClick={() => setIsNotifOpen(false)}
                  className="text-xs font-medium text-primary hover:underline"
                >
                  Open Center
                </Link>
              </div>

              {notifications.length === 0 ? (
                <div className="py-6 text-center text-xs text-muted-foreground">
                  No active governance notifications in this session.
                </div>
              ) : (
                <ul className="mt-2 max-h-64 divide-y divide-border/60 overflow-y-auto">
                  {notifications.slice(0, 5).map((item) => (
                    <li key={item.id} className="py-2.5 text-xs">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium text-foreground">
                          {item.title}
                        </span>
                        <span className="font-mono text-[10px] text-muted-foreground">
                          {formatTimestamp(item.timestamp)}
                        </span>
                      </div>
                      <p className="mt-0.5 line-clamp-2 text-muted-foreground">
                        {item.message}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>

        {/* User Profile Menu */}
        <div className="relative">
          <button
            type="button"
            aria-label="User profile menu"
            aria-expanded={isUserMenuOpen}
            onClick={() => {
              setIsUserMenuOpen((prev) => !prev);
              setIsNotifOpen(false);
            }}
            className="flex items-center gap-2.5 rounded-md border border-border bg-card/70 px-2.5 py-1.5 text-left text-xs transition-colors hover:border-primary/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary/20 font-mono text-xs font-semibold text-primary">
              {getInitials(user?.full_name)}
            </div>
            <div className="hidden min-w-0 sm:block">
              <p className="truncate font-medium text-foreground">
                {user?.full_name ?? 'Unauthenticated Operator'}
              </p>
              <p className="truncate font-mono text-[10px] text-muted-foreground">
                {user?.role ?? 'GUEST'}
              </p>
            </div>
          </button>

          {isUserMenuOpen && (
            <div
              role="menu"
              aria-label="Operator account actions"
              data-testid="user-profile-dropdown"
              className="absolute right-0 mt-2 w-64 rounded-lg border border-border bg-popover p-2 text-popover-foreground shadow-xl"
            >
              {user ? (
                <>
                  <div className="border-b border-border px-3 py-2.5">
                    <p className="truncate text-xs font-semibold text-foreground">
                      {user.full_name}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">
                      {user.email}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-1">
                      <Badge variant="default" className="font-mono text-[10px]">
                        <Shield className="h-3 w-3" />
                        {user.role}
                      </Badge>
                    </div>
                  </div>
                  <div className="py-1">
                    <Link
                      to="/app/settings"
                      role="menuitem"
                      onClick={() => setIsUserMenuOpen(false)}
                      className="flex items-center gap-2 rounded-md px-3 py-2 text-xs text-foreground hover:bg-accent"
                    >
                      <Settings className="h-3.5 w-3.5 text-muted-foreground" />
                      System & Profile Settings
                    </Link>
                  </div>
                  <div className="border-t border-border pt-1">
                    <button
                      type="button"
                      role="menuitem"
                      onClick={handleLogout}
                      className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-xs text-red-300 hover:bg-red-500/15"
                    >
                      <LogOut className="h-3.5 w-3.5" />
                      Sign Out of Command Center
                    </button>
                  </div>
                </>
              ) : (
                <div className="p-3 text-xs">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <UserIcon className="h-4 w-4" />
                    <span>No active operator session</span>
                  </div>
                  <Link
                    to="/login"
                    onClick={() => setIsUserMenuOpen(false)}
                    className="mt-2.5 block rounded-md bg-primary px-3 py-1.5 text-center font-medium text-primary-foreground"
                  >
                    Sign In
                  </Link>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Global Search Dialog */}
      <Dialog open={isCommandSearchOpen} onOpenChange={setCommandSearchOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Command Center Navigation & Search</DialogTitle>
            <DialogDescription>
              Jump to an authorized governance module. Full record search across
              decisions and audit logs connects in Phase 9.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filter governance modules…"
                aria-label="Global module search input"
                className="pl-9"
              />
            </div>

            {visibleModules.length === 0 ? (
              <p className="py-4 text-center text-xs text-muted-foreground">
                No authorized governance modules match "{searchQuery}".
              </p>
            ) : (
              <ul className="max-h-60 divide-y divide-border/60 overflow-y-auto rounded-md border border-border">
                {visibleModules.map((mod) => {
                  const Icon = mod.icon;
                  return (
                    <li key={mod.id}>
                      <button
                        type="button"
                        onClick={() => {
                          setCommandSearchOpen(false);
                          setSearchQuery('');
                          navigate(mod.path);
                        }}
                        className="flex w-full items-center gap-3 px-3 py-2.5 text-left text-xs transition-colors hover:bg-accent"
                      >
                        <Icon className="h-4 w-4 shrink-0 text-primary" />
                        <div className="min-w-0 flex-1">
                          <p className="font-semibold text-foreground">
                            {mod.label}
                          </p>
                          <p className="truncate text-muted-foreground">
                            {mod.description}
                          </p>
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </header>
  );
}

