import { create } from 'zustand';
import type { PermissionCode, SystemRoleName, UserAuth } from '@/types/auth';

/**
 * Auth Store:
 * Holds the authenticated user profile, permissions, and short-lived JWT access token IN MEMORY ONLY.
 * Sensitive access and refresh tokens are NEVER persisted to localStorage or sessionStorage.
 */
interface AuthState {
  user: UserAuth | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isInitialized: boolean;
  isLoading: boolean;
  permissionsLoaded: boolean;
  setSession: (user: UserAuth, accessToken: string) => void;
  setUser: (user: UserAuth) => void;
  setAccessToken: (accessToken: string | null) => void;
  clearSession: () => void;
  setInitialized: (initialized: boolean) => void;
  setLoading: (loading: boolean) => void;
  hasPermission: (permission: PermissionCode) => boolean;
  hasAnyPermission: (permissions: PermissionCode[]) => boolean;
  hasAllPermissions: (permissions: PermissionCode[]) => boolean;
  hasRole: (role: SystemRoleName) => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,
  isInitialized: false,
  isLoading: false,
  permissionsLoaded: false,

  setSession: (user, accessToken) =>
    set({
      user,
      accessToken,
      isAuthenticated: true,
      isInitialized: true,
      isLoading: false,
      permissionsLoaded: Array.isArray(user.permissions),
    }),

  setUser: (user) =>
    set({
      user,
      isAuthenticated: true,
      permissionsLoaded: Array.isArray(user.permissions),
    }),

  setAccessToken: (accessToken) =>
    set((state) => ({
      accessToken,
      isAuthenticated: Boolean(accessToken && state.user),
    })),

  clearSession: () =>
    set({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isLoading: false,
      permissionsLoaded: false,
    }),

  setInitialized: (isInitialized) => set({ isInitialized }),

  setLoading: (isLoading) => set({ isLoading }),

  hasPermission: (permission) => {
    const { user, isAuthenticated, permissionsLoaded } = get();
    if (!isAuthenticated || !permissionsLoaded || !user) return false;
    if (user.roles?.includes('SUPER_ADMIN')) return true;
    return user.permissions?.includes(permission) ?? false;
  },

  hasAnyPermission: (permissions) => {
    const { user, isAuthenticated, permissionsLoaded } = get();
    if (permissions.length === 0) return isAuthenticated;
    if (!isAuthenticated || !permissionsLoaded || !user) return false;
    if (user.roles?.includes('SUPER_ADMIN')) return true;
    return permissions.some((p) => user.permissions?.includes(p));
  },

  hasAllPermissions: (permissions) => {
    const { user, isAuthenticated, permissionsLoaded } = get();
    if (permissions.length === 0) return isAuthenticated;
    if (!isAuthenticated || !permissionsLoaded || !user) return false;
    if (user.roles?.includes('SUPER_ADMIN')) return true;
    return permissions.every((p) => user.permissions?.includes(p));
  },

  hasRole: (role) => {
    const { user, isAuthenticated } = get();
    if (!isAuthenticated || !user) return false;
    return user.role === role || (user.roles?.includes(role) ?? false);
  },
}));

