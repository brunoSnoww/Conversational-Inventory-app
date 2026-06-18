import { Box, Stack } from '@mantine/core';
import { useLayoutEffect, useRef, useState } from 'react';
import { Chat, ChatInput, ChatMessage, ChatMessages } from 'mantine-chat-components';

import { useAuth } from '../auth/AuthContext';
import {
  isThinkingPlaceholder,
  sendChatMessage,
  THINKING_PLACEHOLDER,
  useChatMessages,
} from '../sync';
import { ChatMessageBody } from './ChatMessageBody';
import { ErrorText, friendlyError } from './ui';

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
  const agentBusy = lastMessage != null && isThinkingPlaceholder(lastMessage.content);
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
      setError(friendlyError(err));
      setValue(msg);
    } finally {
      setSending(false);
    }
  }

  return (
    <Stack flex={1} mih={0} gap="sm" style={{ overflow: 'hidden' }}>
      <Chat flex={1} mih={0} style={{ display: 'flex', flexDirection: 'column' }}>
        <ChatMessages ref={messagesRef} flex={1} mih={0}>
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
        {error && (
          <Box px="sm" pb="xs">
            <ErrorText>{error}</ErrorText>
          </Box>
        )}
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
    </Stack>
  );
}
