/**
 * TypeScript contracts matching the FastAPI backend authentication & RBAC schemas:
 * - backend/schemas/auth.py
 * - backend/database/seed.py (19 permissions, 6 system roles)
 */

export type SystemRoleName =
  | 'SUPER_ADMIN'
  | 'ADMIN'
  | 'GOVERNANCE_OFFICER'
  | 'HUMAN_REVIEWER'
  | 'ANALYST'
  | 'VIEWER'
  | (string & {});

export type PermissionCode =
  | 'decisions:read'
  | 'decisions:create'
  | 'decisions:update'
  | 'decisions:approve'
  | 'decisions:reject'
  | 'decisions:escalate'
  | 'decisions:manage'
  | 'agents:read'
  | 'agents:manage'
  | 'voting:read'
  | 'voting:participate'
  | 'governance:read'
  | 'governance:manage'
  | 'bias:read'
  | 'audit:read'
  | 'notifications:read'
  | 'users:read'
  | 'users:manage'
  | 'roles:manage'
  | 'system:configure'
  | (string & {});

export interface UserAuth {
  id: string;
  username?: string | null;
  email: string;
  full_name: string;
  role: SystemRoleName;
  roles: SystemRoleName[];
  permissions: PermissionCode[];
  is_active: boolean;
  is_verified: boolean;
  auth_provider: string;
  preferences: Record<string, unknown>;
  last_login_at?: string | null;
  created_at?: string | null;
}

export interface TokenResponse {
  token: string;
  access_token: string;
  refresh_token?: string | null;
  token_type: string;
  expires_in: number;
  user: UserAuth;
}

export interface LoginPayload {
  email?: string;
  username?: string;
  identifier?: string;
  password: string;
  remember_me?: boolean;
}

export interface RegisterPayload {
  full_name: string;
  email: string;
  password: string;
  confirm_password?: string;
  accept_terms: boolean;
  username?: string;
}

export interface ForgotPasswordPayload {
  email: string;
}

export interface ForgotPasswordResponse {
  status: string;
  email_provider_configured: boolean;
  message: string;
}

export interface AuthProvidersStatus {
  local_enabled: boolean;
  google_oauth_enabled: boolean;
  google_oauth_message: string;
  password_reset_email_enabled: boolean;
  password_reset_message: string;
}
