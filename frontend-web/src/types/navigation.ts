import type { LucideIcon } from 'lucide-react';
import type { PermissionCode } from './auth';

export type NavigationGroupKey =
  | 'OVERVIEW'
  | 'INTELLIGENCE'
  | 'GOVERNANCE'
  | 'ADMINISTRATION';

export interface NavigationItem {
  id: string;
  label: string;
  path: string;
  icon: LucideIcon;
  group: NavigationGroupKey;
  /**
   * Required permissions (user needs at least one of these permissions to see the item).
   * Empty array means accessible to any authenticated user.
   */
  requiredPermissions: PermissionCode[];
  badge?: string;
  description: string;
}

export interface RouteBreadcrumbMeta {
  title: string;
  parentPath?: string;
  section?: NavigationGroupKey;
}

export type WebSocketConnectionState =
  | 'connected'
  | 'connecting'
  | 'reconnecting'
  | 'disconnected'
  | 'unavailable';

