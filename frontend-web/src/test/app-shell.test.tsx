import { act, render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { AppSidebar } from '@/components/navigation/app-sidebar';
import { AppTopbar } from '@/components/navigation/app-topbar';
import { generateBreadcrumbs } from '@/lib/navigation-config';
import { useAuthStore } from '@/stores/auth-store';
import { useUiStore } from '@/stores/ui-store';
import type { UserAuth } from '@/types/auth';

const VIEWER_USER: UserAuth = {
  id: '00000000-0000-0000-0000-000000000001',
  username: 'viewer_op',
  email: 'viewer@parallaxai.io',
  full_name: 'Elena Rostova',
  role: 'VIEWER',
  roles: ['VIEWER'],
  permissions: [
    'decisions:read',
    'agents:read',
    'voting:read',
    'governance:read',
    'bias:read',
    'notifications:read',
  ],
  is_active: true,
  is_verified: true,
  auth_provider: 'local',
  preferences: {},
};

const SUPER_ADMIN_USER: UserAuth = {
  ...VIEWER_USER,
  id: '00000000-0000-0000-0000-000000000099',
  username: 'admin',
  email: 'admin@parallaxai.io',
  full_name: 'Marcus Vance',
  role: 'SUPER_ADMIN',
  roles: ['SUPER_ADMIN'],
  permissions: [
    'decisions:read',
    'decisions:create',
    'decisions:update',
    'decisions:approve',
    'decisions:reject',
    'decisions:escalate',
    'decisions:manage',
    'agents:read',
    'agents:manage',
    'voting:read',
    'voting:participate',
    'governance:read',
    'governance:manage',
    'bias:read',
    'audit:read',
    'notifications:read',
    'users:read',
    'users:manage',
    'roles:manage',
    'system:configure',
  ],
};

describe('AppSidebar & AppTopbar Shell Components', () => {
  beforeEach(() => {
    useUiStore.setState({
      isSidebarCollapsed: false,
      isMobileSidebarOpen: false,
      isCommandSearchOpen: false,
      isRightPanelOpen: false,
      wsConnectionState: 'disconnected',
      toasts: [],
    });
    useAuthStore.getState().clearSession();
  });

  it('does not expose privileged navigation items before permissions have loaded', () => {
    useAuthStore.setState({
      user: null,
      accessToken: null,
      isAuthenticated: true,
      isInitialized: true,
      isLoading: false,
      permissionsLoaded: false,
    });

    render(
      <MemoryRouter initialEntries={['/app/dashboard']}>
        <AppSidebar />
      </MemoryRouter>
    );

    expect(
      screen.getByTestId('sidebar-permissions-loading')
    ).toBeInTheDocument();
    expect(screen.queryByText('Users & Roles')).not.toBeInTheDocument();
    expect(screen.queryByText('Settings')).not.toBeInTheDocument();
  });

  it('filters sidebar navigation items based on loaded user permissions (VIEWER vs SUPER_ADMIN)', () => {
    useAuthStore.getState().setSession(VIEWER_USER, 'test-token');

    const { rerender } = render(
      <MemoryRouter initialEntries={['/app/decisions']}>
        <AppSidebar />
      </MemoryRouter>
    );

    // VIEWER sees permitted read modules
    expect(screen.getByText('Command Center')).toBeInTheDocument();
    expect(screen.getByText('Decisions')).toBeInTheDocument();
    expect(screen.getByText('Agent Registry')).toBeInTheDocument();
    expect(screen.getByText('Bias & Fairness')).toBeInTheDocument();

    // VIEWER does NOT see Audit & Explainability, Users & Roles, or Settings
    expect(
      screen.queryByText('Audit & Explainability')
    ).not.toBeInTheDocument();
    expect(screen.queryByText('Users & Roles')).not.toBeInTheDocument();
    expect(screen.queryByText('Settings')).not.toBeInTheDocument();

    // Active route highlighting on /app/decisions
    const decisionsLink = screen.getByRole('link', { name: /decisions/i });
    expect(decisionsLink.className).toContain('border-primary');

    // Upgrade to SUPER_ADMIN -> sees all navigation items
    act(() => {
      useAuthStore.getState().setSession(SUPER_ADMIN_USER, 'admin-token');
    });
    rerender(
      <MemoryRouter initialEntries={['/app/decisions']}>
        <AppSidebar />
      </MemoryRouter>
    );

    expect(screen.getByText('Audit & Explainability')).toBeInTheDocument();
    expect(screen.getByText('Users & Roles')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('toggles sidebar between expanded and collapsed states and supports mobile drawer', () => {
    useAuthStore.getState().setSession(SUPER_ADMIN_USER, 'admin-token');

    render(
      <MemoryRouter initialEntries={['/app/dashboard']}>
        <AppSidebar />
      </MemoryRouter>
    );

    const desktopSidebar = screen.getByTestId('desktop-sidebar');
    expect(desktopSidebar).toHaveAttribute('data-collapsed', 'false');

    const collapseBtn = screen.getByRole('button', {
      name: /collapse sidebar navigation/i,
    });
    fireEvent.click(collapseBtn);

    expect(desktopSidebar).toHaveAttribute('data-collapsed', 'true');

    const expandBtn = screen.getByRole('button', {
      name: /expand sidebar navigation/i,
    });
    fireEvent.click(expandBtn);
    expect(desktopSidebar).toHaveAttribute('data-collapsed', 'false');

    // Open mobile navigation drawer on the already-rendered AppSidebar
    act(() => {
      useUiStore.getState().setMobileSidebarOpen(true);
    });
    expect(screen.getByTestId('mobile-sidebar-drawer')).toBeInTheDocument();

    // Close mobile navigation drawer
    const closeBtn = screen.getByRole('button', {
      name: /close navigation drawer/i,
    });
    fireEvent.click(closeBtn);
    expect(
      screen.queryByTestId('mobile-sidebar-drawer')
    ).not.toBeInTheDocument();
  });

  it('generates structured breadcrumbs and renders honest WebSocket status, notifications, and user menu', () => {
    useAuthStore.getState().setSession(SUPER_ADMIN_USER, 'admin-token');

    const crumbs = generateBreadcrumbs('/app/decisions/9f8e7d6c-1234');
    expect(crumbs).toEqual([
      { label: 'Command Center', path: '/app/dashboard', isCurrent: false },
      { label: 'Decisions', path: '/app/decisions', isCurrent: false },
      {
        label: 'Decision 9f8e7d6c',
        path: '/app/decisions/9f8e7d6c-1234',
        isCurrent: true,
      },
    ]);

    render(
      <MemoryRouter initialEntries={['/app/decisions/9f8e7d6c-1234']}>
        <AppTopbar notifications={[]} unreadCount={0} />
      </MemoryRouter>
    );

    // Breadcrumb rendered in Topbar
    expect(screen.getByText('Decision 9f8e7d6c')).toHaveAttribute(
      'aria-current',
      'page'
    );

    // Honest WebSocket connection indicator defaults to disconnected (not fake connected)
    const wsIndicator = screen.getByTestId('ws-status-indicator');
    expect(wsIndicator).toHaveAttribute('data-ws-state', 'disconnected');
    expect(wsIndicator).toHaveTextContent('WS Disconnected');

    // Update WS state to connected and verify indicator updates honestly
    act(() => {
      useUiStore.getState().setWsConnectionState('connected');
    });
    expect(wsIndicator).toHaveAttribute('data-ws-state', 'connected');
    expect(wsIndicator).toHaveTextContent('WS Connected');

    // Open notifications dropdown -> shows honest empty state
    const notifBtn = screen.getByRole('button', { name: 'Notifications' });
    fireEvent.click(notifBtn);
    expect(screen.getByTestId('notifications-dropdown')).toHaveTextContent(
      /no active governance notifications/i
    );

    // Open user profile menu -> shows full name, email, and role
    const userMenuBtn = screen.getByRole('button', {
      name: /user profile menu/i,
    });
    fireEvent.click(userMenuBtn);
    const dropdown = screen.getByTestId('user-profile-dropdown');
    expect(dropdown).toHaveTextContent('Marcus Vance');
    expect(dropdown).toHaveTextContent('admin@parallaxai.io');
    expect(dropdown).toHaveTextContent('SUPER_ADMIN');
  });
});
