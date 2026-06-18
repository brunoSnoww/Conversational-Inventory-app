/**
 * TanStack DB collections backed by PowerSync SQLite (eager sync mode).
 *
 * Flow: PowerSync service → local SQLite → collection (eager) → useLiveQuery.
 * Writes for chat use optimistic collection.insert → PowerSync upload connector.
 */
import type { PowerSyncDatabase } from '@powersync/web';
import { powerSyncCollectionOptions } from '@tanstack/powersync-db-collection';
import { createCollection } from '@tanstack/react-db';

import { AppSchema } from './schema';

type ChatCollection = ReturnType<typeof createChatCollection>;

function createChatCollection(database: PowerSyncDatabase) {
  return createCollection(
    powerSyncCollectionOptions({
      database,
      table: AppSchema.props.chat_message,
      syncMode: 'eager',
    }),
  );
}

let chatCollection: ChatCollection | null = null;

export { createChatCollection, setChatCollection };

function setChatCollection(collection: ChatCollection | null) {
  chatCollection = collection;
}

export function getChatCollection(): ChatCollection {
  if (!chatCollection) {
    throw new Error('Chat collection not ready — PowerSync not initialized');
  }
  return chatCollection;
}

/** Non-throwing accessor for hooks that render before sync is ready. */
export function tryGetChatCollection(): ChatCollection | null {
  return chatCollection;
}
