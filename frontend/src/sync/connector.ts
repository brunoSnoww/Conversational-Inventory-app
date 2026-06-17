import type { AbstractPowerSyncDatabase, PowerSyncBackendConnector } from '@powersync/web';

import { apiFetch } from '../api/client';

export type AccessTokenProvider = () => string | null;

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

      await apiFetch('/api/sync/mutations/', {
        method: 'POST',
        accessToken,
        body: JSON.stringify({ mutations }),
      });
      await batch.complete();
    }
  }
}
