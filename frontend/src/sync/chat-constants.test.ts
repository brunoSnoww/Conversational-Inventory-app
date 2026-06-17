import { describe, expect, it } from 'vitest';

import { isThinkingPlaceholder, THINKING_PLACEHOLDER } from './chat-constants';

describe('chat-constants', () => {
  it('detects thinking placeholder', () => {
    expect(isThinkingPlaceholder(THINKING_PLACEHOLDER)).toBe(true);
    expect(isThinkingPlaceholder(`  ${THINKING_PLACEHOLDER}  `)).toBe(true);
    expect(isThinkingPlaceholder('Done.')).toBe(false);
  });
});
