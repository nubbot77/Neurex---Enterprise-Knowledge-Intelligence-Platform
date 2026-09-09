import { TypingIndicator } from './TypingIndicator';

export function StreamingMessage({
  content,
  isStreaming,
}: {
  content: string;
  isStreaming: boolean;
}) {
  if (isStreaming && content.length === 0) {
    return <TypingIndicator />;
  }

  return (
    <span className="whitespace-pre-wrap">
      {content}
      {isStreaming && (
        <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-fg-muted align-text-bottom" />
      )}
    </span>
  );
}
