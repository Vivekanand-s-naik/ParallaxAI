import { Navigate, type RouteObject } from 'react-router-dom';
import { AppShellLayout } from '@/layouts/app-shell-layout';
import { ProtectedRoute } from '@/components/navigation/protected-route';
import { LoginPage } from '@/features/auth/login-page';
import { RegisterPage } from '@/features/auth/register-page';
import { ForgotPasswordPage } from '@/features/auth/forgot-password-page';
import { CommandCenterPage } from '@/features/dashboard/command-center-page';
import { DecisionsListPage } from '@/features/decisions/decisions-list-page';
import { DecisionWorkspacePage } from '@/features/decisions/decision-workspace-page';
import {
  AgentDetailPlaceholderPage,
  AgentRegistryPlaceholderPage,
  AuditExplainabilityPlaceholderPage,
  BiasScannerPlaceholderPage,
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
    element: <LoginPage />,
  },
  {
    path: '/register',
    element: <RegisterPage />,
  },
  {
    path: '/forgot-password',
    element: <ForgotPasswordPage />,
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
            <CommandCenterPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'decisions',
        element: (
          <ProtectedRoute requiredPermissions={['decisions:read']}>
            <DecisionsListPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'decisions/:decisionId',
        element: (
          <ProtectedRoute requiredPermissions={['decisions:read']}>
            <DecisionWorkspacePage />
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

