import { getApiBaseUrl } from './base-url';

const API_BASE = getApiBaseUrl();

export function jsonApiHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...extra,
  };
  if (API_BASE.includes('ngrok-free.app') || API_BASE.includes('ngrok-free.dev')) {
    headers['ngrok-skip-browser-warning'] = 'true';
  }
  return headers;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly body: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { accessToken?: string | null } = {},
): Promise<T> {
  const { accessToken, headers, ...rest } = options;
  let resp: Response;
  try {
    resp = await fetch(`${API_BASE}${path}`, {
      ...rest,
      headers: jsonApiHeaders({
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...(headers as Record<string, string> | undefined),
      }),
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Network request failed';
    throw new Error(msg);
  }

  const text = await resp.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }

  if (!resp.ok) {
    const detail =
      typeof body === 'object' && body && 'detail' in body
        ? String((body as { detail: unknown }).detail)
        : text || resp.statusText;
    throw new ApiError(detail, resp.status, body);
  }

  return body as T;
}
