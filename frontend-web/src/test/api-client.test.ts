import type { AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { API_CONFIG } from '@/lib/api-config';
import {
  createApiClient,
  setOnUnauthorizedHandler,
} from '@/services/api-client';
import { ApiError } from '@/services/api-error';
import { useAuthStore } from '@/stores/auth-store';
import type { TokenResponse, UserAuth } from '@/types/auth';

const SAMPLE_USER: UserAuth = {
  id: '11111111-1111-1111-1111-111111111111',
  username: 'sarah.chen',
  email: 'sarah.chen@parallaxai.io',
  full_name: 'Dr. Sarah Chen',
  role: 'GOVERNANCE_OFFICER',
  roles: ['GOVERNANCE_OFFICER'],
  permissions: ['decisions:read', 'decisions:approve', 'governance:manage'],
  is_active: true,
  is_verified: true,
  auth_provider: 'local',
  preferences: {},
};

function makeAxiosResponse<T>(
  config: InternalAxiosRequestConfig,
  status: number,
  data: T
): AxiosResponse<T> {
  return {
    data,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    headers: {},
    config,
  };
}

function makeAxiosError(
  config: InternalAxiosRequestConfig,
  status: number,
  data: unknown
) {
  const err = new Error(`Request failed with status code ${status}`) as Error & {
    isAxiosError: boolean;
    config: InternalAxiosRequestConfig;
    response?: AxiosResponse;
  };
  err.isAxiosError = true;
  err.config = config;
  if (status > 0) {
    err.response = makeAxiosResponse(config, status, data);
  }
  return err;
}

describe('Centralized Axios API Client & Refresh Rotation', () => {
  beforeEach(() => {
    useAuthStore.getState().clearSession();
    setOnUnauthorizedHandler(null);
  });

  it('configures baseURL and attaches in-memory Bearer access token to requests', async () => {
    const client = createApiClient();
    expect(client.defaults.baseURL).toBe(API_CONFIG.baseUrl);
    expect(client.defaults.withCredentials).toBe(true);

    useAuthStore.getState().setSession(SAMPLE_USER, 'initial-jwt-access-token');

    let capturedAuthHeader: string | undefined;
    client.defaults.adapter = async (config: InternalAxiosRequestConfig) => {
      capturedAuthHeader = config.headers?.Authorization as string | undefined;
      return makeAxiosResponse(config, 200, { ok: true });
    };

    const res = await client.get('/decisions');
    expect(res.data).toEqual({ ok: true });
    expect(capturedAuthHeader).toBe('Bearer initial-jwt-access-token');
  });

  it('rotates refresh token once on 401 and shares a single refresh call across concurrent requests', async () => {
    const client = createApiClient();
    useAuthStore.getState().setSession(SAMPLE_USER, 'expired-access-token');

    let refreshCallCount = 0;
    const retriedAuthHeaders: string[] = [];

    client.defaults.adapter = async (config: InternalAxiosRequestConfig) => {
      if (config.url?.includes('/auth/refresh')) {
        refreshCallCount += 1;
        await new Promise((r) => setTimeout(r, 20));
        const tokenPayload: TokenResponse = {
          token: 'freshly-rotated-access-token',
          access_token: 'freshly-rotated-access-token',
          token_type: 'bearer',
          expires_in: 900,
          user: SAMPLE_USER,
        };
        return makeAxiosResponse(config, 200, tokenPayload);
      }

      const authHeader = config.headers?.Authorization as string | undefined;
      if (authHeader === 'Bearer expired-access-token') {
        throw makeAxiosError(config, 401, { detail: 'Token has expired' });
      }

      retriedAuthHeaders.push(authHeader ?? '');
      return makeAxiosResponse(config, 200, { url: config.url });
    };

    const [res1, res2, res3] = await Promise.all([
      client.get('/decisions'),
      client.get('/agents'),
      client.get('/governance/rules'),
    ]);

    expect(refreshCallCount).toBe(1);
    expect(res1.status).toBe(200);
    expect(res2.status).toBe(200);
    expect(res3.status).toBe(200);
    expect(retriedAuthHeaders).toEqual([
      'Bearer freshly-rotated-access-token',
      'Bearer freshly-rotated-access-token',
      'Bearer freshly-rotated-access-token',
    ]);
    expect(useAuthStore.getState().accessToken).toBe(
      'freshly-rotated-access-token'
    );
  });

  it('clears authentication state and invokes unauthorized handler when refresh fails', async () => {
    const client = createApiClient();
    useAuthStore.getState().setSession(SAMPLE_USER, 'expired-access-token');

    const onUnauthorized = vi.fn();
    setOnUnauthorizedHandler(onUnauthorized);

    client.defaults.adapter = async (config: InternalAxiosRequestConfig) => {
      if (config.url?.includes('/auth/refresh')) {
        throw makeAxiosError(config, 401, {
          detail: 'Refresh token expired or revoked',
        });
      }
      throw makeAxiosError(config, 401, { detail: 'Access token expired' });
    };

    await expect(client.get('/decisions')).rejects.toBeInstanceOf(ApiError);
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it('prevents infinite retry loops and normalizes network errors', async () => {
    const client = createApiClient();
    useAuthStore.getState().setSession(SAMPLE_USER, 'expired-access-token');

    let protectedCallCount = 0;
    client.defaults.adapter = async (config: InternalAxiosRequestConfig) => {
      if (config.url?.includes('/auth/refresh')) {
        const tokenPayload: TokenResponse = {
          token: 'still-unauthorized-token',
          access_token: 'still-unauthorized-token',
          token_type: 'bearer',
          expires_in: 900,
          user: SAMPLE_USER,
        };
        return makeAxiosResponse(config, 200, tokenPayload);
      }
      protectedCallCount += 1;
      throw makeAxiosError(config, 401, { detail: 'Still unauthorized' });
    };

    await expect(client.get('/decisions')).rejects.toBeInstanceOf(ApiError);
    // Original call + exactly 1 retry = 2 calls total (never an infinite loop)
    expect(protectedCallCount).toBe(2);

    // Network error normalization
    client.defaults.adapter = async (config: AxiosRequestConfig) => {
      throw makeAxiosError(
        config as InternalAxiosRequestConfig,
        0,
        undefined
      );
    };

    try {
      await client.get('/system/health');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.isNetworkError).toBe(true);
      expect(apiErr.status).toBe(0);
    }
  });
});

