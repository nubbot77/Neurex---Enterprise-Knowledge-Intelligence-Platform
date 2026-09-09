import { Send, Square } from 'lucide-react';
import { useState, type KeyboardEvent } from 'react';
import { Button, Textarea } from '@/components/ui';

export interface MessageInputProps {
  onSend: (text: string) => void;
  onStop: () => void;
  isStreaming: boolean;
}

export function MessageInput({
  onSend,
  onStop,
  isStreaming,
}: MessageInputProps) {
  const [value, setValue] = useState('');

  const submit = () => {
    if (!value.trim() || isStreaming) return;
    onSend(value);
    setValue('');
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <div className="flex items-end gap-2 border-t border-border p-3">
      <Textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask a question about your documents…"
        rows={2}
        className="min-h-0 flex-1 resize-none"
      />
      {isStreaming ? (
        <Button
          variant="outline"
          size="icon"
          aria-label="Stop generating"
          onClick={onStop}
        >
          <Square className="size-4" />
        </Button>
      ) : (
        <Button
          size="icon"
          aria-label="Send message"
          onClick={submit}
          disabled={!value.trim()}
        >
          <Send className="size-4" />
        </Button>
      )}
    </div>
  );
}
