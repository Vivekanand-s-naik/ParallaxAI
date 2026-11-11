import { Navigate, type RouteObject } from 'react-router-dom';
import { AppShellLayout } from '@/layouts/app-shell-layout';
import { ProtectedRoute } from '@/components/navigation/protected-route';
import { LoginPage } from '@/features/auth/login-page';
import { RegisterPage } from '@/features/auth/register-page';
import { ForgotPasswordPage } from '@/features/auth/forgot-password-page';
import { CommandCenterPage } from '@/features/dashboard/command-center-page';
import { DecisionsListPage } from '@/features/decisions/decisions-list-page';
import { DecisionWorkspacePage } from '@/features/decisions/decision-workspace-page';
import { AgentRegistryPage } from '@/features/agents/agent-registry-page';
import { AgentDetailPage } from '@/features/agents/agent-detail-page';
import { MultiAgentVotingPage } from '@/features/voting/multi-agent-voting-page';
import { InfluenceGraphPage } from '@/features/influence/influence-graph-page';
import { BiasScannerPage } from '@/features/bias/bias-scanner-page';
import { GovernanceConsolePage } from '@/features/governance/governance-console-page';
import { AuditExplainabilityPage } from '@/features/audit/audit-explainability-page';
import { NotificationsPage } from '@/features/notifications/notifications-page';
import { UsersAndRolesPage } from '@/features/administration/users-roles-page';
import { SystemSettingsPage } from '@/features/administration/system-settings-page';
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
            <AgentRegistryPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'agents/:agentId',
        element: (
          <ProtectedRoute requiredPermissions={['agents:read']}>
            <AgentDetailPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'voting',
        element: (
          <ProtectedRoute requiredPermissions={['voting:read']}>
            <MultiAgentVotingPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'influence',
        element: (
          <ProtectedRoute requiredPermissions={['agents:read']}>
            <InfluenceGraphPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'bias',
        element: (
          <ProtectedRoute requiredPermissions={['bias:read']}>
            <BiasScannerPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'governance',
        element: (
          <ProtectedRoute requiredPermissions={['governance:read']}>
            <GovernanceConsolePage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'audit',
        element: (
          <ProtectedRoute requiredPermissions={['audit:read']}>
            <AuditExplainabilityPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'notifications',
        element: (
          <ProtectedRoute requiredPermissions={['notifications:read']}>
            <NotificationsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'users',
        element: (
          <ProtectedRoute requiredPermissions={['users:read', 'roles:manage']}>
            <UsersAndRolesPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'roles',
        element: (
          <ProtectedRoute requiredPermissions={['roles:manage']}>
            <UsersAndRolesPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'settings',
        element: (
          <ProtectedRoute requiredPermissions={['system:configure']}>
            <SystemSettingsPage />
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
