import { ApiError } from './errors';
import type { HttpMethod, RequestOptions } from './types';

const DEFAULT_TIMEOUT_MS = 30_000;

type AuthTokenProvider = () => string | null;

/**
 * Thin fetch wrapper: one place for base URL, JSON (de)serialization,
 * auth header injection, timeouts, and error normalization into ApiError.
 * Feature modules build on top of this instead of calling fetch directly,
 * so every request gets the same error shape and auth handling.
 */
class ApiClient {
  private readonly baseUrl: string;
  private getAuthToken: AuthTokenProvider = () => null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
  }

  /** Wired up by the auth store at app startup — keeps this module free of a circular import. */
  setAuthTokenProvider(provider: AuthTokenProvider): void {
    this.getAuthToken = provider;
  }

  get<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('GET', path, undefined, options);
  }

  post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>('POST', path, body, options);
  }

  put<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>('PUT', path, body, options);
  }

  patch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>('PATCH', path, body, options);
  }

  delete<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('DELETE', path, undefined, options);
  }

  async request<T>(
    method: HttpMethod,
    path: string,
    body?: unknown,
    options: RequestOptions = {},
  ): Promise<T> {
    const url = this.buildUrl(path, options.params);
    const headers: Record<string, string> = {
      Accept: 'application/json',
      ...options.headers,
    };

    const isFormData = body instanceof FormData;
    if (body !== undefined && !isFormData) {
      headers['Content-Type'] = 'application/json';
    }

    if (!options.skipAuth) {
      const token = this.getAuthToken();
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }
    }

    const { signal, cleanup } = this.resolveSignal(options);

    let response: Response;
    try {
      response = await fetch(url, {
        method,
        headers,
        body:
          body === undefined
            ? undefined
            : isFormData
              ? body
              : JSON.stringify(body),
        signal,
      });
    } finally {
      cleanup();
    }

    return this.parseResponse<T>(response);
  }

  private resolveSignal(options: RequestOptions): {
    signal: AbortSignal;
    cleanup: () => void;
  } {
    if (options.signal) {
      // eslint-disable-next-line @typescript-eslint/no-empty-function -- caller owns cancellation
      return { signal: options.signal, cleanup: () => {} };
    }
    const controller = new AbortController();
    const timeout = setTimeout(
      () => controller.abort(),
      options.timeoutMs ?? DEFAULT_TIMEOUT_MS,
    );
    return { signal: controller.signal, cleanup: () => clearTimeout(timeout) };
  }

  private buildUrl(path: string, params?: RequestOptions['params']): string {
    const url = new URL(
      `${this.baseUrl}${path.startsWith('/') ? path : `/${path}`}`,
    );
    if (params) {
      for (const [key, value] of Object.entries(params)) {
        if (value !== undefined) {
          url.searchParams.set(key, String(value));
        }
      }
    }
    return url.toString();
  }

  private async parseResponse<T>(response: Response): Promise<T> {
    const contentType = response.headers.get('content-type') ?? '';
    const isJson = contentType.includes('application/json');
    const payload: unknown = isJson
      ? await response.json().catch(() => null)
      : await response.text().catch(() => null);

    if (!response.ok) {
      const body: Record<string, unknown> =
        isJson && payload !== null && typeof payload === 'object'
          ? (payload as Record<string, unknown>)
          : {};
      const bodyMessage = typeof body.message === 'string' ? body.message : '';
      const message =
        bodyMessage.length > 0
          ? bodyMessage
          : response.statusText.length > 0
            ? response.statusText
            : 'Request failed';
      throw new ApiError(response.status, {
        message,
        code: typeof body.code === 'string' ? body.code : undefined,
        details: body.details,
      });
    }

    return payload as T;
  }
}

export const apiClient = new ApiClient(import.meta.env.VITE_API_URL);
export { ApiClient };
