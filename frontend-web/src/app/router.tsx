import { Navigate, type RouteObject } from 'react-router-dom';
import { AppShellLayout } from '@/layouts/app-shell-layout';
import { ProtectedRoute } from '@/components/navigation/protected-route';
import {
  ForgotPasswordPagePlaceholder,
  LoginPagePlaceholder,
  RegisterPagePlaceholder,
} from '@/features/auth/auth-placeholders';
import {
  AgentDetailPlaceholderPage,
  AgentRegistryPlaceholderPage,
  AuditExplainabilityPlaceholderPage,
  BiasScannerPlaceholderPage,
  DashboardPlaceholderPage,
  DecisionWorkspacePlaceholderPage,
  DecisionsListPlaceholderPage,
  GovernanceConsolePlaceholderPage,
  InfluenceGraphPlaceholderPage,
  NotificationsPlaceholderPage,
  SettingsPlaceholderPage,
  UsersAndRolesPlaceholderPage,
  VotingMatrixPlaceholderPage,
} from '@/features/common/feature-placeholders';
import {
  NotFoundPage,
  UnauthorizedPage,
} from '@/features/common/system-pages';

export const appRoutes: RouteObject[] = [
  {
    path: '/',
    element: <Navigate to="/app/dashboard" replace />,
  },
  {
    path: '/login',
    element: <LoginPagePlaceholder />,
  },
  {
    path: '/register',
    element: <RegisterPagePlaceholder />,
  },
  {
    path: '/forgot-password',
    element: <ForgotPasswordPagePlaceholder />,
  },
  {
    path: '/app',
    element: (
      <ProtectedRoute>
        <AppShellLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <Navigate to="/app/dashboard" replace />,
      },
      {
        path: 'dashboard',
        element: (
          <ProtectedRoute requiredPermissions={['decisions:read']}>
            <DashboardPlaceholderPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'decisions',
        element: (
          <ProtectedRoute requiredPermissions={['decisions:read']}>
            <DecisionsListPlaceholderPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'decisions/:decisionId',
        element: (
          <ProtectedRoute requiredPermissions={['decisions:read']}>
            <DecisionWorkspacePlaceholderPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'agents',
        element: (
          <ProtectedRoute requiredPermissions={['agents:read']}>
            <AgentRegistryPlaceholderPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'agents/:agentId',
        element: (
          <ProtectedRoute requiredPermissions={['agents:read']}>
            <AgentDetailPlaceholderPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'voting',
        element: (
          <ProtectedRoute requiredPermissions={['voting:read']}>
            <VotingMatrixPlaceholderPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'influence',
        element: (
          <ProtectedRoute requiredPermissions={['agents:read']}>
            <InfluenceGraphPlaceholderPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'bias',
        element: (
          <ProtectedRoute requiredPermissions={['bias:read']}>
            <BiasScannerPlaceholderPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'governance',
        element: (
          <ProtectedRoute requiredPermissions={['governance:read']}>
            <GovernanceConsolePlaceholderPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'audit',
        element: (
          <ProtectedRoute requiredPermissions={['audit:read']}>
            <AuditExplainabilityPlaceholderPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'notifications',
        element: (
          <ProtectedRoute requiredPermissions={['notifications:read']}>
            <NotificationsPlaceholderPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'users',
        element: (
          <ProtectedRoute requiredPermissions={['users:read', 'roles:manage']}>
            <UsersAndRolesPlaceholderPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'roles',
        element: (
          <ProtectedRoute requiredPermissions={['roles:manage']}>
            <UsersAndRolesPlaceholderPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'settings',
        element: (
          <ProtectedRoute requiredPermissions={['system:configure']}>
            <SettingsPlaceholderPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'unauthorized',
        element: <UnauthorizedPage />,
      },
    ],
  },
  {
    path: '*',
    element: <NotFoundPage />,
  },
];

