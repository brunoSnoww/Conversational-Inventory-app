import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ChatMessageBody } from './ChatMessageBody';

describe('ChatMessageBody', () => {
  it('renders user text with plain pre-wrap', () => {
    render(<ChatMessageBody content={'hello\nworld'} role="user" />);
    const el = screen.getByText(/hello/);
    expect(el).toHaveClass('chat-plain');
    expect(el.textContent).toBe('hello\nworld');
  });

  it('renders assistant markdown as HTML', () => {
    const { container } = render(
      <ChatMessageBody content={'**Profit:** $900'} role="assistant" />,
    );
    const md = container.querySelector('.chat-md');
    expect(md?.innerHTML).toContain('<strong>Profit:</strong>');
  });
});
