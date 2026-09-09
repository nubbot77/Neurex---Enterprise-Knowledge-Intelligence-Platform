import { FileText } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Badge, Card, CardContent } from '@/components/ui';
import { highlightMatches } from '@/utils/highlight';
import type { SearchResult } from '../types';

export interface SearchResultCardProps {
  result: SearchResult;
  query: string;
  debug: boolean;
}

function scoreLabel(value: number | undefined): string | null {
  return value === undefined ? null : value.toFixed(3);
}

export function SearchResultCard({
  result,
  query,
  debug,
}: SearchResultCardProps) {
  return (
    <Card>
      <CardContent className="space-y-2">
        <div className="flex items-start justify-between gap-3">
          <Link
            to={`/documents/${result.documentId}`}
            className="flex items-center gap-1.5 text-sm font-medium text-fg hover:text-accent"
          >
            <FileText
              className="size-4 shrink-0 text-fg-subtle"
              aria-hidden="true"
            />
            {result.documentTitle}
            {result.pageNumber !== undefined && (
              <span className="text-fg-subtle"> · p. {result.pageNumber}</span>
            )}
          </Link>
          <Badge variant="accent">{result.score.toFixed(3)}</Badge>
        </div>

        <p className="text-sm text-fg-muted">
          {highlightMatches(result.snippet, query)}
        </p>

        {debug && (
          <div className="flex flex-wrap gap-x-4 gap-y-1 border-t border-border pt-2 text-xs text-fg-subtle">
            {scoreLabel(result.lexicalScore) && (
              <span>lexical: {scoreLabel(result.lexicalScore)}</span>
            )}
            {scoreLabel(result.denseScore) && (
              <span>dense: {scoreLabel(result.denseScore)}</span>
            )}
            {scoreLabel(result.fusedScore) && (
              <span>fused: {scoreLabel(result.fusedScore)}</span>
            )}
            {scoreLabel(result.rerankerScore) && (
              <span>reranker: {scoreLabel(result.rerankerScore)}</span>
            )}
            <span>chunk: {result.chunkId}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
