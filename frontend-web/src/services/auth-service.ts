import { apiClient } from './api-client';
import { useAuthStore } from '@/stores/auth-store';
import type {
  AuthProvidersStatus,
  ForgotPasswordPayload,
  ForgotPasswordResponse,
  LoginPayload,
  RegisterPayload,
  TokenResponse,
  UserAuth,
} from '@/types/auth';

/**
 * Authentication Service aligned with FastAPI /api/v1/auth/* endpoints.
 */
export const authService = {
  async getProvidersStatus(): Promise<AuthProvidersStatus> {
    const { data } = await apiClient.get<AuthProvidersStatus>('/auth/providers');
    return data;
  },

  async login(payload: LoginPayload): Promise<TokenResponse> {
    const { data } = await apiClient.post<TokenResponse>('/auth/login', payload);
    useAuthStore.getState().setSession(data.user, data.access_token);
    return data;
  },

  async register(payload: RegisterPayload): Promise<TokenResponse> {
    const { data } = await apiClient.post<TokenResponse>('/auth/register', payload);
    useAuthStore.getState().setSession(data.user, data.access_token);
    return data;
  },

  async refreshSession(): Promise<TokenResponse> {
    const { data } = await apiClient.post<TokenResponse>('/auth/refresh', {});
    useAuthStore.getState().setSession(data.user, data.access_token);
    return data;
  },

  async getCurrentUser(): Promise<UserAuth> {
    const { data } = await apiClient.get<UserAuth>('/auth/me');
    useAuthStore.getState().setUser(data);
    return data;
  },

  async logout(): Promise<void> {
    try {
      await apiClient.post('/auth/logout', {});
    } finally {
      useAuthStore.getState().clearSession();
    }
  },

  async forgotPassword(payload: ForgotPasswordPayload): Promise<ForgotPasswordResponse> {
    const { data } = await apiClient.post<ForgotPasswordResponse>(
      '/auth/forgot-password',
      payload
    );
    return data;
  },

  async resetPassword(payload: {
    token: string;
    new_password: string;
    confirm_password?: string;
  }): Promise<{ message: string }> {
    const { data } = await apiClient.post<{ message: string }>(
      '/auth/reset-password',
      payload
    );
    return data;
  },

  async initiateGoogleOAuth(redirectUri?: string): Promise<{
    authorization_url: string;
    state: string;
    redirect_uri: string;
  }> {
    const { data } = await apiClient.get<{
      authorization_url: string;
      state: string;
      redirect_uri: string;
    }>('/auth/google/login', {
      params: redirectUri ? { redirect_uri: redirectUri } : undefined,
    });
    return data;
  },

  async bootstrapSession(): Promise<boolean> {
    const store = useAuthStore.getState();
    store.setLoading(true);
    try {
      await authService.refreshSession();
      return true;
    } catch {
      store.clearSession();
      return false;
    } finally {
      store.setInitialized(true);
      store.setLoading(false);
    }
  },
};

