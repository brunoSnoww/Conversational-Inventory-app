import { marked } from 'marked';

marked.use({ breaks: true, gfm: true });

/**
 * Port of jotaweb/shell/web/static/markdown.js — converts WhatsApp-style emphasis
 * (*bold*, _italic_, ~strike~) to standard markdown before parsing.
 */
export function whatsappToMarkdown(text: string): string {
  let t = text.replace(/\r\n/g, '\n');

  t = t.replace(
    /(^|[\s(])(\*)((?!\s)[^\n*]+(?<!\s))\2(?=$|[\s).,!?;:])/gm,
    '$1**$3**',
  );
  t = t.replace(
    /(^|[\s(])(_)((?!\s)[^\n_]+(?<!\s))\2(?=$|[\s).,!?;:])/gm,
    '$1*$3*',
  );
  t = t.replace(
    /(^|[\s(])(~)((?!\s)[^\n~]+(?<!\s))\2(?=$|[\s).,!?;:])/gm,
    '$1~~$3~~',
  );
  // Blockquotes need a blank line before them in markdown.
  t = t.replace(/([^\n])\n(>)/g, '$1\n\n$2');

  return t;
}

/** Collapse runaway blank lines; keep intentional paragraph breaks. */
export function normalizeMessageText(text: string): string {
  return text.replace(/\r\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
}

export function renderAssistantMarkdown(content: string): string {
  const md = whatsappToMarkdown(normalizeMessageText(content));
  return marked.parse(md, { async: false }) as string;
}
