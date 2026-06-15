import type { AbstractPowerSyncDatabase, PowerSyncBackendConnector } from '@powersync/web';

export type AccessTokenProvider = () => string | null;

/**
 * Hybrid upload connector:
 * - fetchCredentials → Django JWT → POST /api/sync/token/
 * - uploadData → Django JWT → POST /api/sync/mutations/ (chat_message only on server)
 */
export class InventoryConnector implements PowerSyncBackendConnector {
  constructor(
    private readonly apiBaseUrl: string,
    private readonly getAccessToken: AccessTokenProvider,
  ) {}

  async fetchCredentials() {
    const accessToken = this.getAccessToken();
    if (!accessToken) {
      throw new Error('No Django access token — login first');
    }

    const resp = await fetch(`${this.apiBaseUrl}/api/sync/token/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
    });

    if (!resp.ok) {
      throw new Error(`sync/token failed: HTTP ${resp.status}: ${await resp.text()}`);
    }

    const data = (await resp.json()) as { token: string; powersync_url: string };
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

      const resp = await fetch(`${this.apiBaseUrl}/api/sync/mutations/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ mutations }),
      });

      if (!resp.ok) {
        throw new Error(`sync/mutations failed: HTTP ${resp.status}: ${await resp.text()}`);
      }

      await batch.complete();
    }
  }
}
