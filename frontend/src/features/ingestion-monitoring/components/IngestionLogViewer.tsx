import { Dialog, EmptyState, Skeleton } from '@/components/ui';
import { formatDate } from '@/utils/format';
import { useIngestionJobLogs } from '../hooks';

const levelColor: Record<string, string> = {
  info: 'text-fg-muted',
  warn: 'text-warning',
  error: 'text-danger',
};

export interface IngestionLogViewerProps {
  jobId: string | null;
  onOpenChange: (open: boolean) => void;
}

export function IngestionLogViewer({
  jobId,
  onOpenChange,
}: IngestionLogViewerProps) {
  const { data: logs, isLoading } = useIngestionJobLogs(
    jobId ?? '',
    Boolean(jobId),
  );

  return (
    <Dialog
      open={Boolean(jobId)}
      onOpenChange={onOpenChange}
      title="Ingestion logs"
    >
      {isLoading && (
        <div className="space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-5/6" />
        </div>
      )}

      {!isLoading && (!logs || logs.length === 0) && (
        <EmptyState
          title="No logs yet"
          description="Logs appear once the job starts running."
        />
      )}

      {!isLoading && logs && logs.length > 0 && (
        <div className="max-h-72 space-y-1 overflow-y-auto rounded-md bg-surface-hover p-3 font-mono text-xs">
          {logs.map((entry, index) => (
            <p key={index} className={levelColor[entry.level]}>
              <span className="text-fg-subtle">
                {formatDate(entry.timestamp)}
              </span>{' '}
              {entry.message}
            </p>
          ))}
        </div>
      )}
    </Dialog>
  );
}
