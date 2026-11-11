import * as React from 'react';
import { useAuthStore } from '@/stores/auth-store';
import type { PermissionCode } from '@/types/auth';

export interface PermissionGateProps {
  permissions: PermissionCode[];
  requireAll?: boolean;
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

export function PermissionGate({
  permissions,
  requireAll = false,
  fallback = null,
  children,
}: PermissionGateProps) {
  const permissionsLoaded = useAuthStore((s) => s.permissionsLoaded);
  const hasAnyPermission = useAuthStore((s) => s.hasAnyPermission);
  const hasAllPermissions = useAuthStore((s) => s.hasAllPermissions);

  if (!permissionsLoaded) return null;

  const allowed = requireAll
    ? hasAllPermissions(permissions)
    : hasAnyPermission(permissions);

  if (!allowed) return <>{fallback}</>;
  return <>{children}</>;
}
