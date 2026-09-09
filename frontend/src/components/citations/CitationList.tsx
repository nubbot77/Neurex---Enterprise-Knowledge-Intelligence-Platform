import { useState } from 'react';
import type { Citation as CitationType } from '@/features/conversations/types';
import { Citation } from './Citation';
import { SourcePanel } from './SourcePanel';

export function CitationList({ citations }: { citations: CitationType[] }) {
  const [active, setActive] = useState<CitationType | null>(null);

  if (citations.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-1.5 pt-1">
      <span className="text-xs text-fg-subtle">Sources:</span>
      {citations.map((citation, index) => (
        <Citation
          key={citation.id}
          citation={citation}
          index={index}
          onOpen={setActive}
        />
      ))}
      <SourcePanel
        citation={active}
        onOpenChange={(open) => !open && setActive(null)}
      />
    </div>
  );
}
