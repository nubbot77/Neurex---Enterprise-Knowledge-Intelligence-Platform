import type { ApiErrorBody } from '@/types/api';

/** Thrown for any non-2xx response or network/parse failure from ApiClient. */
export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly details?: unknown;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = 'ApiError';
    this.status = status;
    this.code = body.code;
    this.details = body.details;
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  get isForbidden(): boolean {
    return this.status === 403;
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  get isValidation(): boolean {
    return this.status === 422;
  }

  get isServerError(): boolean {
    return this.status >= 500;
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

/** Best-effort human message for any thrown value, safe to show in UI. */
export function toUserMessage(error: unknown): string {
  if (isApiError(error)) {
    return error.message;
  }
  if (error instanceof DOMException && error.name === 'AbortError') {
    return 'Request timed out. Please try again.';
  }
  if (error instanceof TypeError) {
    return 'Network error. Check your connection and try again.';
  }
  return 'Something went wrong. Please try again.';
}
