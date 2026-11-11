import axios from 'axios';

export class ApiError extends Error {
  public readonly status: number;
  public readonly code: string;
  public readonly retryAfter?: number;
  public readonly isNetworkError: boolean;

  constructor(params: {
    message: string;
    status: number;
    code?: string;
    retryAfter?: number;
    isNetworkError?: boolean;
  }) {
    super(params.message);
    this.name = 'ApiError';
    this.status = params.status;
    this.code = params.code ?? 'api_error';
    this.retryAfter = params.retryAfter;
    this.isNetworkError = params.isNetworkError ?? false;
  }
}

export function normalizeApiError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error;
  }

  if (axios.isAxiosError(error)) {
    const status = error.response?.status ?? 0;
    const data = error.response?.data as
      | {
          detail?: string | Array<{ msg?: string; loc?: Array<string | number> }>;
          error?: string;
          retry_after?: number;
        }
      | undefined;

    const retryHeader = error.response?.headers?.['retry-after'];
    const retryAfter =
      data?.retry_after ??
      (retryHeader ? Number.parseInt(String(retryHeader), 10) : undefined);

    if (!error.response) {
      return new ApiError({
        message:
          'Unable to reach the ParallaxAI governance server. Check your network connection or service status.',
        status: 0,
        code: 'network_error',
        isNetworkError: true,
      });
    }

    let message = 'An unexpected error occurred while processing the request.';
    if (typeof data?.detail === 'string') {
      message = data.detail;
    } else if (Array.isArray(data?.detail) && data.detail.length > 0) {
      message = data.detail
        .map((item) => item.msg || 'Validation error')
        .join('; ');
    } else if (status === 401) {
      message = 'Authentication is required or your session has expired.';
    } else if (status === 403) {
      message = 'You do not have sufficient governance permissions for this action.';
    } else if (status === 404) {
      message = 'The requested governance resource was not found.';
    } else if (status === 429) {
      message = `Rate limit exceeded. Please wait ${retryAfter ?? 60} seconds before retrying.`;
    }

    return new ApiError({
      message,
      status,
      code: data?.error ?? `http_${status}`,
      retryAfter: Number.isNaN(retryAfter) ? undefined : retryAfter,
      isNetworkError: false,
    });
  }

  if (error instanceof Error) {
    return new ApiError({
      message: error.message,
      status: 500,
      code: 'client_error',
    });
  }

  return new ApiError({
    message: 'An unknown error occurred.',
    status: 500,
    code: 'unknown_error',
  });
}
