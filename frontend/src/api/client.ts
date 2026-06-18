import { ngrokSkipHeaders } from '../lib/ngrok';
import { getApiBaseUrl } from './base-url';

const API_BASE = getApiBaseUrl();

function jsonApiHeaders(extra: Record<string, string> = {}): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    ...ngrokSkipHeaders(API_BASE),
    ...extra,
  };
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

const FIELD_LABELS: Record<string, string> = {
  email: 'Email',
  password: 'Password',
  sku: 'SKU',
  name: 'Name',
  unit: 'Unit',
  quantity: 'Quantity',
  unit_price: 'Unit price',
  total_cost: 'Total cost',
};

function messageFromValue(value: unknown): string | null {
  if (typeof value === 'string' && value.trim()) {
    return value.trim();
  }
  if (Array.isArray(value)) {
    const parts = value.filter(
      (item): item is string => typeof item === 'string' && item.trim().length > 0,
    );
    if (parts.length) {
      return parts.join(' ');
    }
  }
  return null;
}

/** Turn Django REST Framework error JSON into a single user-facing sentence. */
export function parseApiErrorBody(body: unknown): string | null {
  if (body == null) {
    return null;
  }
  if (typeof body === 'string') {
    const trimmed = body.trim();
    if (!trimmed) {
      return null;
    }
    if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
      try {
        return parseApiErrorBody(JSON.parse(trimmed));
      } catch {
        return trimmed;
      }
    }
    return trimmed;
  }
  if (typeof body !== 'object') {
    return null;
  }

  const obj = body as Record<string, unknown>;

  const detail = messageFromValue(obj.detail);
  if (detail) {
    return detail;
  }

  const nonField = messageFromValue(obj.non_field_errors);
  if (nonField) {
    return nonField;
  }

  const fieldMessages: string[] = [];
  for (const [key, value] of Object.entries(obj)) {
    if (key === 'detail' || key === 'non_field_errors') {
      continue;
    }
    const msg = messageFromValue(value);
    if (msg) {
      const label = FIELD_LABELS[key] ?? key.replace(/_/g, ' ');
      fieldMessages.push(`${label}: ${msg}`);
    }
  }
  if (fieldMessages.length) {
    return fieldMessages.join(' ');
  }

  return null;
}

export function formatError(err: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (err instanceof ApiError) {
    return (
      parseApiErrorBody(err.body) ??
      parseApiErrorBody(err.message) ??
      (err.message || fallback)
    );
  }
  if (err instanceof Error) {
    return parseApiErrorBody(err.message) ?? (err.message || fallback);
  }
  if (typeof err === 'string') {
    return parseApiErrorBody(err) ?? (err || fallback);
  }
  return fallback;
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
    const message =
      parseApiErrorBody(body) ?? (text || resp.statusText || `Request failed (${resp.status})`);
    throw new ApiError(message, resp.status, body);
  }

  return body as T;
}
