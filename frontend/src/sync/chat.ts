/**
 * TanStack DB chat collection, optimistic sends, and live query hook.
 *
 * Flow: PowerSync service → local SQLite (last CHAT_SYNC_LIMIT rows) → collection → useChatMessages.
 * Writes use optimistic collection.insert → PowerSync upload connector.
 */
import type { PowerSyncDatabase } from '@powersync/web';
import { powerSyncCollectionOptions } from '@tanstack/powersync-db-collection';
import { createCollection, useLiveQuery } from '@tanstack/react-db';

import { syncLog } from './logger';
import { PowerSyncManager } from './powersync';
import { AppSchema } from './schema';

/** Server-side placeholder inserted while the inventory agent runs. */
export const THINKING_PLACEHOLDER = 'Thinking…';

export function isThinkingPlaceholder(content: string | null | undefined): boolean {
  return (content ?? '').trim() === THINKING_PLACEHOLDER;
}

export type ChatCollection = ReturnType<typeof createChatCollection>;

export function createChatCollection(database: PowerSyncDatabase) {
  return createCollection(
    powerSyncCollectionOptions({
      database,
      table: AppSchema.props.chat_message,
      syncMode: 'eager',
    }),
  );
}

/** Client-side id for idempotent upload (server ON CONFLICT DO NOTHING). */
export function clientMessageId(): string {
  const ts = Date.now();
  const rand = Math.floor(Math.random() * 4096);
  return String(ts * 4096 + rand);
}

/**
 * Optimistic chat send via TanStack DB collection.
 *
 * insert → local SQLite (UI updates instantly) → PowerSync CRUD upload →
 * /api/sync/mutations/ → agent runs server-side → assistant reply syncs back.
 * The user row is idempotent (server ON CONFLICT on chat_message_id).
 */
export async function sendChatMessage(userId: string, content: string): Promise<void> {
  const trimmed = content.trim();
  if (!trimmed) {
    return;
  }

  const chatMessageId = clientMessageId();
  syncLog.info('chat send optimistic', { chatMessageId, content: trimmed });
  await PowerSyncManager.getInstance()
    .getChatCollection()
    .insert({
      id: chatMessageId,
      chat_message_id: chatMessageId,
      user_id: userId,
      role: 'user',
      content: trimmed,
      created_at: new Date().toISOString(),
    }).isPersisted.promise;
}

export function useChatMessages() {
  const collection = PowerSyncManager.getInstance().tryGetChatCollection();
  return useLiveQuery(
    (q) =>
      collection
        ? q.from({ m: collection }).orderBy(({ m }) => m.created_at, 'asc')
        : null,
    [collection],
  );
}
