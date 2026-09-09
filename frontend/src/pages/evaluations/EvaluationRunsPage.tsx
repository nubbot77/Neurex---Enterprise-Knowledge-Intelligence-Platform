import { useState } from 'react';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui';
import { RunDetailDialog, RunsTable } from '@/features/evaluations/components';
import { useEvaluationRuns } from '@/features/evaluations/hooks';
import type { EvaluationRun } from '@/features/evaluations/types';
import { toUserMessage } from '@/services/api/errors';

export function EvaluationRunsPage() {
  const { data, isLoading, isError, error, refetch } = useEvaluationRuns();
  const [selectedRun, setSelectedRun] = useState<EvaluationRun | null>(null);

  return (
    <div className="space-y-4 p-6">
      <div>
        <h1 className="text-xl font-semibold text-fg">Evaluation runs</h1>
        <p className="text-sm text-fg-muted">
          Latency, cost, and metric history for past evaluation runs.
        </p>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      )}

      {isError && (
        <ErrorState
          description={toUserMessage(error)}
          onRetry={() => void refetch()}
        />
      )}

      {!isLoading && !isError && data?.items.length === 0 && (
        <EmptyState
          title="No evaluation runs yet"
          description="Runs will appear here once an evaluation dataset has been executed."
        />
      )}

      {!isLoading && !isError && data && data.items.length > 0 && (
        <RunsTable runs={data.items} onSelectRun={setSelectedRun} />
      )}

      <RunDetailDialog
        run={selectedRun}
        onOpenChange={(open) => !open && setSelectedRun(null)}
      />
    </div>
  );
}
