import type {
  PowerSyncBackendConnector,
  RequiredAdditionalConnectionOptions,
  StreamingSyncImplementation,
} from '@powersync/common';
import {
  PowerSyncDatabase,
  WebRemote,
  WebStreamingSyncImplementation,
  type WebStreamingSyncImplementationOptions,
} from '@powersync/web';

import { createPowerSyncFetch } from './powersync-fetch';

/**
 * PowerSync HTTP calls (write-checkpoint) need ngrok-safe routing on Vercel.
 * WebSocket sync still uses the public PowerSync URL from /api/sync/token/.
 */
export class InventoryPowerSyncDatabase extends PowerSyncDatabase {
  protected generateSyncStreamImplementation(
    connector: PowerSyncBackendConnector,
    options: RequiredAdditionalConnectionOptions,
  ): StreamingSyncImplementation {
    if (this.resolvedFlags.ssrMode || this.resolvedFlags.enableMultiTabs) {
      return super.generateSyncStreamImplementation(connector, options);
    }

    const remote = new WebRemote(connector, this.logger, {
      fetchImplementation: createPowerSyncFetch(),
    });
    const syncOptions: WebStreamingSyncImplementationOptions = {
      ...(this.options as object),
      ...options,
      flags: this.resolvedFlags,
      adapter: this.bucketStorageAdapter,
      remote,
      uploadCrud: async () => {
        await this.waitForReady();
        await connector.uploadData(this);
      },
      identifier: this.database.name,
      logger: this.logger,
    };
    return new WebStreamingSyncImplementation(syncOptions);
  }
}
