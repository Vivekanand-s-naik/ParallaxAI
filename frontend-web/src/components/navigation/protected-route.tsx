import * as React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { LoadingSkeleton } from '@/components/feedback/loading-skeleton';
import { useAuthStore } from '@/stores/auth-store';
import type { PermissionCode } from '@/types/auth';

export interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredPermissions?: PermissionCode[];
}

/**
 * Protected Route & Permission-Aware Route Guard:
 * 1. While session initialization is in progress, renders a skeleton state.
 * 2. If unauthenticated, redirects to /login while preserving the intended destination.
 * 3. If authenticated but lacking requiredPermissions, redirects to /app/unauthorized.
 */
export function ProtectedRoute({
  children,
  requiredPermissions = [],
}: ProtectedRouteProps) {
  const location = useLocation();
  const isInitialized = useAuthStore((s) => s.isInitialized);
  const isLoading = useAuthStore((s) => s.isLoading);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const permissionsLoaded = useAuthStore((s) => s.permissionsLoaded);
  const hasAnyPermission = useAuthStore((s) => s.hasAnyPermission);

  if (!isInitialized || isLoading) {
    return (
      <div
        data-testid="auth-initializing-state"
        className="min-h-screen bg-background p-8"
      >
        <LoadingSkeleton cards={3} rows={3} />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname }}
      />
    );
  }

  if (requiredPermissions.length > 0) {
    if (!permissionsLoaded) {
      return (
        <div
          data-testid="permissions-loading-state"
          className="p-6"
        >
          <LoadingSkeleton cards={2} rows={2} />
        </div>
      );
    }

    if (!hasAnyPermission(requiredPermissions)) {
      return <Navigate to="/app/unauthorized" replace />;
    }
  }

  return <>{children}</>;
}
