import type { AbstractPowerSyncDatabase, PowerSyncBackendConnector } from '@powersync/web';
import type { FetchImplementation } from '@powersync/common';

import { apiFetch } from '../api/client';
import { getApiBaseUrl } from '../api/base-url';
import { isNgrokHost, ngrokSkipHeaders } from '../lib/ngrok';
import { syncLog } from './logger';

export type AccessTokenProvider = () => string | null;

function resolveFetchUrl(input: RequestInfo | URL): string {
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
  const fetchImpl: FetchImplementation = async (input: RequestInfo | URL, init?: RequestInit) => {
    const originalUrl = resolveFetchUrl(input);
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

/** PowerSync hybrid connector: token + chat upload mutations via Django REST. */
export class InventoryConnector implements PowerSyncBackendConnector {
  constructor(private readonly getAccessToken: AccessTokenProvider) {}

  async fetchCredentials() {
    const accessToken = this.getAccessToken();
    if (!accessToken) {
      throw new Error('No Django access token — login first');
    }

    const data = await apiFetch<{ token: string; powersync_url: string }>('/api/sync/token/', {
      method: 'POST',
      accessToken,
    });
    syncLog.info('sync token', { endpoint: data.powersync_url });
    return { endpoint: data.powersync_url, token: data.token };
  }

  async uploadData(database: AbstractPowerSyncDatabase): Promise<void> {
    const accessToken = this.getAccessToken();
    if (!accessToken) {
      throw new Error('No Django access token — cannot upload');
    }

    let batch;
    while ((batch = await database.getCrudBatch(100)) !== null) {
      const mutations = batch.crud.map((op) => {
        const mutation: Record<string, unknown> = {
          op: op.op,
          type: op.table,
          data: op.opData,
        };
        if (op.transactionId != null) {
          mutation.tx_id = op.transactionId;
        }
        return mutation;
      });

      if (mutations.length === 0) {
        await batch.complete();
        continue;
      }

      syncLog.info('upload crud batch', {
        count: mutations.length,
        tables: [...new Set(mutations.map((m) => m.type))],
      });
      await apiFetch('/api/sync/mutations/', {
        method: 'POST',
        accessToken,
        body: JSON.stringify({ mutations }),
      });
      await batch.complete();
    }
  }
}
