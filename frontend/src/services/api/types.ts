export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export interface RequestOptions {
  /** Query params, appended to the URL. Undefined values are skipped. */
  params?: Record<string, string | number | boolean | undefined>;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  /** Timeout in ms; ignored if `signal` is provided. Default 30000. */
  timeoutMs?: number;
  /** Skip attaching the Authorization header for this request. */
  skipAuth?: boolean;
}
