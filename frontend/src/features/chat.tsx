import { useLayoutEffect, useRef, useState } from 'react';
import { Chat, ChatInput, ChatMessage, ChatMessages } from 'mantine-chat-components';

import { useAuth } from '../auth/AuthContext';
import { sendChatMessage, useChatMessages } from '../sync';
import { ErrorText, Page, friendlyError } from './ui';

function messageSender(role: string): 'user' | 'assistant' {
  return role === 'user' ? 'user' : 'assistant';
}

export function ChatPage() {
  const { session } = useAuth();
  const chatMessages = useChatMessages();
  const [value, setValue] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const messages = chatMessages.data ?? [];
  const awaitingReply =
    messages.length > 0 && messages[messages.length - 1].role === 'user';
  const messagesRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const el = messagesRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages.length, awaitingReply]);

  async function send() {
    const msg = value.trim();
    if (!msg || !session || sending) return;
    setValue('');
    setError(null);
    setSending(true);
    try {
      await sendChatMessage(session.userId, msg);
    } catch (err) {
      setError(friendlyError(err instanceof Error ? err.message : 'Failed to send'));
      setValue(msg);
    } finally {
      setSending(false);
    }
  }

  return (
    <Page title="Chat">
      <Chat h={360}>
        <ChatMessages ref={messagesRef}>
          {messages.map((m) => {
            const id = m.chat_message_id ?? m.id;
            return (
              <ChatMessage
                key={id}
                sender={messageSender(m.role ?? 'assistant')}
                messageId={id}
                userColor="blue"
                assistantColor="gray"
              >
                {m.content}
              </ChatMessage>
            );
          })}
          {awaitingReply && (
            <ChatMessage sender="assistant" assistantColor="gray">
              …
            </ChatMessage>
          )}
        </ChatMessages>
        <ChatInput
          value={value}
          onValueChange={setValue}
          onSubmit={send}
          loading={sending}
          disabled={!session || sending}
          withEmojiPicker={false}
          withFileUpload={false}
          inputProps={{ placeholder: 'Message' }}
        />
      </Chat>
      {error && <ErrorText>{error}</ErrorText>}
    </Page>
  );
}
