import { render, screen } from '@testing-library/react';
import { MemoryRouter, useRoutes } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { AppProviders } from '@/app/providers';
import { appRoutes } from '@/app/router';
import { useAuthStore } from '@/stores/auth-store';
import type { UserAuth } from '@/types/auth';

function TestRouterApp({ initialEntries }: { initialEntries: string[] }) {
  return (
    <AppProviders>
      <MemoryRouter initialEntries={initialEntries}>
        <RoutesContent />
      </MemoryRouter>
    </AppProviders>
  );
}

function RoutesContent() {
  return useRoutes(appRoutes);
}

const VIEWER_USER: UserAuth = {
  id: '00000000-0000-0000-0000-000000000001',
  username: 'viewer',
  email: 'viewer@parallaxai.io',
  full_name: 'Viewer Operator',
  role: 'VIEWER',
  roles: ['VIEWER'],
  permissions: ['decisions:read', 'agents:read'],
  is_active: true,
  is_verified: true,
  auth_provider: 'local',
  preferences: {},
};

describe('Application Routing & Permission Guards', () => {
  beforeEach(() => {
    useAuthStore.getState().clearSession();
    useAuthStore.getState().setInitialized(true);
  });

  it('redirects unauthenticated users from protected routes to /login', () => {
    render(<TestRouterApp initialEntries={['/app/dashboard']} />);
    expect(screen.getByText('Operator Sign In')).toBeInTheDocument();
  });

  it('renders loading skeleton while authentication initialization is in progress', () => {
    useAuthStore.setState({
      isInitialized: false,
      isLoading: true,
    });
    render(<TestRouterApp initialEntries={['/app/dashboard']} />);
    expect(screen.getByTestId('auth-initializing-state')).toBeInTheDocument();
  });

  it('renders authorized routes for authenticated users with matching permissions', () => {
    useAuthStore.getState().setSession(VIEWER_USER, 'valid-jwt');
    render(<TestRouterApp initialEntries={['/app/decisions/dec-9988']} />);
    expect(
      screen.getByRole('heading', { name: /Decision Workspace — dec-9988/i })
    ).toBeInTheDocument();
  });

  it('redirects authenticated users lacking required route permissions to /app/unauthorized', () => {
    useAuthStore.getState().setSession(VIEWER_USER, 'valid-jwt');
    render(<TestRouterApp initialEntries={['/app/users']} />);
    expect(screen.getByTestId('unauthorized-page')).toBeInTheDocument();
    expect(
      screen.getByText('Insufficient Governance Permissions')
    ).toBeInTheDocument();
  });

  it('renders NotFoundPage for unknown routes', () => {
    useAuthStore.getState().setSession(VIEWER_USER, 'valid-jwt');
    render(
      <TestRouterApp initialEntries={['/non-existent-governance-path']} />
    );
    expect(screen.getByTestId('not-found-page')).toBeInTheDocument();
    expect(
      screen.getByText('Requested Governance Route Does Not Exist')
    ).toBeInTheDocument();
  });
});

