import { getChatCollection } from './collections';

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
  await getChatCollection().insert({
    id: chatMessageId,
    chat_message_id: chatMessageId,
    user_id: userId,
    role: 'user',
    content: trimmed,
    created_at: new Date().toISOString(),
  }).isPersisted.promise;
}
