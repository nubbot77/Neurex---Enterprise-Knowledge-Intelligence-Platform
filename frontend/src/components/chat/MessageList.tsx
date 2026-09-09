import { useEffect, useRef } from 'react';
import { EmptyState } from '@/components/ui';
import type { Message } from '@/features/conversations/types';
import { MessageBubble } from './MessageBubble';

export interface MessageListProps {
  messages: Message[];
  onRegenerate: () => void;
}

export function MessageList({ messages, onRegenerate }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-6">
        <EmptyState
          title="Ask anything about your documents"
          description="Answers are grounded in your ingested knowledge base, with citations back to the source."
        />
      </div>
    );
  }

  const lastAssistantIndex = messages
    .map((m) => m.role)
    .lastIndexOf('assistant');

  return (
    <div className="flex-1 space-y-4 overflow-y-auto p-4">
      {messages.map((message, index) => (
        <div key={message.id} className="group">
          <MessageBubble
            message={message}
            isLastAssistantMessage={index === lastAssistantIndex}
            onRegenerate={onRegenerate}
          />
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
