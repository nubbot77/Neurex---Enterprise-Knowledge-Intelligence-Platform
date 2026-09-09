import type { Citation as CitationType } from '@/features/conversations/types';

export interface CitationProps {
  citation: CitationType;
  index: number;
  onOpen: (citation: CitationType) => void;
}

export function Citation({ citation, index, onOpen }: CitationProps) {
  return (
    <button
      type="button"
      onClick={() => onOpen(citation)}
      className="inline-flex size-5 items-center justify-center rounded-full bg-accent/15 text-xs font-medium text-accent hover:bg-accent/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      aria-label={`Source ${index + 1}: ${citation.documentTitle}`}
    >
      {index + 1}
    </button>
  );
}
