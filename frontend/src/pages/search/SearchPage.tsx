import { Code2, Search as SearchIcon } from 'lucide-react';
import { useState } from 'react';
import {
  Checkbox,
  EmptyState,
  ErrorState,
  Input,
  Pagination,
  Skeleton,
} from '@/components/ui';
import { SearchResultCard } from '@/features/search/components';
import { useSearch } from '@/features/search/hooks';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { toUserMessage } from '@/services/api/errors';

const PAGE_SIZE = 10;

export function SearchPage() {
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const [debugMode, setDebugMode] = useState(false);

  const debouncedQuery = useDebouncedValue(query, 300);

  const { data, isLoading, isError, error, refetch } = useSearch({
    query: debouncedQuery,
    page,
    pageSize: PAGE_SIZE,
  });

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-6">
      <div>
        <h1 className="text-xl font-semibold text-fg">Search</h1>
        <p className="text-sm text-fg-muted">
          Hybrid lexical + dense retrieval across your ingested documents.
        </p>
      </div>

      <div className="relative">
        <SearchIcon
          className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-fg-subtle"
          aria-hidden="true"
        />
        <Input
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setPage(1);
          }}
          placeholder="Ask a question or search for a term…"
          className="h-11 pl-9 text-base"
          autoFocus
        />
      </div>

      <Checkbox
        label="Show retrieval debug info (lexical / dense / fused / reranker scores)"
        checked={debugMode}
        onChange={(event) => setDebugMode(event.target.checked)}
      />

      {!debouncedQuery.trim() && (
        <EmptyState
          icon={Code2}
          title="Start typing to search"
          description="Results are ranked by hybrid relevance across lexical and dense retrieval."
        />
      )}

      {debouncedQuery.trim() && isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      )}

      {debouncedQuery.trim() && isError && (
        <ErrorState
          description={toUserMessage(error)}
          onRetry={() => void refetch()}
        />
      )}

      {debouncedQuery.trim() &&
        !isLoading &&
        !isError &&
        data?.items.length === 0 && (
          <EmptyState
            title="No results"
            description="Try a different phrasing, or check that the document has finished ingesting."
          />
        )}

      {debouncedQuery.trim() &&
        !isLoading &&
        !isError &&
        data &&
        data.items.length > 0 && (
          <>
            <div className="space-y-3">
              {data.items.map((result) => (
                <SearchResultCard
                  key={result.id}
                  result={result}
                  query={debouncedQuery}
                  debug={debugMode}
                />
              ))}
            </div>
            <Pagination
              page={data.page}
              totalPages={Math.max(1, Math.ceil(data.total / data.pageSize))}
              onPageChange={setPage}
              className="pt-2"
            />
          </>
        )}
    </div>
  );
}
