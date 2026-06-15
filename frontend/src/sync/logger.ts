/**
 * Dev sync logs — filter browser console with `[inventory-sync]`.
 * Set VITE_SYNC_DEBUG=false to silence in dev.
 */
const ENABLED =
  import.meta.env.VITE_SYNC_DEBUG !== 'false' &&
  (import.meta.env.DEV || import.meta.env.VITE_SYNC_DEBUG === 'true');

const PREFIX = '[inventory-sync]';

function emit(level: 'log' | 'warn' | 'error', message: string, data?: unknown) {
  if (!ENABLED) {
    return;
  }
  if (data === undefined) {
    console[level](`${PREFIX} ${message}`);
  } else {
    console[level](`${PREFIX} ${message}`, data);
  }
}

export const syncLog = {
  info: (message: string, data?: unknown) => emit('log', message, data),
  warn: (message: string, data?: unknown) => emit('warn', message, data),
  error: (message: string, data?: unknown) => emit('error', message, data),
};
