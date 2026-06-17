import { describe, expect, it } from 'vitest';

import { formatWhen } from './format';

describe('formatWhen', () => {
  it('formats valid ISO timestamps', () => {
    const result = formatWhen('2025-06-15T12:00:00.000Z');
    expect(result).not.toBe('2025-06-15T12:00:00.000Z');
    expect(result.length).toBeGreaterThan(0);
  });

  it('returns input unchanged on invalid date', () => {
    expect(formatWhen('not-a-date')).toBe('not-a-date');
  });
});
