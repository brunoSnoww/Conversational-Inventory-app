/** Server-side placeholder inserted while the inventory agent runs. */
export const THINKING_PLACEHOLDER = 'Thinking…';

export function isThinkingPlaceholder(content: string | null | undefined): boolean {
  return (content ?? '').trim() === THINKING_PLACEHOLDER;
}
