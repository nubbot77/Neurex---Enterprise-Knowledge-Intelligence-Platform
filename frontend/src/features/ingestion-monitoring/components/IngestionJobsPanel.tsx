import { useState } from 'react';
import { EmptyState, ErrorState, Pagination, Skeleton } from '@/components/ui';
import { toUserMessage } from '@/services/api/errors';
import { useIngestionJobs } from '../hooks';
import { IngestionJobsTable } from './IngestionJobsTable';
import { IngestionLogViewer } from './IngestionLogViewer';

const PAGE_SIZE = 20;

export function IngestionJobsPanel() {
  const [page, setPage] = useState(1);
  const [logsJobId, setLogsJobId] = useState<string | null>(null);

  const { data, isLoading, isError, error, refetch } = useIngestionJobs({
    page,
    pageSize: PAGE_SIZE,
  });

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorState
        description={toUserMessage(error)}
        onRetry={() => void refetch()}
      />
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <EmptyState
        title="No ingestion jobs"
        description="Jobs appear here once a document is uploaded."
      />
    );
  }

  return (
    <>
      <IngestionJobsTable jobs={data.items} onViewLogs={setLogsJobId} />
      <Pagination
        page={data.page}
        totalPages={Math.max(1, Math.ceil(data.total / data.pageSize))}
        onPageChange={setPage}
        className="pt-2"
      />
      <IngestionLogViewer
        jobId={logsJobId}
        onOpenChange={(open) => !open && setLogsJobId(null)}
      />
    </>
  );
}
