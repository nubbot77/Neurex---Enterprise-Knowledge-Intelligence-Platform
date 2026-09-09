import { FileText } from 'lucide-react';
import { Link } from 'react-router-dom';
import { buttonVariants } from '@/components/ui';
import type { Citation } from '@/features/conversations/types';

export function SourcePreview({ citation }: { citation: Citation }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm font-medium text-fg">
        <FileText className="size-4 text-fg-subtle" aria-hidden="true" />
        {citation.documentTitle}
        {citation.pageNumber !== undefined && (
          <span className="text-fg-subtle">· p. {citation.pageNumber}</span>
        )}
      </div>
      <blockquote className="rounded-md border-l-2 border-accent bg-surface-hover p-3 text-sm text-fg-muted italic">
        {citation.snippet}
      </blockquote>
      <Link
        to={`/documents/${citation.documentId}`}
        className={buttonVariants({ variant: 'outline', size: 'sm' })}
      >
        Open document
      </Link>
    </div>
  );
}
