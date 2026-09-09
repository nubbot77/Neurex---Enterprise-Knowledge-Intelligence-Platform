import { AlertCircle, Bot, Check, Copy, RotateCw } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui';
import { CitationList } from '@/components/citations';
import type { Message } from '@/features/conversations/types';
import { cn } from '@/utils/cn';
import { StreamingMessage } from './StreamingMessage';

export interface MessageBubbleProps {
  message: Message;
  isLastAssistantMessage: boolean;
  onRegenerate: () => void;
}

export function MessageBubble({
  message,
  isLastAssistantMessage,
  onRegenerate,
}: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';

  const handleCopy = () => {
    void navigator.clipboard.writeText(message.content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-lg bg-accent px-3.5 py-2 text-sm text-accent-fg">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-surface-hover">
        <Bot className="size-4 text-fg-muted" aria-hidden="true" />
      </div>
      <div className="min-w-0 flex-1 space-y-1.5">
        {message.status === 'error' ? (
          <p className="flex items-center gap-1.5 text-sm text-danger">
            <AlertCircle className="size-4 shrink-0" aria-hidden="true" />
            {message.error ?? 'Something went wrong generating a response.'}
          </p>
        ) : (
          <div className="text-sm text-fg">
            <StreamingMessage
              content={message.content}
              isStreaming={message.status === 'streaming'}
            />
          </div>
        )}

        {message.citations && <CitationList citations={message.citations} />}

        {message.status !== 'streaming' && message.status !== 'sending' && (
          <div
            className={cn(
              'flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100',
            )}
          >
            <Button
              variant="ghost"
              size="icon"
              aria-label="Copy response"
              onClick={handleCopy}
            >
              {copied ? (
                <Check className="size-3.5" />
              ) : (
                <Copy className="size-3.5" />
              )}
            </Button>
            {isLastAssistantMessage && (
              <Button
                variant="ghost"
                size="icon"
                aria-label="Regenerate response"
                onClick={onRegenerate}
              >
                <RotateCw className="size-3.5" />
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
