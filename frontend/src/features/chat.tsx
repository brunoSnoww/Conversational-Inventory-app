import { useLayoutEffect, useRef, useState } from 'react';
import { Chat, ChatInput, ChatMessage, ChatMessages } from 'mantine-chat-components';

import { useAuth } from '../auth/AuthContext';
import { isThinkingPlaceholder, THINKING_PLACEHOLDER } from '../sync/chat-constants';
import { sendChatMessage, useChatMessages } from '../sync';
import { ChatMessageBody } from './ChatMessageBody';
import { ErrorText, Page, Panel, friendlyError } from './ui';

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
  const lastMessage = messages.length > 0 ? messages[messages.length - 1] : null;
  const awaitingReply =
    lastMessage != null &&
    (lastMessage.role === 'user' || isThinkingPlaceholder(lastMessage.content));
  const agentBusy = awaitingReply;
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
      <Panel>
        <Chat h={360}>
          <ChatMessages ref={messagesRef}>
            {messages.map((m) => {
              const id = m.chat_message_id ?? m.id;
              const thinking = isThinkingPlaceholder(m.content);
              return (
                <ChatMessage
                  key={id}
                  sender={messageSender(m.role ?? 'assistant')}
                  messageId={id}
                  userColor="blue"
                  assistantColor="gray"
                >
                  <ChatMessageBody
                    content={thinking ? THINKING_PLACEHOLDER : (m.content ?? '')}
                    role={messageSender(m.role ?? 'assistant')}
                  />
                </ChatMessage>
              );
            })}
            {awaitingReply && lastMessage?.role === 'user' && (
              <ChatMessage sender="assistant" assistantColor="gray">
                {THINKING_PLACEHOLDER}
              </ChatMessage>
            )}
          </ChatMessages>
          <ChatInput
            value={value}
            onValueChange={setValue}
            onSubmit={send}
            loading={sending}
            disabled={!session || sending || agentBusy}
            withEmojiPicker={false}
            withFileUpload={false}
            inputProps={{ placeholder: 'Message' }}
          />
        </Chat>
      </Panel>
      {error && (
        <Panel>
          <ErrorText>{error}</ErrorText>
        </Panel>
      )}
    </Page>
  );
}
