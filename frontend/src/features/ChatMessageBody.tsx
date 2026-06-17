import { useMemo } from 'react';

import { renderAssistantMarkdown } from './chat-markdown';
import './chat-markdown.css';

export function ChatMessageBody({
  content,
  role,
}: {
  content: string;
  role: 'user' | 'assistant';
}) {
  const html = useMemo(
    () => (role === 'assistant' ? renderAssistantMarkdown(content) : null),
    [content, role],
  );

  if (role === 'user') {
    return <span className="chat-plain">{content}</span>;
  }

  return <div className="chat-md" dangerouslySetInnerHTML={{ __html: html! }} />;
}
