import { describe, expect, it } from 'vitest';

import {
  normalizeMessageText,
  renderAssistantMarkdown,
  whatsappToMarkdown,
} from './chat-markdown';

describe('whatsappToMarkdown', () => {
  it('converts WhatsApp bold to markdown', () => {
    expect(whatsappToMarkdown('Total *$200*')).toBe('Total **$200**');
  });

  it('converts WhatsApp italic to markdown', () => {
    expect(whatsappToMarkdown('Note _important_')).toBe('Note *important*');
  });

  it('inserts blank line before blockquote', () => {
    expect(whatsappToMarkdown('line one\n> quote')).toBe('line one\n\n> quote');
  });
});

describe('normalizeMessageText', () => {
  it('collapses triple newlines', () => {
    expect(normalizeMessageText('a\n\n\n\nb')).toBe('a\n\nb');
  });

  it('trims outer whitespace', () => {
    expect(normalizeMessageText('  hello  ')).toBe('hello');
  });
});

describe('renderAssistantMarkdown', () => {
  it('renders bold markdown', () => {
    const html = renderAssistantMarkdown('**SKU:** `CB-01`');
    expect(html).toContain('<strong>SKU:</strong>');
    expect(html).toContain('<code>CB-01</code>');
  });

  it('preserves single line breaks', () => {
    const html = renderAssistantMarkdown('line one\nline two');
    expect(html).toMatch(/<br\s*\/?>/);
  });

  it('renders bullet lists', () => {
    const html = renderAssistantMarkdown('- first\n- second');
    expect(html).toContain('<ul>');
    expect(html).toContain('<li>first</li>');
  });

  it('escapes raw HTML from assistant output', () => {
    const html = renderAssistantMarkdown('<script>alert(1)</script>');
    expect(html).not.toContain('<script');
    expect(html).toContain('&lt;script');
  });
});
