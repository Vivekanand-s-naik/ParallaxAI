import axios, {
  type AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from 'axios';
import { API_CONFIG } from '@/lib/api-config';
import { useAuthStore } from '@/stores/auth-store';
import type { TokenResponse } from '@/types/auth';
import { normalizeApiError } from './api-error';

export interface RetryableRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

const AUTH_EXEMPT_PATHS = [
  '/auth/login',
  '/auth/register',
  '/auth/refresh',
  '/auth/logout',
  '/auth/forgot-password',
  '/auth/reset-password',
  '/auth/providers',
  '/auth/google/login',
  '/auth/google/callback',
];

function isExemptAuthEndpoint(url?: string): boolean {
  if (!url) return false;
  return AUTH_EXEMPT_PATHS.some((exempt) => url.includes(exempt));
}

type UnauthorizedHandler = () => void;
let onUnauthorizedCallback: UnauthorizedHandler | null = null;

export function setOnUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  onUnauthorizedCallback = handler;
}

/**
 * Single-flight refresh promise shared across concurrent 401 responses.
 */
let activeRefreshPromise: Promise<TokenResponse> | null = null;

export function createApiClient(baseURL: string = API_CONFIG.baseUrl): AxiosInstance {
  const client = axios.create({
    baseURL,
    timeout: API_CONFIG.timeoutMs,
    withCredentials: true, // Required so browser sends/receives HttpOnly refresh cookie
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
  });

  // Request Interceptor: Attach in-memory JWT access token
  client.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      const token = useAuthStore.getState().accessToken;
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error: unknown) => Promise.reject(normalizeApiError(error))
  );

  // Response Interceptor: Handle 401 with single-flight refresh token rotation
  client.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const originalRequest = error.config as RetryableRequestConfig | undefined;
      const status = error.response?.status;

      if (
        status === 401 &&
        originalRequest &&
        !originalRequest._retry &&
        !isExemptAuthEndpoint(originalRequest.url)
      ) {
        originalRequest._retry = true;

        try {
          if (!activeRefreshPromise) {
            activeRefreshPromise = client
              .post<TokenResponse>('/auth/refresh', {})
              .then((res) => res.data)
              .finally(() => {
                activeRefreshPromise = null;
              });
          }

          const tokenData = await activeRefreshPromise;
          useAuthStore
            .getState()
            .setSession(tokenData.user, tokenData.access_token);

          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${tokenData.access_token}`;
          }
          return client(originalRequest);
        } catch (refreshError) {
          useAuthStore.getState().clearSession();
          if (onUnauthorizedCallback) {
            onUnauthorizedCallback();
          }
          return Promise.reject(normalizeApiError(refreshError));
        }
      }

      return Promise.reject(normalizeApiError(error));
    }
  );

  return client;
}

export const apiClient = createApiClient();
