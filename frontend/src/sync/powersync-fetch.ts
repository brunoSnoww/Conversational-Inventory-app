import type { FetchImplementation } from '@powersync/common';

import { getApiBaseUrl } from '../api/base-url';
import { isNgrokHost, ngrokSkipHeaders } from '../lib/ngrok';

function resolveUrl(input: RequestInfo | URL): string {
  if (typeof input === 'string') {
    return input;
  }
  if (input instanceof URL) {
    return input.href;
  }
  return input.url;
}

/** Route write-checkpoint through Django /api so Vercel gets CORS + ngrok skip on /api paths. */
export function createPowerSyncFetch(): FetchImplementation {
  const fetchImpl: FetchImplementation = async (
    input: RequestInfo | URL,
    init?: RequestInit,
  ) => {
    const originalUrl = resolveUrl(input);
    let url = originalUrl;
    let headers = new Headers(init?.headers);

    if (originalUrl.includes('/write-checkpoint2.json') && isNgrokHost(originalUrl)) {
      const clientId = new URL(originalUrl).searchParams.get('client_id') ?? '';
      url = `${getApiBaseUrl()}/api/sync/write-checkpoint/?client_id=${encodeURIComponent(clientId)}`;
      headers = new Headers(init?.headers);
      headers.delete('x-user-agent');
      Object.entries(ngrokSkipHeaders(url)).forEach(([key, value]) => headers.set(key, value));
    }

    return fetch(url, { ...init, headers });
  };
  return fetchImpl;
}
